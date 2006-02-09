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
#          Alessandro Decina <alessandro@nnva.org>

"""
This module contains operations to convert sound files to WAV and to
retrieve a their metadata.
"""

import threading
import gst
import gobject
import operations

class GstPlayingFailledError(StandardError):
    """This error is thrown when we can't set the state to PLAYING"""
    
class GstOperationListener (operations.OperationListener):
    def on_tag (self, event, tag):
        """Called when a tag is found"""

    def on_eos (self, event):
        """Called when the pipeline reaches EOS."""

    def on_error (self, event, error):
        """Called when an error occurs"""
   
class GstPipelineOperation (operations.MeasurableOperation):
    """GStreamer pipeline operation"""

    can_start = property (lambda self: self.__can_start)
    running = property (lambda self: self.__running)
    bin = property (lambda self: self.__bin)
    query_element = None
    progress = property (lambda self: self._get_progress ())
    
    def __init__ (self, query_element, pipeline):
        super (GstPipelineOperation, self).__init__ ()

        self.query_element = query_element
        self.__bin = pipeline
        self.__progress = 0.0
        self.__can_start = True
        self.__running = False
        self.__duration = 0

    def start (self):
        assert self.can_start
        if self.bin.set_state (gst.STATE_PLAYING):
            self.__can_start = False
            self.__running = True
        else:
            raise GstPlayingFailledError()

    def stop (self):
        self._finalize (operations.ABORTED)

    def query_duration (self, format = gst.FORMAT_BYTES):
        """Return the total duration"""
        return 0.0

    def query_position (self, format = gst.FORMAT_BYTES):
        """Return the current position"""
        return 0
    
    # implementation methods
    def _finalize (self, event_id, error = None):
        # set state to NULL and notify the listeners
        if self.__running:
            self.bin.set_state (gst.STATE_NULL)
            self.__running = False
            self._send_finished_event (event_id, error)
        # Notice that GstOperations are run-once.

    def _get_progress (self):
        # get the current progress
        if self.query_element and self.__progress < 1: 
            if not self.__duration:
                self.__duration = self.query_duration ()
            if self.__duration == 0:
                progress = 0
            else:
                position = self.query_position ()
                progress = self.query_position () / self.__duration

            self.__progress = max (self.__progress, progress)
            assert 0 <= self.__progress <= 1, self.__progress
            
        return self.__progress

    def _on_eos (self):
        event = operations.Event (self)
        self._notify ("on_eos", event)
        self._finalize (operations.SUCCESSFUL)

    def _on_error (self, error):
        event = operations.Event (self)
        self._notify ("on_error", event, error)
        self._finalize (operations.ERROR, error)

    def _on_tag (self, taglist):
        event = operations.Event (self)
        self._notify ("on_tag", event, taglist)

class Gst08Operation (GstPipelineOperation):
    """Implement GstPipelineOperation with gstreamer 0.8 API"""
    def __init__ (self, query_element = None, pipeline = None,
                use_threads = False):
        
        if pipeline is None:
            pipeline = use_threads and gst.Thread () or gst.Pipeline ()
        
        super (Gst08Operation, self).__init__ (query_element, pipeline)
        
        self.__use_threads = use_threads
        pipeline.connect ("found-tag", self._on_tag)
        pipeline.connect ("error", self._on_error)
        pipeline.connect ("eos", self._on_eos)
        self.__source = None

    def start (self):
        super (Gst08Operation, self).start ()
        if self.running and not self.__use_threads:
                self.__source = gobject.idle_add (self.bin.iterate)

    def stop (self):
        if self.__source is not None:
            gobject.source_remove (self.__source)
            self.__source = None
        super (Gst08Operation, self).stop ()
 
    def query_duration (self, format = gst.FORMAT_TIME):
        return float (self.query_element.query(gst.QUERY_TOTAL, format))

    def query_position (self, format = gst.FORMAT_TIME):
        return self.query_element.query (gst.QUERY_POSITION, format)

    def _on_error (self, pipeline, element, error, user_data = None):
        super (Gst08Operation, self)._on_error (error)
    
    def _on_tag (self, pipeline, element, taglist):
        super (Gst08Operation, self)._on_tag (taglist)

    def _on_eos (self, pipeline):
        super (Gst08Operation, self)._on_eos ()

    def _finalize (self, event_id, error = None):
        super (Gst08Operation, self)._finalize (event_id, error)
        if self.__source is not None:
            gobject.source_remove (self.__source)
            self.__source = None


class Gst09Operation (GstPipelineOperation):
    """Implement GstPipelineOperation with gstreamer 0.9/0.10 API"""
    running = property (lambda self: self.__running)

    def __init__ (self, query_element = None, pipeline = None):
        if pipeline is None:
            pipeline = gst.Pipeline ()
        
        super (Gst09Operation, self).__init__ (query_element, pipeline)

        self.bus = pipeline.get_bus ()
        self.bus.add_watch (self._dispatch_bus_message)
        self.__running = False
        
        # the operation can be started/stopped in the main thread, when start()
        # or stop() are called inside serpentine, and in the stream thread,
        # when .stop() is called in on_handoff. start() and _finalize() are thus
        # synchronized with self.lock
        self.lock = threading.RLock ()
 
    def query_duration (self, format = gst.FORMAT_TIME):
        try:
            total, format = self.query_element.query_duration (format)
            return float (total)
        except gst.QueryError, e:
            return 0.0

    def query_position (self, format = gst.FORMAT_TIME):
        try:
            pos, format = self.query_element.query_position (format)
            return pos
        except gst.QueryError:
            return 0
    
    def start (self):
        self.lock.acquire ()
        try:
            if not self.__running:
                self.__running = True
                super (Gst09Operation, self).start ()
        finally:
            self.lock.release ()

    def _dispatch_bus_message (self, bus, message):
        handler = getattr (self, "_on_" + message.type.first_value_nick, None)
        if handler:
            handler (bus, message)

        return True
   
    def _finalize (self, event_id, error = None):
        self.lock.acquire ()
        try:
            if self.running:
                self.__running = False
                # finalize the pipeline in the main thread to avoid deadlocks
                def wrapper ():
                    super (Gst09Operation, self)._finalize (event_id, error)
                    return False

                gobject.idle_add (wrapper)
        finally:
            self.lock.release ()

    def _on_eos (self, bus, message):
        super (Gst09Operation, self)._on_eos ()

    def _on_error (self, bus, message):
        super (Gst09Operation, self)._on_error (message.parse_error ()) 

    def _on_tag (self, bus, message):
        super (Gst09Operation, self)._on_tag (message.parse_tag ())

if gst.gst_version[0] == 0 and gst.gst_version[1] >= 9:
    # use Gst09Operation with gstreamer >= 0.9
    NEW_PAD_SIGNAL = "pad-added"
    GstOperation = Gst09Operation
else:
    # use Gst08Operation with gstreamer < 0.9
    NEW_PAD_SIGNAL = "new-pad"
    GstOperation = Gst08Operation

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

class AudioMetadata (operations.Operation, GstOperationListener):
    """Returns the metadata associated with the source element.
    
    To retrieve the metadata associated with a certain media file on gst-launch -t:
    source ! decodebin ! fakesink
    """

    can_start = property (lambda self: self.__oper.can_start)
    running = property (lambda self: self.__oper.running)

    def __init__ (self, source):
        super (AudioMetadata, self).__init__ ()
        
        # setup the metadata extracting pipeline
        bin = gst.parse_launch ("decodebin name=am_decodebin ! \
                                fakesink name=am_fakesink")
        self.__oper = GstOperation(pipeline = bin)
        # link source with decodebin
        bin.add (source)
        source.link (bin.get_by_name ("am_decodebin"))
        # set fakesink as the query_element
        self._fakesink = bin.get_by_name ("am_fakesink")
        self._fakesink.set_property ("signal-handoffs", True)
        self._fakesink.connect ("handoff", self.on_handoff)
        self.__oper.query_element = self._fakesink
        self.__oper.listeners.append (self) 
        self.__metadata = {}

    def start (self):
        self.__oper.start ()
    
    def stop (self):
        self._check_duration ()
        self.__oper.stop ()

    def on_eos (self, event):
        self._check_duration ()

    def on_error (self, event, message):
        # try to get the size even when there is an error
        self._check_duration ()

    def on_handoff (self, *ignored):
        self._fakesink.set_property ("signal-handoffs", False)
        self.stop ()

    def on_tag (self, event, taglist):
        self.__metadata.update (taglist)

    def on_finished (self, event):
        try:
            duration = int (self.__metadata["duration"]) / gst.SECOND
        except KeyError:
            duration = 0
        self.__metadata["duration"] = duration
        
        evt = operations.Event (self)
        self._notify ("on_metadata", evt, self.__metadata)
        
        self.__metadata = None
        self.__element = None
        self._send_finished_event (operations.SUCCESSFUL)

    def _check_duration (self):
        if not self.__metadata.has_key ("duration"):
            self.__metadata["duration"] = \
                self.__oper.query_duration (gst.FORMAT_TIME)

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


class IsWavPcm (operations.Operation, GstOperationListener):
    """
    Tests if a certain WAV is in the PCM format.
    """

    can_start = property (lambda self: self.oper.can_start)
    running = property (lambda self: self.oper.running)

    def __init__ (self, source):
        super (IsWavPcm, self).__init__ ()
    
        bin = gst.parse_launch (
            "typefind name=iwp_typefind ! \
            wavparse name=iwp_wavparse ! "
            + WavPcmParse +
            " ! fakesink name=iwp_fakesink"
        )
        
        self.oper = GstOperation(pipeline = bin)
        self.oper.listeners.append (self)
 
        decoder = bin.get_by_name ("iwp_typefind")
        
        sink = bin.get_by_name ("iwp_fakesink")
        self.oper.query_element = sink
        sink.set_property ("signal-handoffs", True)
        sink.connect ("handoff", self.on_handoff)
        
        waveparse = bin.get_by_name ("iwp_wavparse")
        waveparse.connect (NEW_PAD_SIGNAL, self.on_new_pad)
        
        self.oper.bin.add (source)
        source.link (decoder)
        
        self.isPcm = False

    def on_handoff (self, *args):
        self.oper.stop ()
    
    def on_new_pad (self, src, pad):
        caps = pad.get_caps()
        self.isWavPcm = capsIsWavPcm (caps)

    def on_finished (self, event):
        if event.id != operations.ERROR and self.isWavPcm:
            assert event.id == operations.SUCCESSFUL or event.id == operations.ABORTED
            
            self._send_finished_event (operations.SUCCESSFUL)
        else:
            if event.id == operations.SUCCESSFUL:
                eid = operations.ERROR
                err = StandardError ("Not a valid WAV PCM")
            else:
                eid = event.id
                err = event.error
                
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
fileIsPcmWav = operations.async(fileIsPcmWav)
fileIsPcmWav = operations.operation_factory(fileIsPcmWav)

def gvfsIsPcmWav(uri):
    src = gst.element_factory_make("gnomevfssrc")
    src.set_property("location", uri)
    return IsWavPcm(src)

gvfsIsPcmWav = operations.async(gvfsIsPcmWav)
gvfsIsPcmWav = operations.operation_factory(gvfsIsPcmWav)

def sourceToWav (source, sink):
    """
    Converts a given source element to wav format and sends it to sink element.
    
    To convert a media file to a wav using gst-launch:
    source ! decodebin ! audioconvert ! audioscale !$WavPcmParse ! wavenc
    """
    bin = gst.parse_launch (
        "decodebin name=stw_decodebin !"
        "audioconvert ! "
        + WavPcmParse +
        " ! wavenc name=stw_wavenc"
    )
    oper = GstOperation(sink, bin)
      
    decoder = bin.get_by_name ("stw_decodebin")
    encoder = bin.get_by_name ("stw_wavenc")
      
    oper.bin.add (source)
    oper.bin.add (sink)
    source.link (decoder)
    encoder.link (sink)
    
    return oper

sourceToWav = operations.operation_factory(sourceToWav)


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
    
    bin = gst.parse_launch ("cdparanoia name=eat_cdparanoia ! \
                            wavenc name=eat_wavenc")
    bin.set_state (gst.STATE_PAUSED)
    
    oper = GstOperation (sink, pipeline)
   
    TRACK_FORMAT = gst.format_get_by_nick ("track")
    assert TRACK_FORMAT != 0
    PLAY_TRACK = TRACK_FORMAT | gst.SEEK_METHOD_SET | gst.SEEK_FLAG_FLUSH
 
    cdparanoia = bin.get_by_name ("eat_cdparanoia")
    wavenc = bin.get_by_name ("eat_wavenc")
    
    cdparanoia.set_property ("device", device)
    
    if extra is not None:
        for key, value in extra.iteritems ():
            cdparanoia.set_property (key, value)
            
    src = cdparanoia.get_pad ("src")
    evt = gst.event_new_segment_seek (PLAY_TRACK, track_number, track_number + 1)
    src.send_event (evt)
    
    bin.add (sink)
    wavenc.link (sink)
    
    return oper

def extractAudioTrackFile (device, track_number, filename, extra = None):
    sink = gst.element_factory_make ("filesink")
    sink.set_property ("location", filename)
    
    return extractAudioTrack (device, track_number, sink, extra)
    
################################################################################
if __name__ == '__main__':
    import sys
    import gobject
    
    mainloop = gobject.MainLoop ()
    class L (GstOperationListener):
        def __init__(self, foo):
            self.foo = foo
            
        def on_metadata (self, event, metadata):
            print metadata
            
        def on_finished (self, event):
            if event.id == operations.ABORTED:
                print "Aborted!"
                
            if event.id == operations.ERROR:
                print "Error:", event.error
            #gst.main_quit()
            mainloop.quit ()

        def on_progress (self):
            #print
            self.foo.progress
            return True
    
    #f = fileToWav (sys.argv[1], sys.argv[2])
    f = gvfsIsPcmWav (sys.argv[1])
    print operations.syncOperation (f).id == operations.SUCCESSFUL
    raise SystemError
    #f = fileAudioMetadata (sys.argv[1])
    #f = extractAudioTrackFile ("/dev/cdrom", int(sys.argv[1]) + 1, sys.argv[2])
    l = L(f)
    #gobject.timeout_add (200, l.on_progress)
    f.listeners.append (l)
    f.start()
    l.finished = False
    #gst.main()

    mainloop.run ()
#    while not l.finished:
#        pass
    
