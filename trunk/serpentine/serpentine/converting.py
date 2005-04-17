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

""""
This module is used to convert audio data to local WAV files. These files
are cached in the local filesystem and can be used by the recording module.
"""
import operations

class GetMusic (operations.MeasurableOperation, operations.OperationListener):
	""""
	A Measurable Operation that finishes when the filename is available in the 
	music pool.
	"""
	def __init__ (self, pool, music):
		operations.MeasurableOperation.__init__ (self)
		self.__music = music
		self.__pool = pool
		self.__oper = None
		
	progress = property (lambda self: self.__oper and self.__oper.progress)
	running = property (lambda self: self.__oper and self.__oper.running)
	
	can_stop = property (lambda self: self.__oper and self.__oper.can_stop)
	
	music = property (lambda self: self.__music)
	
	pool = property (lambda self: self.__pool)
	
	def start (self):
		if self.__pool.is_available (self.__music):
			self.__done ()
			self.__oper = None
		else:
			try:
				self.__oper = self.__pool.fetch_music (self.__music)
				self.__oper.listeners.append (self)
				self.__oper.start()
			except Exception, e:
				evt = operations.FinishedEvent (self, operations.ERROR)
				evt.error = e
				for l in self.listeners:
					l.on_finished (evt)
	
	def __done (self, success = operations.SUCCESSFUL):
		e = operations.FinishedEvent (self, success)
		for l in self.listeners:
			l.on_finished (e)
	
	def on_finished (self, event):
		self.__done (event.id)
		self.__oper = None
	
	def stop (self):
		assert self.__oper
		self.__oper.stop ()

class MusicPool:
	"""
	A music pool is basically a place where you put your music to convert it
	to local WAV files which will then be used to create audio CDs.
	"""
	def __init__ (self):
		raise NotImplementedError
		
	def fetch_music (self, music):
		"""
		Returns a operations.MeasurableOperation that correspondes the user
		can use to monitor it's progress.
		"""
		raise NotImplementedError
	
	def fetch_musics (self, musics):
		return FetchMusics (self, musics)
	
	def is_available (self, music):
		"""
		Returns if a certain music is on cache.
		"""
		raise NotImplementedError
	
	def get_filename (self, music):
		"""
		Returns the filename associated with a certain music in cache. The user
		must be sure that the file is in cache.
		"""
		raise NotImplementedError
	
	def clear (self):
		"""
		Clears the pool of it's elements.
		"""
		raise NotImplementedError

################################################################################
# GStreamer implementation
#

import tempfile, os
import gst
import audio

class GstCacheEntry:
	def __init__ (self, filename, is_temp):
		self.is_temp = is_temp
		self.filename = filename

class GstSourceToWavListener (operations.OperationListener):
	def __init__ (self, parent, filename, music):
		self.__filename = filename
		self.__music = music
		self.__parent = parent
	
	def on_finished (self, event):
		if event.id == operations.SUCCESSFUL:
			self.__parent.cache[self.__parent.unique_music_id (self.__music)] = GstCacheEntry (self.__filename, True)
		else:
			os.unlink (self.__filename)
		
class GstMusicPool (MusicPool):
	def __init__ (self):
		self.__cache = {}
		self.__temp_dir = None

	# read-only
	cache = property (lambda self: self.__cache)
	
	def __set_temp_dir (self, temp_dir):
		assert temp_dir == None or isinstance (temp_dir, str), "Directory must be a string. Or None for default."
		self.__temp_dir = temp_dir
		
	
	temporary_dir = property (lambda self: self.__temp_dir, __set_temp_dir)
	
	def is_available (self, music):
		return self.cache.has_key (self.unique_music_id (music))
	
	def get_filename (self, music):
		assert self.is_available (music)
		return self.cache[self.unique_music_id (music)].filename
		
	def get_source (self, music):
		raise NotImplementedError
	
	def fetch_music (self, music):
		"""
		Can throw a OSError exception in case of the provided temporary dir being
		invalid.
		"""
		assert not self.is_available (music)
		source = self.get_source (music)
		sink = gst.element_factory_make ("filesink", "destination")
		
		handle, filename = tempfile.mkstemp(suffix = '.wav', dir = self.temporary_dir)
		os.close (handle)
		sink.set_property ("location", filename)
		
		our_listener = GstSourceToWavListener (self, filename, music)
		oper = audio.source_to_wav (source, sink)
		oper.listeners.append (our_listener)
		return oper

	def clear (self):
		for key in self.cache:
			entry = self.cache[key]
			if entry.is_temp:
				os.unlink (entry.filename)
		self.__cache = {}
		
	def __del__ (self):
		self.clear()
	
	def unique_music_id (self, music):
		pass
	
import urllib
from urlparse import urlparse, urlunparse
import gnomevfs

class GvfsMusicPool (GstMusicPool):
	def unique_music_id (self, uri):
		"""
		Provides a way of uniquely identifying URI's, in case of user sends:
		file:///foo%20bar
		file:///foo bar
		/foo bar
		Returns always a URL, even if the string was a file path.
		"""
		s = urlparse (uri)
		scheme = s[1]
		path = s[2]
		# Just unparse in case we are handling a URL
		if scheme != '':
			# Remove %20
			path = urllib.unquote(path)
		s = list(s)
		# If it was a file path convert it to a file scheme
		if scheme == '':
			s[1] = 'file'
		s[2] = path
		return urlunparse (s)
		
	def is_available (self, music):
		on_cache = GstMusicPool.is_available (self, music)
		uri = gnomevfs.URI (music)
		if not on_cache and \
					uri.is_local and \
					gnomevfs.get_mime_type (music) == 'audio/x-wav':
			# convert to native filename
			unique_id = self.unique_music_id (music)
			s = urlparse (unique_id)
			filename = s[2]
			self.cache[unique_id] = GstCacheEntry (filename, False)
			on_cache = True
		del uri
		return on_cache
	
	def get_source (self, music):
		src = gst.element_factory_make ("gnomevfssrc", "source")
		src.set_property ("location", music)
		return src

class FetchMusicListPriv (operations.OperationListener):
	def __init__ (self, parent, music_list):
		self.music_list = music_list
		self.parent = parent
	
	def get_music_from_uri (self, uri):
		for m in self.music_list:
			if m["location"] == uri:
				return m
		return None
	
	def on_finished (self, evt):
		if isinstance (evt.source, operations.OperationsQueue):
			e = operations.FinishedEvent (self.parent, evt.id)
			for l in self.parent.listeners:
				l.on_finished (e)
			return
		assert isinstance (evt.source, GetMusic)
		if evt.id != operations.SUCCESSFUL:
			return
			
		uri = evt.source.music
		pool = evt.source.pool
		filename = pool.get_filename (uri)
		m = self.get_music_from_uri (uri)
		if m:
			m["cache_location"] = filename
		else:
			assert False, "uri '%s' was not found in music list." % (uri)
	
	def before_operation_starts (self, event, operation):
		e = operations.Event (self.parent)
		m = self.get_music_from_uri (operation.music)
		assert m
		
		for l in self.parent.listeners:
			if isinstance (l, FetchMusicListListener):
				l.before_music_fetched (e, m)


class FetchMusicListListener (operations.OperationListener):
	def before_music_fetched (self, event, music):
		pass
	

class FetchMusicList (operations.MeasurableOperation):
	"""
	Fetches a music list which contains the field 'uri' and replaces it by a
	local filename located inside the pool. When the filename is fetched it
	updates the 'filename' field inside each music entry of the music list.
	"""
	
	def __init__ (self, music_list, pool):
		operations.MeasurableOperation.__init__(self)
		self.__music_list = music_list
		self.__queue = operations.OperationsQueue ()
		self.__pool = pool
		self.__listener = FetchMusicListPriv (self, music_list)
		self.__queue.listeners.append (self.__listener)
		
	progress = property (lambda self: self.__queue.progress)
	running = property (lambda self: self.__queue.running)
	
	def start (self):
		for m in self.__music_list:
			get = GetMusic (self.__pool, m["location"])
			get.listeners.append (self.__listener)
			self.__queue.append (get)
		self.__queue.start ()
	
	can_stop = property (lambda self: self.__queue.can_stop)
	
	def stop (self):
		self.__queue.stop ()

if __name__ == '__main__':
	import os.path, sys, gtk, gobject, gtkutil
	def quit ():
		#gtk.main_quit()
		return False
	
	def pp (oper):
		p = oper.get_progress()
		print p
		if p == 1:
			gtk.main_quit()
		return True
		
	class MyListener (FetchMusicListListener):
		def __init__ (self, prog, oper):
			FetchMusicListListener.__init__(self)
			self.music = None
			self.prog = prog
			self.oper = oper
			
		def before_music_fetched (self, evt, music):
			print music
			prog_txt = "Converting "
			prog_txt += gnomevfs.URI (music['uri']).short_path_name
			
			self.prog.set_sub_progress_text (prog_txt)
			self.prog.set_progress_fraction (self.oper.progress)
			
			if self.music:
				print "Fetched", self.music['filename']
				
			print "Fetching", music['uri']
			self.music = music
			
		def on_finished (self, e):
			if self.music:
				print "Fetched", self.music['filename']
			print self.oper.progress
			#self.prog.set_progress_fraction (self.oper.progress)
			#gtk.main_quit()
		
		def tick (self):
			self.prog.set_progress_fraction (self.oper.progress)
			return True
	
#	win = gtk.Window (gtk.WINDOW_TOPLEVEL)
	prog = gtkutil.HigProgress ()
	prog.set_primary_text ("Recording Audio Disc")
	prog.set_secondary_text ("Selected files are to be written to a CD or DVD disc. This operation may take a long time, depending on data size and write speed.")
	prog.show()
#	win.add (prog)
#	win.set_border_width (6)
#	win.show()
	pool = GvfsMusicPool ()
	#f = os.path.abspath (sys.argv[1])
	music_list = [{'uri': 'file://' + os.path.abspath (sys.argv[1])}]
	fetcher = FetchMusicList (music_list, pool)
	l = MyListener (prog, fetcher)
	fetcher.listeners.append (l)
	gobject.timeout_add (200, l.tick)
	fetcher.start()
	
	gtk.main()
	pool.clear()
