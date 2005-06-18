# Copyright (C) 2004 Tiago Cogumbreiro <cogumbreiro@users.sf.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors: Tiago Cogumbreiro <cogumbreiro@users.sf.net>

"""
This is the window widget which will contain the audio mastering widget
defined in audio_widgets.AudioMastering. 
"""

import os, os.path, gtk, gtk.glade, gobject, sys, statvfs, gnome.ui
from xml.parsers.expat import ExpatError

# Private modules
import operations, nautilusburn, gtkutil
from mastering import AudioMastering, GtkMusicList, MusicListGateway
from mastering import ErrorTrapper
from recording import RecordMusicList, RecordingMedia
from preferences import RecordingPreferences
from operations import MapProxy, OperationListener, OperationsQueue
from operations import CallableOperation
import constants

from plugins import plugins

class SerpentineError (StandardError): pass

class SerpentineCacheError (SerpentineError):
	INVALID = 1
	NO_SPACE = 2
	def __init__ (self, args):
		self.__error_id, self.__error_message = args
	
	error_id = property (lambda self: self.__error_id)
	error_message = property (lambda self: self.__error_message)
	
	def __str__ (self):
		return "[Error %d] %s" % (self.error_id, self.error_message)

class Application (operations.Operation):
	def __init__ (self):
		operations.Operation.__init__ (self)
		self.__preferences = RecordingPreferences ()
		self.__operations = []
		
		self._music_file_patterns = {}
		self._playlist_file_patterns = {}
		self._music_file_filters = None
		self._playlist_file_filters = None
		self.register_music_file_pattern ("MPEG Audio Stream, Layer III", "*.mp3")
		self.register_music_file_pattern ("Ogg Vorbis Codec Compressed WAV File", "*.ogg")
		self.register_music_file_pattern ("Free Lossless Audio Codec", "*.flac")
	
	def _load_plugins (self):
		# Load Plugins
		self.__plugins = []
		for plug in plugins:
			# TODO: Do not add plugins that throw exceptions calling this method
			self.__plugins.append (plugins[plug].create_plugin (self))
		

	preferences = property (lambda self: self.__preferences)

	operations = property (lambda self: self.__operations)

	can_stop = property (lambda self: len (self.operations) == 0)
	
	# The window is only none when the operation has finished
	can_start = property (lambda self: self.__window is not None)


	def on_finished (self, event):
		# We listen to operations we contain, when they are finished we remove them
		self.operations.remove (event.source)
		if self.can_stop:
			self.stop ()

	def stop (self):
		assert self.can_stop, "Check if you can stop the operation first."
		self.preferences.save_playlist (self.music_list)
		self.preferences.pool.clear()
		# Warn listeners
		evt = operations.FinishedEvent (self, operations.SUCCESSFUL)
		for listener in self.listeners:
			listener.on_finished (evt)
			
		# Cleanup plugins
		del self.__plugins


	def write_files (self, window = None):
		# TODO: we should add a confirmation dialog
		r = RecordingMedia (self.music_list, self.preferences, window)
		# Add this operation to the recording
		self.operations.append (r)
		r.listeners.append (self)
		return r
	
	# TODO: should these be moved to MusicList object?
	# TODO: have a better definition of a MusicList
	def add_hints_filter (self, location_filter):
		self.music_list_gw.add_hints_filter (location_filter)
		
	def remove_hints_filter (self, location_filter):
		self.music_list_gw.remove_hints_filter (location_filter)
	
	def register_music_file_pattern (self, name, pattern):
		"""Music patterns are meant to be used in the file dialog for adding
		musics to the playlist."""
		self._music_file_patterns[pattern] = name
		self._music_file_filters = None

	def register_playlist_file_pattern (self, name, pattern):
		"""Playlist patterns are meant to be used in the file dialog for adding
		playlist contents to the current playlist."""
		self._playlist_file_patterns[pattern] = name
		self._playlist_file_filters = None
	
	def __gen_file_filters (self, patterns, all_filters_name):
		all_musics = gtk.FileFilter ()
		all_musics.set_name (all_filters_name)
		
		filters = [all_musics]
		
		for pattern, name in patterns.iteritems ():
			all_musics.add_pattern (pattern)
			
			filter = gtk.FileFilter ()
			filter.set_name (name)
			filter.add_pattern (pattern)
			
			filters.append (filter)
		
		return filters
	
	def __get_file_filter (self, filter_attr, pattern_attr, name):
		file_filter = getattr (self, filter_attr)
		if file_filter is not None:
			return file_filter
		
		setattr (
			self,
			filter_attr,
			self.__gen_file_filters (
				getattr (self, pattern_attr),
				name
			)
		)
		
		return getattr (self, filter_attr)
		
	music_file_filters = property (
		lambda self: self.__get_file_filter (
			"_music_file_filters",
			"_music_file_patterns",
			"Supported files"
		)
	)

	playlist_file_filters = property (
		lambda self: self.__get_file_filter (
			"_playlist_file_filters",
			"_playlist_file_patterns",
			"Playlists"
		)
	)

	
	# a list of filenames, can be URI's
	add_files = lambda self, files: self.music_list_gw.add_files (files)

class HeadlessApplication (Application):
	
	class Gateway (MusicListGateway):
		def __init__ (self):
			MusicListGateway.__init__ (self)
			self.music_list = GtkMusicList ()
		
		class Handler:
			def prepare_queue (self, gateway, queue):
				self.trapper = ErrorTrapper (None)
			
			def prepare_add_file (self, gateway, add_file):
				add_file.listeners.append (self.trapper)
				
			def finish_queue (self, gateway, queue):
				queue.append (self.trapper)
				del self.trapper
		

	def __init__ (self):
		Application.__init__ (self)
		self.music_list_gw = HeadlessApplication.Gateway ()
		self._load_plugins ()

	music_list = property (lambda self: self.music_list_gw.music_list)
	

def write_files (app, files):
	"""Helper function that takes a Serpentine application adds the files
	to the music list and writes them. When no `app` is provided a
	HeadlessApplication is created."""
	files = map (os.path.abspath, files)
	queue = OperationsQueue ()
	queue.append (app.add_files (files))
	queue.append (CallableOperation (lambda: app.write_files().start()))
	queue.start ()

class SerpentineApplication (Application):
	"""When no operations are left in SerpentineApplication it will exit.
	An operation can be writing the files to cd or showing the main window.
	This enables us to close the main window and continue showing the progress
	dialog. This object should be simple enough for D-Bus export.
	"""
	def __init__ (self):
		Application.__init__ (self)
		self.__window = SerpentineWindow (self)
		self.preferences.dialog.set_transient_for (self.window_widget)
		self.__window.listeners.append (self)
		self._load_plugins ()


	window_widget = property (lambda self: self.__window)
	
	music_list = property (lambda self: self.window_widget.music_list)

	music_list_gw = property (lambda self: self.window_widget.masterer.music_list_gateway)
	
	def write_files (self):
		return Application.write_files (self, self.window_widget)
	
	# TODO: decouple the window from SerpentineApplication ?
	def show_window (self):
		# Starts the window operation
		self.__window.start ()
		self.operations.append (self.__window)
	
	def close_window (self):
		# Stops the window operation
		if self.__window.running:
			self.__window.stop ()
	
	def stop (self):
		# Clean window object
		Application.stop (self)
		self.__window.destroy ()
		del self.__window
		

class PlaylistWidgets:
	pass

import weakref

class GladeComponent (object):
	def __init__ (self, parent, glade_file):
		self.__parent = weakref.ref (parent)
	
	parent = property (lambda self: self.__parent())

class FileDialogComponent (GladeComponent):
	def __init__ (self, parent, g):
		super (FileDialogComponent, self).__init__ (parent, g)
		
		# Open playlist file dialog
		self.file_dlg = gtk.FileChooserDialog (buttons = (gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		self.file_dlg.set_title ("")
		self.file_dlg.set_transient_for (self.parent)
		self.__file_filters = None
		self._setup (g)
		
	
	def _setup (self, g):
		pass
	
	def run_dialog (self, *args):
		# Triggered by add button
		# update file filters
		self.__sync_file_filters ()
		
		if self.file_dlg.run () == gtk.RESPONSE_OK:
			self._on_response_ok ()
		
		self._on_response_fail ()
		
		self.file_dlg.unselect_all()
		self.file_dlg.hide()
	
	def _on_response_ok (self):
		pass
	
	def _on_response_fail (self):
		pass
	
	def _get_file_filter (self):
		raise NotImplementedError
	
	def __sync_file_filters (self):
		file_filters = self._get_file_filters ()
				
		if file_filters == self.__file_filters:
			return
		
		# Remove old filters
		for filter in self.file_dlg.list_filters ():
			self.file_dlg.remove_filter (filter)
			
		self.__file_filters = file_filters

		# Add new filters
		for filter in file_filters:
			self.file_dlg.add_filter (filter)

class AddFileComponent (FileDialogComponent):
	def _setup (self, g):
		g.get_widget ("add").connect ("clicked", self.run_dialog)
		g.get_widget ("add_mni").connect ("activate", self.run_dialog)
		
		self.file_dlg.set_select_multiple (True)
		
	def _on_response_ok (self):
		files = self.file_dlg.get_uris()
		self.parent.music_list_widget.music_list_gateway.add_files (files).start ()

	_get_file_filters = lambda self: self.parent.application.music_file_filters

	
class PlaylistComponent (FileDialogComponent):
	def _setup (self, g):
		g.get_widget ("open_playlist_mni").connect ("activate", self.run_dialog)
	
	
	_get_file_filters = lambda self: self.parent.application.playlist_file_filters

	def _on_response_ok (self):
		playlist = self.file_dlg.get_uri()
		self.parent.music_list_widget.music_list_gateway.add_files ([playlist]).start ()
		self.parent.clear_files ()

class SerpentineWindow (gtk.Window, OperationListener, operations.Operation):
	# TODO: finish up implementing an Operation
	components = (AddFileComponent, PlaylistComponent)
	
	def __init__ (self, application):
		gtk.Window.__init__ (self, gtk.WINDOW_TOPLEVEL)
		operations.Operation.__init__ (self)
		components = []
			
		self.__application = application
		self.__masterer = AudioMastering ()
		# Variable related to this being an Operation
		self.__running = False
		self.connect ("show", self.__on_show)
		# We listen for GtkMusicList events
		self.music_list_widget.listeners.append (self)

		glade_file = os.path.join (constants.data_dir, "serpentine.glade")
		g = gtk.glade.XML (glade_file, "main_window_container")

		for c in SerpentineWindow.components:
			components.append (c(self, g))
		self.__components = components

		self.add (g.get_widget ("main_window_container"))
		self.set_title ("Serpentine")
		self.set_default_size (450, 350)
		
		
		# record button
		g.get_widget("burn").connect ("clicked", self.__on_write_files)
		g.get_widget ("write_to_disc_mni").connect ("activate", self.__on_write_files)
		
		# masterer widget
		box = self.get_child()
		self.music_list_widget.show()
		box.add (self.music_list_widget)
		
		# preferences
		g.get_widget ("preferences_mni").connect ("activate", self.__on_preferences)
		
		# setup remove buttons
		self.remove = MapProxy ({'menu': g.get_widget ("remove_mni"),
		                         'button': g.get_widget ("remove")})

		self.remove["menu"].connect ("activate", self.__on_remove_file)
		self.remove["button"].connect ("clicked", self.__on_remove_file)
		self.remove.set_sensitive (False)
		
		# setup record button
		self.__on_write_files = g.get_widget ("burn")
		self.__on_write_files.set_sensitive (False)
		
		# setup clear buttons
		self.clear = MapProxy ({'menu': g.get_widget ("clear_mni"),
		                        'button': g.get_widget ("clear")})
		self.clear['button'].connect ("clicked", self.clear_files)
		self.clear['menu'].connect ("activate", self.clear_files)
		self.clear.set_sensitive (False)
		
		# setup quit menu item
		g.get_widget ("quit_mni").connect ("activate", self.stop)
		self.connect("delete-event", self.stop)
		
		# About dialog
		g.get_widget ("about_mni").connect ("activate", self.__on_about)
		
		# update buttons
		self.on_contents_changed()
		
		if self.__application.preferences.drive is None:
			gtkutil.dialog_warn ("No recording drive found", "No recording drive found on your system, therefore some of Serpentine's functionalities will be disabled.", self)
			g.get_widget ("preferences_mni").set_sensitive (False)
			self.__on_write_files.set_sensitive (False)
	
		# Load internal XSPF playlist
		self.__load_playlist()
		
	music_list_widget = property (lambda self: self.__masterer)
	
	music_list = property (lambda self: self.__masterer.music_list)
	
	can_start = property (lambda self: True)
	# TODO: handle the can_stop property better
	can_stop = property (lambda self: True)
	
	masterer = property (lambda self: self.__masterer)
	
	application = property (lambda self: self.__application)
	
	def __on_show (self, *args):
		self.__running = True
	
	def __load_playlist (self):
		#TODO: move it to SerpentineApplication ?
		"""Private method for loading the internal playlist."""
		try:
			self.__application.preferences.load_playlist (self.music_list_widget.source)
		except ExpatError:
			pass
		except IOError:
			pass
			
	def on_selection_changed (self, *args):
		self.remove.set_sensitive (self.music_list_widget.count_selected() > 0)
		
	def on_contents_changed (self, *args):
		is_sensitive = len(self.music_list_widget.source) > 0
		self.clear.set_sensitive (is_sensitive)
		# Only set it sentitive if the drive is available and is not recording
		if self.__application.preferences.drive is not None:
			self.__on_write_files.set_sensitive (is_sensitive)

	def __on_remove_file (self, *args):
		self.music_list_widget.remove_selected()
		
	def clear_files (self, *args):
		self.music_list_widget.source.clear()
	
	def __on_preferences (self, *args):
		# Triggered by preferences menu item
		self.__application.preferences.dialog.run ()
		self.__application.preferences.dialog.hide ()
	
	def __on_about (self, widget, *args):
		# Triggered by the about menu item
		a = gtk.AboutDialog ()
		a.set_name ("Serpentine")
		a.set_version (self.__application.preferences.version)
		a.set_website ("http://s1x.homelinux.net/projects/serpentine")
		a.set_copyright ("2004-2005 Tiago Cogumbreiro")
		a.set_transient_for (self)
		a.run ()
		a.hide()
	
	def __on_write_files (self, *args):
		# TODO: move this to SerpentineApplication.write_files ?
		try:
			# Try to validate music list
			validate_music_list (self.music_list_widget.source, self.__application.preferences)
		except SerpentineCacheError, err:
			show_prefs = False
			
			if err.error_id == SerpentineCacheError.INVALID:
				title = "Cache directory location unavailable"
				show_prefs = True
				
			elif err.error_id == SerpentineCacheError.NO_SPACE:
				title = "Not enough space on cache directory"
			
			gtkutil.dialog_warn (title, err.error_message)
			return

		# TODO: move this to recording module?
		if self.music_list_widget.source.total_duration > self.music_list_widget.disc_size:
			title = "Do you want to overburn your disc?"
			msg = "You are about to record a media disc in overburn mode. " \
			      "This may not work on all drives and shouldn't give you " \
			      "more then a couple of minutes."
			btn = "Overburn Disk"
			self.__application.preferences.overburn = True
		else:
			title = "Do you want to record your musics?"
			msg = "You are about to record a media disc. " \
			      "Canceling a writing operation will make your disc unusable."
			btn = "Record Disk"
			self.__application.preferences.overburn = False
		
		if gtkutil.dialog_ok_cancel (title, msg, self, btn) != gtk.RESPONSE_OK:
			return
		
		self.__application.write_files ().start ()
	
	# Start is the same as showing a window, we do it every time
	start = gtk.Window.show

	def stop (self, *args):
		evt = operations.FinishedEvent (self, operations.SUCCESSFUL)
		for listener in self.listeners:
			listener.on_finished (evt)
		self.hide ()
	

def __hig_bytes (bytes):
	hig_desc = [("GByte", "GBytes"),
	            ("MByte", "MBytes"),
	            ("KByte", "KByte" ),
	            ("byte" , "bytes" )]
	value, strings = __decompose_bytes (bytes, 30, hig_desc)
	return "%.1f %s" % (value, __plural (value, strings))

def __decompose_bytes (bytes, offset, hig_desc):
	if bytes == 0:
		return (0.0, hig_desc[-1:])
	if offset == 0:
		return (float (bytes), hig_desc[-1:])
		
	part = bytes >> offset
	if part > 0:
		sub_part = part ^ ((part >> offset) << offset)
		return ((part * 1024 + sub_part) / 1024.0, hig_desc[0])
	else:
		del hig_desc[0]
		return __decompose_bytes (bytes, offset - 10, hig_desc)

def __plural (value, strings):
	if value == 1:
		return strings[0]
	else:
		return strings[1]

def validate_music_list (music_list, preferences):
	# Check if we have space available in our cache dir
	secs = 0
	for music in music_list:
		# When music is not available it will have to be converted
		if not preferences.pool.is_available (music["location"]):
			secs += music["duration"]
	# 44100hz * 16bit * 2channels / 8bits = 176400 bytes per sec
	size_needed = secs * 176400L
	
	# Now check if cache location is ok
	try:
		s = os.statvfs (preferences.temporary_dir)
		# Raise exception if temporary dir is not ok
		assert preferences.temporary_dir_is_ok
	except OSError, AssertionError:
		raise SerpentineCacheError (SerpentineCacheError.INVALID, "Please "    \
		                            "check if the cache location exists and "  \
		                            "has writable permissions.")
	
	size_avail = s[statvfs.F_BAVAIL] * long(s[statvfs.F_BSIZE])
	if (size_avail - size_needed) < 0:
		raise SerpentineCacheError (SerpentineCacheError.NO_SPACE, "Remove "   \
		                            "some music tracks or make sure your "     \
		                            "cache location location has enough free " \
		                            "space (about %s)." \
		                            % __hig_bytes(size_needed - size_avail))

gobject.type_register (SerpentineWindow)

if __name__ == '__main__':
	s = Serpentine ()
	s.preferences.simulate = len(sys.argv) == 2 and sys.argv[1] == '--simulate'
	s.show()
	gtk.main()
