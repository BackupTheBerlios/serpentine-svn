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

import nautilusburn
from nautilusburn import AudioTrack
import gtk, gobject
import operations, gtkutil
from operations import OperationsQueueListener, MeasurableOperation
from converting import FetchMusicList

################################################################################
class RecordingMedia (MeasurableOperation, OperationsQueueListener):
	"""
	RecordingMedia class is yet another operation. When this operation is
	started it will show the user the dialog for the recording operation.
	It is supposed to be a one time operation.
	"""
	def __init__ (self, music_list, preferences, parent = None):
		MeasurableOperation.__init__ (self)
		self.__queue = operations.OperationsQueue ()
		self.__queue.listeners.append (self)
		self.__parent = parent
		self.__prog = gtkutil.HigProgress ()
		self.__prog.primary_text = "Recording Audio Disc"
		self.__prog.secondary_text = "The audio tracks are going to be written to a disc. This operation may take a long time, depending on data size and write speed."
		self.__prog.connect ('destroy-event', self.__on_prog_destroyed)
		self.__prog.cancel_button.connect ("clicked", self.__on_cancel)
		self.__prog.close_button.connect ("clicked", self.__on_close)
		self.__music_list = music_list
		self.__preferences = preferences
		self.__drive = preferences.drive
		self.__can_start = True
	
	preferences = property (lambda self: self.__preferences)
	
	# MeasurableOperation's properties
	can_stop = property (lambda self: self.__queue.can_stop)
	can_start = property (lambda self: self.__can_start)
	running = property (lambda self: self.__queue.running)
	progress = property (lambda self: self.__queue.progress)
	drive = property (lambda self: self.__drive)
	
	def __on_prog_destroyed (self, *args):
		if self.cancel_button.is_sensitive ():
			self.__prog.hide ()
			self.__on_cancel ()
		return False
		
	def start (self):
		self.__can_start = False
		self.__prog.show ()
		if self.preferences.drive.get_media_type () == nautilusburn.MEDIA_TYPE_CDRW:
			gtkutil.dialog_warn ("CD-RW disc will be erased",
			                     "Please remove your disc if you want to "\
			                     "preserve it's contents.",
			                     self.__prog)
		self.__blocked = False
		self.preferences.pool.temporary_dir = self.preferences.temporary_dir
		oper = FetchMusicList(self.__music_list, self.preferences.pool)
		self.__fetching = oper
		self.__queue.append (oper)
		
		oper = RecordMusicList (self.__music_list,
		                        self.preferences,
		                        self.__prog)
		                        
		oper.recorder.connect ('progress-changed', self.__tick)
		oper.recorder.connect ('action-changed', self.__on_action_changed)
		self.__queue.append (oper)
		self.__recording = oper

		self.__queue.start ()
		self.__source = gobject.timeout_add (200, self.__tick)
	
	def stop (self):
		self.__on_cancel ()
	
	def __tick (self, *args):
		if self.__queue.running:
			self.__prog.progress_fraction = self.__queue.progress
			
		return True
	
	def __on_cancel (self, *args):
		if self.can_stop:
			# Makes it impossible for our user to stop
			self.__prog.cancel_button.set_sensitive (False)
			self.__queue.stop ()
		
	def __on_close (self, *args):
		self.__prog.destroy ()
	
	def __on_action_changed (self, recorder, action, media):
		if action == nautilusburn.RECORDER_ACTION_PREPARING_WRITE:
			self.__prog.sub_progress_text = "Preparing recorder"
		elif action == nautilusburn.RECORDER_ACTION_WRITING:
			self.__prog.sub_progress_text = "Writing media files to disc"
		elif action == nautilusburn.RECORDER_ACTION_FIXATING:
			self.__prog.sub_progress_text = "Fixating disc"
	
	def before_operation_starts (self, evt, oper):
		# There can be only to operations starting
		# The first is to convert to WAV the second is to record files
		
		# We are converting
		if oper == self.__fetching:
			self.__prog.sub_progress_text = "Preparing media files"
		
		# We are recording
		else:
			# When we are recording the main source remains blocked
			# Therefore there are no idle events
			self.__blocked = True
	
	def on_finished (self, evt):
		self.__prog.cancel_button.hide ()
		self.__prog.close_button.show ()
		gobject.source_remove (self.__source)
		# Warn our listenrs
		e = operations.FinishedEvent (self, evt.id)
		for l in self.listeners:
			l.on_finished (e)

################################################################################

class RecordMusicList (MeasurableOperation):
	def __init__ (self, music_list, preferences, parent = None):
		MeasurableOperation.__init__(self)
		self.music_list = music_list
		self.__progress = 0.0
		self.__running = False
		self.parent = parent
		self.__recorder = nautilusburn.Recorder()
		self.__preferences = preferences
	
	progress = property (lambda self: self.__progress)
	running = property (lambda self: self.__running)
	recorder = property (lambda self: self.__recorder)
	preferences = property (lambda self: self.__preferences)
	
	def start (self):
		# TODO: Compare media size with music list duration
		# If it's bigger then current eject media and ask for another one
		self.__running = True
		tracks = []
		for m in self.music_list:
			tracks.append (AudioTrack (filename = m["cache_location"]))
		self.recorder.connect ('progress-changed', self.__on_progress)
		self.recorder.connect ('insert-media-request', self.__insert_cd)
		self.recorder.connect ('warn-data-loss', self.__on_data_loss)
		gobject.idle_add (self.__thread, tracks)
	
	def __on_data_loss (self, *args):
		print "data loss", args
		return True
	
	def stop (self):
		# To cancel you have to send False, sending True just checks
		self.recorder.cancel (False)
		
	def __on_progress (self, source, progress):
		self.__progress = progress
	
	def __thread (self, tracks):
		result = self.recorder.write_tracks (self.preferences.drive,
		                                     tracks,
		                                     self.preferences.speed_write,
		                                     self.preferences.write_flags)

		if result == nautilusburn.RECORDER_RESULT_FINISHED:
			result = operations.SUCCESSFUL
		elif result == nautilusburn.RECORDER_RESULT_ERROR:
			result = operations.ERROR
		elif result == nautilusburn.RECORDER_RESULT_CANCEL:
			result == operations.ABORTED
		elif result == nautilusburn.RECORDER_RESULT_RETRY:
			#TODO: hanlde this
			result == operations.ERROR
			
		e = operations.FinishedEvent(self, result)
		
		self.__running = False
		for l in self.listeners:
			l.on_finished (e)
	
	def __insert_cd (self, rec, reload_media, can_rewrite, busy_cd):
		# messages from nautilus-burner-cd.c
		if busy_cd:
			msg = "Please make sure another application is not using the drive."
			title = "Drive is busy"
		elif not reload_media and can_rewrite:
			msg = "Please put a rewritable or blank disc into the drive."
			title = "Insert rewritable or blank disc"
		elif not reload_media and not can_rewrite:
			msg = "Please put a blank disc into the drive."
			title = "Insert blank disc"
		elif can_rewrite:
			msg = "Please replace the disc in the drive with a rewritable or blank disc."
			title = "Reload rewritable or blank disc"
		else:
			msg = "Please replace the disc in the drive a blank disc."
			title = "Reload blank disc"
		return gtkutil.dialog_ok_cancel (title, msg, self.parent) == gtk.RESPONSE_OK


if __name__ == '__main__':
	import sys, gobject
	class MyListener:
		def on_finished (self, evt):
			gtk.main_quit()
	
	def print_progress (oper):
		return True
	w = gtk.Window(gtk.WINDOW_TOPLEVEL)
	w.add (gtk.Label("---"))
	w.show_all()
	d = nautilusburn.get_drives_list (False)[0]
	music_lst = [{'filename': sys.argv[1]}]
	r = RecordMusicList (music_lst, d, d.get_max_speed_write(), 0) #nautilusburn.RECORDER_WRITE_DUMMY_WRITE
	r.listeners.append (MyListener())
	gobject.timeout_add (250, print_progress, r)
	r.start()
	gtk.main()
