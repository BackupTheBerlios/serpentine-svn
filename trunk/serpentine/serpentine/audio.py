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
	def __init__ (self, query_element = None, pipeline = None):
		operations.MeasurableOperation.__init__ (self)
		self.__element = query_element
		self.__can_start = True
		self.__running = False
		
		# create a new bin to hold the elements
		if pipeline is None:
			self.__bin = gst.Pipeline ()
		else:
			self.__bin = pipeline 
			
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
		self.__source = gobject.idle_add (self.bin.iterate)
	
	def __on_eos (self, element, user_data = None):
		self.__finalize ()
		evt = operations.FinishedEvent (self, operations.SUCCESSFUL)
		for l in self.listeners:
			assert isinstance (l, operations.OperationListener), l
			l.on_finished (evt)
	
	def __on_error (self, pipeline, element, error, user_data = None):
		# Do not continue processing it
		if self.__source:
			gobject.source_remove (self.__source)
		self.__finalize ()
		evt = operations.FinishedEvent (self, operations.ERROR)
		evt.error = error
		for l in self.listeners:
			l.on_finished (evt)

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
		evt = operations.FinishedEvent(self, operations.ABORTED)
		for l in self.listeners:
			l.on_finished (evt)

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
	
	To retrieve the metadata associated with a certain media file on gst-launch:
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
			
		event = operations.FinishedEvent (self, success)
		for l in self.listeners:
			l.on_finished (event)
	
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
	
def file_audio_metadata (filename):
	"""
	Returns the audio metadata from a file.
	"""
	filesrc = gst.element_factory_make ("filesrc", "source")
	filesrc.set_property ("location", filename)
	return AudioMetadata(filesrc)


try:
	import gnomevfs
	def gvfs_audio_metadata (uri):
		"""
		Returns the audio metadata from an URI.
		"""
		filesrc = gst.element_factory_make ("gnomevfssrc", "source")
		filesrc.set_property ("location", uri)
		return AudioMetadata(filesrc)

except:
	pass

	
################################################################################
def source_to_wav (source, sink):
	"""
	Converts a given source element to wav format and sends it to sink element.
	
	To convert a media file to a wav using gst-launch:
	source ! decodebin ! audioconvert ! audioscale ! wavenc ! sink
	"""
	bin = gst.parse_launch ("decodebin ! audioconvert ! audioscale ! wavenc")
	oper = GstOperation(sink, bin)
	
	elements = bin.get_list ()
	decoder = elements[0]
	encoder = elements[-1]
	
	oper.bin.add_many (source, sink)
	source.link (decoder)
	encoder.link (sink)
	
	return oper


def file_to_wav (src_filename, sink_filename):
	"""
	Utility function that given a source filename it converts it to a wav
	with sink_filename.
	"""
	src = gst.element_factory_make ("filesrc")
	src.set_property ("location", src_filename)
	sink = gst.element_factory_make ("filesink")
	sink.set_property ("location", sink_filename)
	return source_to_wav (src, sink)

# We don't export the gvfs function if there is no gnomevfs avail
try:
	import gnomevfs
	def gvfs_to_wav (src_uri, sink_uri):
		"Converts a given source URI to a wav located in sink URI."
		src = gst.element_factory_make ("gnomevfssrc")
		src.set_property ("location", src_uri)
		handle = gnomevfs.Handle (sink_uri)
		sink = gst.element_factory_make ("gnomevfssink")
		sink.set_property ("handle", handle)
		return source_to_wav (src, sink)
except:
	pass

################################################################################
if __name__ == '__main__':
	import sys
	class L (operations.OperationListener):
		def on_metadata (self, event, metadata):
			print metadata
			
		def on_finished (self, event):
			if event.id == operations.ABORTED:
				print "Aborted!"
				
			if event.id == operations.ERROR:
				print "Error:", event.error
			gst.main_quit()
	
	l = L()
	f = file_to_wav (sys.argv[1], sys.argv[2])
	#f = file_audio_metadata (sys.argv[1])
	f.listeners.append (l)
	f.start()
	l.finished = False
	gst.main()
#	while not l.finished:
#		pass
	
