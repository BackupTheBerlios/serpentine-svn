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

import gtk, gtk.glade, gobject, os.path, urllib, gnomevfs
from xml.dom import minidom
from types import IntType, TupleType
from urlparse import urlparse, urlunparse

import operations, audio, xspf, constants, gtkutil
from gtkutil import DictStore
from operations import OperationsQueue

################################################################################
# Operations used on AudioMastering
#
# 

class ErrorTrapper (operations.Operation, operations.OperationListener):
	def __init__ (self, parent = None):
		operations.Operation.__init__ (self)
		self.__errors = []
		self.__parent = parent
	
	errors = property (lambda self: self.__errors)
	parent = property (lambda self: self.__parent)
	
	def on_finished (self, event):
		if event.id == operations.ERROR:
			self.errors.append (event.source)
	
	def start (self):
		if len (self.errors) == 0:
			e = operations.FinishedEvent (self, operations.SUCCESSFUL)
			for l in self.listeners:
				l.on_finished (e)
			return
				
		elif len (self.errors) > 1:
			title = "Unsupported file types"
		else:
			title = "Unsupported file type"
			
		filenames = []
		for e in self.errors:
			filenames.append (gnomevfs.URI(e.hints['location']).short_name)
		del self.__errors
		
		if len (filenames) == 1:
			msg = "The following files were not added:" + "\n"
		else:
			msg = "The following files were not added:" + "\n"
		
		msg +=  " " + filenames[0]
		
		for f in filenames[1:]:
			msg += ", " + f
		gtkutil.dialog_error (title, msg, self.parent)
		
		e = operations.FinishedEvent (self, operations.SUCCESSFUL)
		for l in self.listeners:
			l.on_finished (e)

class AddFile (audio.AudioMetadataListener, operations.Operation):
	# TODO: Implement full Operation here
	
	running = property (lambda self: False)

	def __init__ (self, music_list, hints, insert = None):
		operations.Operation.__init__ (self)
		self.hints = hints
		self.music_list = music_list
		self.insert = insert
	
	def start (self):
		oper = audio.gvfs_audio_metadata (self.hints['location'])
		oper.listeners.append (self)
		oper.start()
	
	def on_metadata (self, event, metadata):
		
		row = {
			"location": self.hints['location'],
			"cache_location": "",
			"title": gnomevfs.URI(self.hints['location'][:-4]).short_name or "Unknown",
			"artist": "Unknow Artist",
			"duration": int(metadata['duration']),
		}
		
		if metadata.has_key ('title'):
			row['title'] = metadata['title']
		if metadata.has_key ('artist'):
			row['artist'] = metadata['artist']
			
		if self.hints.has_key ('title'):
			row['title'] = self.hints['title']
		if self.hints.has_key ('artist'):
			row['artist'] = self.hints['artist']
				
		if self.insert is not None:
			self.music_list.insert (self.insert, row)
		else:
			self.music_list.append (row)
		
	
	def on_finished (self, evt):
		e = operations.FinishedEvent (self, evt.id)
		for l in self.listeners:
			l.on_finished (e)
			
 
class SetGraphicalUpdate (operations.Operation):
	def __init__ (self, masterer, update):
		operations.Operation.__init__ (self)
		self.__update = update
		self.__masterer = masterer
	
	running = property (lambda self: False)
	
	can_run = property (lambda self: True)
		
	def start (self):
		self.__masterer.update = self.__update
		if self.__update:
			self.__masterer.update_disc_usage()
		e = operations.FinishedEvent (self, operations.SUCCESSFUL)
		for l in self.listeners:
			l.on_finished (e)

################################################################################

class MusicListListener:
	def on_musics_added (self, event, rows):
		pass
	
	def on_musics_removed (self, event, rows):
		pass

class MusicList (operations.Listenable):
	def __getitem__ (self):
		pass
		
	def append_many (self, rows):
		pass
	
	def append (self, row):
		pass
	
	def insert (self, index, row):
		pass
	
	def insert_many (self, index, rows):
		pass
	
	def __len__ (self):
		pass
	
	def __delitem__ (self, index):
		pass
	
	def delete_many (self, indexes):
		pass
	
	def clear (self):
		pass
	
	def has_key (self, key):
		pass
	
	def from_playlist (self, playlist):
		rows = []
		for t in playlist.tracks:
			rows.append ({'location': t.location,
			              'duration': t.duration,
			              'title': t.title,
			              'artist': t.creator})
		self.append_many (rows)

	def to_playlist (self, playlist):
		for r in self:
			t = xspf.Track()
			t.location = r['location']
			t.duration = r['duration']
			t.title = r['title']
			t.creator = r['artist']
			playlist.tracks.append (t)
			
class GtkMusicList (MusicList):
	"Takes care of the data source. Supports events and listeners."
	SPEC = (
			# URI is used in converter
			{"name": "location", "type": gobject.TYPE_STRING},
			# filename is used in recorder
			{"name": "cache_location", "type": gobject.TYPE_STRING},
			# Remaining items are for the list
			{"name": "duration", "type": gobject.TYPE_INT},
			{"name": "title", "type": gobject.TYPE_STRING},
			{"name": "artist", "type": gobject.TYPE_STRING},
			{"name": "time", "type": gobject.TYPE_STRING})
			
	def __init__ (self):
		operations.Listenable.__init__ (self)
		self.__model = DictStore (*self.SPEC)
		self.__total_duration = 0
		self.__freezed = False
	
	model = property (fget=lambda self: self.__model, doc="Associated ListStore.")
	total_duration = property (fget=lambda self:self.__total_duration, doc="Total disc duration, in seconds.")
	
	def __getitem__ (self, index):
		return self.model.get (index)
	
	def append_many (self, rows):
		self.__freezed = True
		for row in rows:
			self.append (row)
		self.__freezed = False
		
		rows = tuple(rows)
		e = operations.Event(self)
		for l in self.listeners:
			l.on_musics_added (e, rows)
	
	def __correct_row (self, row):
		if not row.has_key ('time'):
			row['time'] = "%.2d:%.2d" % (row['duration'] / 60, row['duration'] % 60)
		if not row.has_key ('cache_location'):
			row['cache_location'] = ''
		return row
		
	def append (self, row):
		row = self.__correct_row(row)
		self.model.append (row)
		self.__total_duration += int(row['duration'])
		if not self.__freezed:
			e = operations.Event (self)
			rows = (row,)
			for l in self.listeners:
				l.on_musics_added (e, rows)
	
	def insert (self, index, row):
		row = self.__correct_row(row)
		self.model.insert_before (self.model.get_iter (index), row)
		self.__total_duration += int (row['duration'])
		
	def __len__ (self):
		return len(self.model)
	
	def __delitem__ (self, index):
		# Copy native row
		row = dict(self[index])
		del self.model[index]
		self.__total_duration -= row['duration']
		rows = (row,)
		if not self.__freezed:
			e = operations.Event (self)
			for l in self.listeners:
				l.on_musics_removed (e, rows)
	
	def delete_many (self, indexes):
		assert isinstance(indexes, list)
		rows = []
		indexes.sort()
		low = indexes[0] - 1
		# Remove duplicate entries
		for i in indexes:
			if low == i:
				indexes.remove (i)
			low = i
		# Now decrement the offsets
		for i in range (len (indexes)):
			indexes[i] -= i
		
		# Remove the elements directly
		for i in indexes:
			# Copy native row
			r = dict(self.model.get(i))
			rows.append(r)
			self.__total_duration -= r['duration']
			del self.model[i]
		
		# Warn the listeners
		rows = tuple(rows)
		e = operations.Event(self)
		for l in self.listeners:
			l.on_musics_removed (e, rows)
		
	def clear (self):
		rows = []
		for row in iter(self.model):
			# Copy each element
			rows.append(dict(row))
		
		self.model.clear()
		self.__total_duration = 0
		
		rows = tuple(rows)
		e = operations.Event (self)
		for l in self.listeners:
			l.on_musics_removed(e, rows)
	

################################################################################
# Audio Mastering widget
#	
import sys, os.path

class AudioMasteringMusicListener (MusicListListener):
	def __init__ (self, audio_mastering):
		self.__master = audio_mastering
		
	def on_musics_added (self, e, rows):
		self.__master.update_disc_usage()
	
	def on_musics_removed (self, e, rows):
		self.__master.update_disc_usage()

class HintsFilter (object):
	__priority = 0
	
	def priority (self, value):
		assert isinstance (value, int)
		self.__priority = value
		
	priority = property (lambda self: self.__priority, priority, doc="Represents " \
	"the parser priority, a higher value will give it precedence over " \
	"filters lower filters.")
	
	def filter_location (self, location):
		"""Returns a list of dictionaries of hints of a given location.
		The 'location' field is obligatory.
		
		For example if your filter parses a directory it should return a list
		of hints of each encountered file.
		"""
		raise NotImplementedError
	
	def __cmp__ (self, value):
		assert isinstance (value, HintsFilter)
		return self.priority - value.priority

class AudioMastering (gtk.VBox, operations.Listenable):
	SIZE_74 = 0
	SIZE_80 = 1
	SIZE_90 = 2

	disc_sizes = [74 * 60, 80 * 60, 90 * 60]
	
	DND_TARGETS = [
		('SERPENTINE_ROW', gtk.TARGET_SAME_WIDGET, 0),
		('text/uri-list', 0, 1),
		('text/plain', 0, 2),
		('STRING', 0, 3),
	]
	def __init__ (self):
		gtk.VBox.__init__ (self)
		operations.Listenable.__init__ (self)
		self.__disc_size = 74 * 60
		self.update = True
		self.source = GtkMusicList ()
		self.source.listeners.append (AudioMasteringMusicListener(self))
		gtk.VBox.__init__ (self)
		g = gtk.glade.XML (os.path.join (constants.data_dir, "serpentine.glade"),
		                   "audio_container")
		self.add (g.get_widget ("audio_container"))
		self.__setup_track_list (g)
		self.__setup_container_misc (g)
		# Filters
		self.__filters = []
	
	def __set_disc_size (self, size):
		assert size in AudioMastering.disc_sizes
		self.__disc_size = size
		self.__size_list.set_active (AudioMastering.disc_sizes.index(size))
		self.update_disc_usage()

	music_list = property (lambda self: self.source)
	disc_size = property (
			lambda self: self.__disc_size,
			__set_disc_size,
			doc = "Represents the disc size, in seconds.")
	
	disc_size_widget = property (lambda self: self.__size_list)
	
	def __setup_container_misc (self, g):
		self.__size_list = g.get_widget ("size_list")
		self.__usage_bar = g.get_widget ("usage_bar")
		self.__capacity_exceeded = g.get_widget ("capacity_exceeded")
		
		self.__size_list.connect ("changed", self.__on_size_changed)
		self.__size_list.set_active (AudioMastering.SIZE_74)
	
	def __setup_track_list (self, g):
		lst = g.get_widget ("track_list")
		lst.set_model (self.source.model)
		# Track value is dynamicly calculated
		r = gtk.CellRendererText()
		col = gtk.TreeViewColumn ("Track", r)
		col.set_cell_data_func (r, self.__generate_track)
		
		r = gtk.CellRendererText()
		r.set_property ('editable', True)
		r.connect ('edited', self.__on_title_edited)
		lst.append_column (col)
		col = gtk.TreeViewColumn ("Title", r, text = self.source.model.index_of("title"))
		lst.append_column (col)
		
		r = gtk.CellRendererText()
		r.set_property ('editable', True)
		r.connect ('edited', self.__on_artist_edited)
		col = gtk.TreeViewColumn ("Artist", r, text = self.source.model.index_of("artist"))
		lst.append_column (col)
		r = gtk.CellRendererText()
		col = gtk.TreeViewColumn ("Duration", r, text = self.source.model.index_of("time"))
		lst.append_column (col)
		
		# TreeView Selection
		self.__selection = lst.get_selection()
		self.__selection.connect ("changed", self.__selection_changed)
		self.__selection.set_mode (gtk.SELECTION_MULTIPLE)
		
		# Listen for drag-n-drop events
		lst.set_reorderable (True)
		#XXX pygtk bug here
		lst.enable_model_drag_source (gtk.gdk.BUTTON1_MASK,
		                              AudioMastering.DND_TARGETS,
		                              gtk.gdk.ACTION_DEFAULT |
		                              gtk.gdk.ACTION_MOVE)

		lst.enable_model_drag_dest (AudioMastering.DND_TARGETS,
		                            gtk.gdk.ACTION_DEFAULT |
		                            gtk.gdk.ACTION_MOVE)
		lst.connect ("drag_data_received", self.__on_dnd_drop)
		lst.connect ("drag_data_get", self.__on_dnd_send)
	
	def __generate_track (self, col, renderer, tree_model, treeiter, user_data = None):
		index = tree_model.get_path(treeiter)[0]
		renderer.set_property ('text', index + 1)
	
	def __on_size_changed (self, *args):
		self.disc_size = AudioMastering.disc_sizes[self.__size_list.get_active()]
	
	def __on_title_edited (self, cell, path, new_text, user_data = None):
		self.source[path]["title"] = new_text
	
	def __on_artist_edited (self, cell, path, new_text, user_data = None):
		self.source[path]["artist"] = new_text
	
	def __on_pl_entry (self, parser, uri, title, genre, hints_list):
		hints = {'location': uri}
		if title is not None:
			hints['title'] = title
		hints_list.append(hints)
	
	def __on_dnd_drop (self, treeview, context, x, y, selection, info, timestamp, user_data = None):
		data = selection.data
		hints_list = []
		
		# Insert details
		insert = None
		drop_info = treeview.get_dest_row_at_pos(x, y)
		if drop_info:
			insert, insert_before = drop_info
			assert isinstance(insert, TupleType), len(insert) == 1
			insert, = insert
			if (insert_before != gtk.TREE_VIEW_DROP_BEFORE and
			    insert_before != gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
				insert += 1
				if insert == len (self.source):
					insert = None
			del insert_before
				
		del drop_info
		
		if selection.type == 'application/x-rhythmbox-source':
			#TODO: handle rhythmbox playlists
			return
		elif selection.type == 'SERPENTINE_ROW':
			# Private row
			store, path_list = self.__selection.get_selected_rows ()
			if not path_list or len (path_list) != 1:
				return
			path, = path_list
			# Copy the row
			row = dict(self.source[path])
			# Remove old row
			del self.source[path]
			# Append this row
			if insert is not None:
				self.source.insert (insert, row)
			else:
				self.source.append (row)
			return
			
		for line in data.split("\n"):
			line = line.strip()
			if len (line) < 1:
				continue
				
			hint = {'location': line}
			hints_list.append (hint)
		self.add_files (hints_list, insert)
	
	def __on_dnd_send (self, widget, context, selection, target_type, timestamp):
		store, path_list = self.__selection.get_selected_rows ()
		assert path_list and len(path_list) == 1
		path, = path_list # unpack the only element
		selection.set (selection.target, 8, self.source[path]['location'])
	
	def __hig_duration (self, duration):
		hig_duration = ""
		minutes = duration / 60
		if minutes:
			hig_duration = ("%s %s") %(minutes, minutes == 1 and "minute" or "minutes")
		seconds = duration % 60
		if seconds:
			hig_secs = ("%s %s") %(seconds, seconds == 1 and "second" or "seconds")
			hig_duration += (len (hig_duration) and " and ") + hig_secs
		return hig_duration
	
	def update_disc_usage (self):
		if not self.update:
			return
		if self.source.total_duration > self.disc_size:
			self.__usage_bar.set_fraction (1)
			self.__capacity_exceeded.show ()
		else:
			self.__usage_bar.set_fraction (self.source.total_duration / float (self.disc_size))
			self.__capacity_exceeded.hide ()
		# Flush events so progressbar redrawing gets done
		while gtk.events_pending():
			gtk.main_iteration(True)
		
		if self.source.total_duration > 0:
			dur = "%s remaining"  % self.__hig_duration (self.__disc_size - self.source.total_duration)
		else:
			dur = "Empty"
		
		self.__usage_bar.set_text (dur)
			
		e = operations.Event(self)
		for l in self.listeners:
			l.on_contents_changed (e)
	
	def __selection_changed (self, treeselection):
		e = operations.Event (self)
		for l in self.listeners:
			l.on_selection_changed (e)

	def add_file (self, hints):
		w = gtkutil.get_root_parent (self)
		assert isinstance(w, gtk.Window)
		pls = self.__add_playlist (hints['location'])
		if pls is not None:
			self.add_files (pls)
			return
			
		trapper = ErrorTrapper (w)
		a = AddFile (self.source, hints)
		queue = OperationsQueue()
		queue.abort_on_failure = False
		queue.append (a)
		queue.append (trapper)
		queue.start()
	
	def __filter_location (self, location):
		for loc_filter in self.__filters:
			hints = loc_filter.filter_location (location)
			if hints is not None:
				return hints
		return None
		
	def add_files (self, hints_list, insert = None):
		assert insert is None or isinstance (insert, IntType)
		# Lock graphical updating on each request and
		# only refresh the UI later
		w = gtkutil.get_root_parent (self)
		assert isinstance(w, gtk.Window), type(w)
		
		trapper = ErrorTrapper (w)
		queue = OperationsQueue()
		queue.abort_on_failure = False
		queue.append (SetGraphicalUpdate (self, False))
		i = 0

		for h in hints_list:
			pls = self.__filter_location (h['location'])
			if pls is not None:
				self.add_files(pls, insert)
				continue
				
			ins = insert
			if insert != None:
				ins += i
			a = AddFile (self.source, h, ins)
			a.listeners.append (trapper)
			queue.append (a)
			i += 1
			
		queue.append (SetGraphicalUpdate (self, True))
		queue.append (trapper)
		queue.start()

	def remove_selected (self):
		store, path_list = self.__selection.get_selected_rows ()
		if not path_list:
			return
		indexes = []
		for p in path_list:
			assert len(p) == 1
			indexes.append(*p)
			
		self.source.delete_many (indexes)
			
	def count_selected (self):
		return self.__selection.count_selected_rows()
	
	def add_hints_filter (self, location_filter):
		self.__filters.append (location_filter)
		# Sort filters priority
		self.__filters.sort ()
	
	def remove_hints_filter (self, location_filter):
		self.__filters.remove (location_filter)
	
if __name__ == '__main__':
	import sys, os
	win = gtk.Window()
	win.connect ("delete-event", gtk.main_quit)
	w = AudioMastering ()
	w.show()
	win.add (w)
	win.show()
	

	w.add_file (sys.argv[1])
	w.source.clear()
	gtk.main()
