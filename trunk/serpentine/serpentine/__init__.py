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
from mastering import AudioMastering
from recording import RecordMusicList, RecordingMedia
from preferences import RecordingPreferences
from operations import MapProxy, OperationListener
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

class SerpentineApplication (operations.Operation):
	"""When no operations are left in SerpentineApplication it will exit.
	An operation can be writing the files to cd or showing the main window.
	This enables us to close the main window and continue showing the progress
	dialog. This object should be simple enough for D-Bus export.
	"""
	def __init__ (self):
		operations.Operation.__init__ (self)
		self.__preferences = RecordingPreferences ()
		self.__window = SerpentineWindow (self)
		self.__window.listeners.append (self)
		# Load Plugins
		self.__plugins = []
		for plug in plugins:
			# TODO: Do not add plugins that throw exceptions calling this method
			self.__plugins.append (plugins[plug].create_plugin (self))
		self.__operations = []

	window_widget = property (lambda self: self.__window)
	
	operations = property (lambda self: self.__operations)
	
	preferences = property (lambda self: self.__preferences)
	
	music_list = property (lambda self: self.__window.music_list)
	
	can_stop = property (lambda self: len (self.operations) == 0)
	
	# The window is only none when the operation has finished
	can_start = property (lambda self: self.__window is not None)
	
	# TODO: decouple the window from SerpentineApplication ?
	def show_window (self):
		# Starts the window operation
		self.__window.start ()
		self.operations.append (self.__window)
	
	def close_window (self):
		# Stops the window operation
		if self.__window.running:
			self.__window.stop ()
	
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
			
		# Clean window object
		self.__window.destroy ()
		del self.__window
		self.__window = None
		
		# Cleanup plugins
		del self.__plugins
	
	def write_files (self):
		# TODO: we should add a confirmation dialog
		r = RecordingMedia (self.music_list, self.preferences, self.__window)
		# Add this operation to the recording
		self.operations.append (r)
		r.listeners.append (self)
		r.start()
	
	# TODO: should these be moved to MusicList object?
	# TODO: have a better definition of a MusicList
	def add_hints_filter (self, location_filter):
		self.__window.music_list_widget.add_hints_filter (location_filter)
		
	def remove_hints_filter (self, location_filter):
		self.__window.music_list_widget.remove_hints_filter (location_filter)
		
class SerpentineWindow (gtk.Window, OperationListener, operations.Operation):
	# TODO: finish up implementing an Operation
	def __init__ (self, application):
		gtk.Window.__init__ (self, gtk.WINDOW_TOPLEVEL)
		operations.Operation.__init__ (self)
		self.__application = application
		self.__masterer = AudioMastering ()
		# Variable related to this being an Operation
		self.__running = False
		self.connect ("show", self.__on_show)
		# We listen for GtkMusicList events
		self.music_list_widget.listeners.append (self)

		glade_file = os.path.join (constants.data_dir, "serpentine.glade")
		g = gtk.glade.XML (glade_file, "main_window_container")
		self.add (g.get_widget ("main_window_container"))
		self.set_title ("Serpentine")
		self.set_default_size (450, 350)
		
		# Add a file button
		g.get_widget ("add").connect ("clicked", self.__on_add_file)
		g.get_widget ("add_mni").connect ("activate", self.__on_add_file)
		
		# record button
		g.get_widget("burn").connect ("clicked", self.__on_write_files)
		
		# masterer widget
		box = self.get_child()
		self.music_list_widget.show()
		box.add (self.music_list_widget)
		
		# preferences
		g.get_widget ("preferences_mni").connect ('activate', self.__on_preferences)
		
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
		g.get_widget ("quit_mni").connect ('activate', self.stop)
		self.connect("delete-event", self.stop)
		
		# About dialog
		g.get_widget ("about_mni").connect ('activate', self.__on_about)
		
		self.__last_path = None
		self.__add_file = gtk.FileChooserDialog (buttons = (gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
		self.__add_file.set_title ('')
		self.__add_file.set_select_multiple (True)
		
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
		
	def __on_add_file (self, *args):
		# Triggered by add button
		if self.__add_file.run () == gtk.RESPONSE_OK:
			files = self.__add_file.get_uris()
			hints_list = []
			for uri in files:
				hints_list.append({'location': uri})
			self.music_list_widget.add_files (hints_list)
		self.__add_file.unselect_all()
		self.__add_file.hide()
	
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
		
		self.__application.write_files ()
	
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
