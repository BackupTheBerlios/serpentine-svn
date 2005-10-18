# Copyright (C) 2004 Tiago Cogumbreiro <cogumbreiro@users.sf.net>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# Authors: Tiago Cogumbreiro <cogumbreiro@users.sf.net>

"""
This module contains operations to convert sound files to WAV and to
retrieve a their metadata.
"""

import gst, gobject
import operations

################################################################################

class GstOperation (operations.MeasurableOperation):
    def __init__ (self, query_element = None, pipeline = None, use_threads = False):
        operations.MeasurableOperation.__init__ (self)
        self.__element = query_element
        self.__can_start = True
        self.__running = False
        
        # create a new bin to hold the elements
        if pipeline is None:
            self.__bin = use_threads and gst.Thread () or gst.Pipeline ()
        else:
            self.__bin = pipeline 
        self.__use_threads = use_threads
        self.__source = None
        self.__bin.connect ('error', self.__on_error)
        self.__bin.connect ('eos', self.__on_eos)
        self.__progress = 0.0

    can_start = property (lambda self: self.__can_start)
    
    running = property (lambda self: self.__running)
    
    def __get_progress (self):
        "Returns the progress of the convertion operation."
        
        if self.query_element and self.__progress < 1:
            total = float(self.query_element.query(gst.QUERY_TOTAL, gst.FORMAT_BYTES))
            # when total is zero return zero
            progress = (total and self.query_element.query (gst.QUERY_POSITION, gst.FORMAT_BYTES) / total) or total
            if progress > 1:
                print "GST_ERROR? Progress > 1:", progress
                progress = 1
            
            self.__progress = max (self.__progress, progress)
            assert 0 <= self.__progress <= 1, self.__progress
            
        return self.__progress
        
    progress = property (__get_progress)
    
    bin = property (lambda self: self.__bin)
    
    query_element = property (lambda self: self.__element)

    def start (self):
        assert self.can_start
        self.__bin.set_state (gst.STATE_PLAYING)
        self.__can_start = False
        self.__running = True
        if not self.__use_threads:
            self.__source = gobject.idle_add (self.bin.iterate)
    
    def __on_eos (self, element, user_data = None):
        self.__finalize ()
        self._send_finished_event (operations.SUCCESSFUL)
    
    def __on_error (self, pipeline, element, error, user_data = None):
        # Do not continue processing it
        if self.__source:
            gobject.source_remove (self.__source)
        self.__finalize ()
        self._send_finished_event (operations.ERROR, error)

    def __finalize (self):
        self.__bin.set_state (gst.STATE_NULL)
        self.__source = None
        self.__running = False
    
    def stop (self):
        if self.__source is None:
            return
        # After this it's dead
        gobject.source_remove (self.__source)
        self.__source = None
        # Finish the event
        self._send_finished_event (operations.ABORTED)

################################################################################

class AudioMetadataListener (operations.OperationListener):
    """
    The on_metadata event is called before the FinishedEvent, if the metadata
    retriavel is successful.
    """
    def on_metadata (self, event, metadata):
        pass

class AudioMetadataEvent (operations.Event):
    "Event that holds the audio metadata."
    
    def __init__ (self, source, id, metadata):
        operations.FinishedEvent.__init__ (source, id)
        self.__metadata = metadata
        
    metadata = property (lambda self: self.__metadata)

class AudioMetadata (operations.Operation, operations.OperationListener):
    """
    Returns the metadata associated with the source element.
    
    To retrieve the metadata associated with a certain media file on gst-launch -t:
    source ! decodebin ! fakesink
    """
    
    def __init__ (self, source):
        operations.Operation.__init__ (self)
        self.__can_start = True
        bin = gst.parse_launch ("decodebin ! fakesink")
                                
        self.__oper = GstOperation(pipeline = bin)
        self.__oper.listeners.append (self)
        
        self.__metadata = {}
        self.__error = None
        
        bin.connect ("found-tag", self.__on_found_tag)
        
        # Last element of the bin is the sinks
        sink = bin.get_list ()[-1]
        sink.set_property ("signal-handoffs", True)
        # handoffs are called when it processes one chunk of data
        sink.connect ("handoff", self.__on_handoff)
        self.__oper.element = sink
        
        # connect source to the first element on the pipeline
        source.link (bin.get_list ()[0])
        bin.add (source)
        
    
    can_start = property (lambda self: self.__can_start)
    
    running = property (lambda self: self.__oper != None)
    
    def start (self):
        assert self.can_start, "Can only be started once."
        self.__can_start = False
        self.__oper.start()
        
    def on_finished (self, event):
        # When the operation is finished we send the metadata
        success = event.id == operations.ABORTED
        if success:
            # We've completed the operation successfully
            if self.__metadata.has_key ("duration"):
                self.__metadata["duration"] /= gst.SECOND
            else:
                self.__metadata["duration"] = self.__oper.element.query(gst.QUERY_TOTAL, gst.FORMAT_TIME) / gst.SECOND
            evt = operations.Event (self)
            
            for l in self.listeners:
                l.on_metadata (evt, self.__metadata)
            self.__metadata = None
            self.__element = None
        
        if success:
            success = operations.SUCCESSFUL
        else:
            success = operations.ERROR
        
        self._send_finished_event (success)
    
    def __on_handoff (self, *args):
        # Ask the gobject main context to stop our pipe
        self.__oper.stop()
        
    def __on_found_tag (self, pipeline, source, tags, user_data = None):
        for key in tags.keys():
            self.__metadata[key] = tags.get(key)
    
    def stop (self):
        if not self.can_stop:
            return
        self.__oper.stop ()
    
def fileAudioMetadata (filename):
    """
    Returns the audio metadata from a file.
    """
    filesrc = gst.element_factory_make ("filesrc", "source")
    filesrc.set_property ("location", filename)
    return AudioMetadata(filesrc)


try:
    import gnomevfs
    def gvfsAudioMetadata (uri):
        """
        Returns the audio metadata from an URI.
        """
        filesrc = gst.element_factory_make ("gnomevfssrc", "source")
        filesrc.set_property ("location", uri)
        return AudioMetadata(filesrc)

except:
    pass

    
################################################################################
WavPcmStruct = {
    'rate'      : 44100,
    'signed'    : True,
    'channels'  : 2,
    'width'     : 16,
    'depth'     : 16,
    'endianness': 1234
}

WavPcmParse = ("audio/x-raw-int, endianness=(int)1234, width=(int)16, "
               "depth=(int)16, signed=(boolean)true, rate=(int)44100, "
               "channels=(int)2")

def capsIsWavPcm (caps):
    global WavPcmParse
    
    struct = caps[0]
    if not struct.get_name () == "audio/x-raw-int":
        return False
    
    for key, value in WavPcmStruct.iteritems ():
        if not struct.has_field (key) or struct[key] != value:
            return False
    
    return True


class IsWavPcm (operations.Operation, operations.OperationListener):
    """
    Tests if a certain WAV is in the PCM format.
    """

    def __init__ (self, source):
    
        bin = gst.parse_launch (
            "typefind ! wavparse ! " + WavPcmParse + " ! fakesink"
        )
        
        
        elements = bin.get_list ()
        decoder = elements[0]
        sink = elements[-1]
        waveparse = elements[1]
        sink.set_property ("signal-handoffs", True)
        sink.connect ("handoff", self.on_handoff)
        
        waveparse.connect ("new-pad", self.on_new_pad)
        
        self.oper = GstOperation(sink, bin)
        self.oper.bin.add (source)
        self.oper.listeners.append (self)
        source.link (decoder)
        self.isPcm = False
        self.__can_start = True
        super (IsWavPcm, self).__init__()

    def on_handoff (self, *args):
        self.oper.stop ()
    
    def on_new_pad (self, src, pad):
        caps = pad.get_caps()
        self.isWavPcm = capsIsWavPcm (caps)

    def on_finished (self, event):
        if self.isWavPcm:
            assert event.id == operations.SUCCESSFUL or event.id == operations.ABORTED
            
            self._send_finished_event (operations.SUCCESSFUL)
        else:
            if event.id == operations.SUCCESSFUL:
                eid = operations.ERROR
                err = Exception ("Not a valid WAV PCM")
            else:
                eid = events.id
                err = events.error
                
            self._send_finished_event (eid, err)
    
    def start (self):
        self.oper.start ()
        self.__can_start = False
    
    def stop (self):
        self.oper.stop ()
        
    can_start = property (lambda self: self.__can_start)
    
    running = property (lambda self: self.__oper != None)

def fileIsPcmWav (filename):
    src = gst.element_factory_make ("filesrc")
    src.set_property ("location", filename)
    return IsWavPcm (src)
    
def sourceToWav (source, sink):
    """
    Converts a given source element to wav format and sends it to sink element.
    
    To convert a media file to a wav using gst-launch:
    source ! decodebin ! audioconvert ! audioscale !$WavPcmParse ! wavenc
    """
    bin = gst.parse_launch (
        "decodebin ! audioconvert ! audioscale ! " + WavPcmParse + " ! wavenc"
    )
    oper = GstOperation(sink, bin)
    
    elements = bin.get_list ()
    decoder = elements[0]
    encoder = elements[-1]
    
    oper.bin.add_many (source, sink)
    source.link (decoder)
    encoder.link (sink)
    
    return oper


def fileToWav (src_filename, sink_filename):
    """
    Utility function that given a source filename it converts it to a wav
    with sink_filename.
    """
    src = gst.element_factory_make ("filesrc")
    src.set_property ("location", src_filename)
    sink = gst.element_factory_make ("filesink")
    sink.set_property ("location", sink_filename)
    return sourceToWav (src, sink)

# We don't export the gvfs function if there is no gnomevfs avail
try:
    import gnomevfs
    def gvfsToWav (src_uri, sink_uri):
        "Converts a given source URI to a wav located in sink URI."
        src = gst.element_factory_make ("gnomevfssrc")
        src.set_property ("location", src_uri)
        handle = gnomevfs.Handle (sink_uri)
        sink = gst.element_factory_make ("gnomevfssink")
        sink.set_property ("handle", handle)
        return sourceToWav (src, sink)
except:
    pass

################################################################################

def extractAudioTrack (device, track_number, sink, extra = None):
    """
    Exctracts an audio track from a certain device. The 'extra' field is used
    to send extra properties to the 'cdparanoia' element.
    """
    
    bin = gst.parse_launch ("cdparanoia ! wavenc")
    bin.set_state (gst.STATE_PAUSED)
    
    TRACK_FORMAT = gst.format_get_by_nick ("track")
    assert TRACK_FORMAT != 0
    PLAY_TRACK = TRACK_FORMAT | gst.SEEK_METHOD_SET | gst.SEEK_FLAG_FLUSH

    
    elements = bin.get_list ()
    cdparanoia = elements[0]
    wavenc = elements[-1]
    
    cdparanoia.set_property ("device", device)
    
    if extra is not None:
        for key, value in extra.iteritems ():
            cdparanoia.set_property (key, value)
            
    src = cdparanoia.get_pad ("src")
    evt = gst.event_new_segment_seek (PLAY_TRACK, track_number, track_number + 1)
    src.send_event (evt)
    
    bin.add (sink)
    wavenc.link (sink)
    
    return GstOperation(sink, bin)

def extractAudioTrackFile (device, track_number, filename, extra = None):
    sink = gst.element_factory_make ("filesink")
    sink.set_property ("location", filename)
    
    return extractAudioTrack (device, track_number, sink, extra)
    
################################################################################
if __name__ == '__main__':
    import sys
    import gobject
    
#    mainloop = gobject.MainLoop ()
    class L (operations.OperationListener):
        def on_metadata (self, event, metadata):
            print metadata
            
        def on_finished (self, event):
            if event.id == operations.ABORTED:
                print "Aborted!"
                
            if event.id == operations.ERROR:
                print "Error:", event.error
            #gst.main_quit()
            mainloop.quit ()
    
    l = L()
    #f = fileToWav (sys.argv[1], sys.argv[2])
    f = fileIsPcmWav (sys.argv[1])
    print operations.syncOperation (f).id == operations.SUCCESSFUL
    #f = fileAudioMetadata (sys.argv[1])
    #f = extractAudioTrackFile ("/dev/cdrom", int(sys.argv[1]) + 1, sys.argv[2])
    #f.listeners.append (l)
    #f.start()
    #l.finished = False
    #gst.main()
#    mainloop.run ()
#    while not l.finished:
#        pass
    
