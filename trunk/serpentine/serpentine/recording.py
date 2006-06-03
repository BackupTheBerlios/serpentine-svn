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
import gtk
import gobject
import operations
import gtkutil
import gst

from nautilusburn import AudioTrack
from operations import OperationsQueueListener, MeasurableOperation
from converting import FetchMusicList
from gettext import gettext as _

class ConvertingError:
    def __init__ (self, win):
        self.win= win
    
    def on_finished (self, evt):
        if evt.id != operations.ERROR:
            return
        err = evt.error
        
        # Handle missing files
        if isinstance(err, gst.GError) and err.code == gst.RESOURCE_ERROR_NOT_FOUND:
            gtkutil.dialog_error(
                _("Converting files failed"),
                _("Some of the files were missing. The disc is still usable."),
                parent = self.win
            )
            return
            
        gtkutil.dialog_error (
            _("Converting files failed"),
            _("Writing to disc didn't start so it is still usable."),
            parent = self.win
        )

class WritingError:
    def __init__ (self, win):
        self.win= win

    def on_finished (self, evt):
        if evt.id == operations.SUCCESSFUL:
            return
        
        if evt.id == operations.ERROR:
            title = _("Writing to disc failed")
        else:
            title = _("Writing to disc canceled")
        
        if evt.error is None:
            msg = _("The writing operation has started. The disc may "
                    "be unusable.")
        else:
            msg = str (evt.error)
        
        gtkutil.dialog_error (title, str(msg), parent = self.win)

################################################################################

class ConvertAndWrite (MeasurableOperation, OperationsQueueListener):
    """
    ConvertAndWrite class is yet another operation. When this operation is
    started it will show the user the dialog for the recording operation.
    It is supposed to be a one time operation.
    """
    def __init__ (self, music_list, preferences, parent = None):
        MeasurableOperation.__init__ (self)
        self.__queue = operations.OperationsQueue ()
        self.__queue.listeners.append (self)
        self.__parent = parent
        self.__prog = gtkutil.HigProgress ()
        self.__prog.primary_text = _("Writing Audio Disc")
        self.__prog.secondary_text = _("The audio tracks are going to be "
                                       "written to a disc. This operation may "
                                       "take a long time, depending on data "
                                       "size and write speed.")
                                     
        self.__prog.connect ("destroy-event", self.__on_prog_destroyed)
        self.__prog.cancel_button.connect ("clicked", self.__on_cancel)
        self.__prog.close_button.connect ("clicked", self.__on_close)
        self.__prog.set_icon_name ("gnome-dev-cdrom-audio")
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
            gtkutil.dialog_warn (_("CD-RW disc will be erased"),
                                 _("Please remove your disc if you want to "
                                   "preserve it's contents."),
                                 parent = self.__prog)
        self.__blocked = False
        self.preferences.pool.temporary_dir = self.preferences.temporary_dir
        oper = FetchMusicList(self.__music_list, self.preferences.pool)
        # Fill filenames after retrieving stuff
        self.__filenames = []
        oper.listeners.append (MusicListToFilenames (self.__music_list, self.__filenames))
        
        oper.listeners.append (ConvertingError(self.__prog))
        
        self.__fetching = oper
        self.__queue.append (oper)
        
        # Convert a music list into a list of filenames
        oper = WriteAudioDisc (self.__filenames, self.preferences, self.__prog)
                                
        oper.recorder.connect ("progress-changed", self.__tick)
        oper.recorder.connect ("action-changed", self.__on_action_changed)
        oper.listeners.append (WritingError(self.__prog))
        
        self.__queue.append (oper)
        self.__recording = oper
        self.__queue.start ()
        self.__source = gobject.timeout_add (300, self.__tick)
    
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
            self.__prog.sub_progress_text = _("Preparing recorder")
        elif action == nautilusburn.RECORDER_ACTION_WRITING:
            self.__prog.sub_progress_text = _("Writing media files to disc")
        elif action == nautilusburn.RECORDER_ACTION_FIXATING:
            self.__prog.sub_progress_text = _("Fixating disc")
    
    def before_operation_starts (self, evt, oper):
        # There can be only to operations starting
        # The first is to convert to WAV the second is to record files
        
        # We are converting
        if oper == self.__fetching:
            self.__prog.sub_progress_text = _("Preparing media files")
        
        # We are recording
        else:
            # When we are recording the main source remains blocked
            # Therefore there are no idle events
            self.__blocked = True
    
    def on_finished (self, evt):
        # self.__prog.cancel_button.hide ()
        # self.__prog.close_button.show ()
        gobject.source_remove (self.__source)
        
        if evt.id == operations.SUCCESSFUL:
            gtkutil.dialog_info (
                _("Writing to disc finished"),
                _("Disc writing was successful."),
                parent = self.__prog
            )
        
        # Warn our listenrs
        self._propagate (evt)

        self.__on_close ()

class MusicListToFilenames:
    def __init__ (self, music_list, filenames):
        self.music_list = music_list
        self.filenames = filenames
        
    def on_finished (self, evt):
        for row in self.music_list:
            self.filenames.append (row["cache_location"])
        

################################################################################
class WriteAudioDisc (MeasurableOperation):
    
    def __init__ (self, music_list, preferences, parent = None):
        MeasurableOperation.__init__(self)
        self.music_list = music_list
        self.__progress = 0.0
        self.__running = False
        self.parent = parent
        self.__recorder = nautilusburn.Recorder()
        self.__preferences = preferences
    
    title = _("Writing Files to Disc")

    progress = property (lambda self: self.__progress)
    running = property (lambda self: self.__running)
    recorder = property (lambda self: self.__recorder)
    preferences = property (lambda self: self.__preferences)
    
    def start (self):
        # TODO: Compare media size with music list duration
        # If it's bigger then current eject media and ask for another one
        self.__running = True
        tracks = []

        for filename in self.music_list:
            tracks.append (AudioTrack (filename))
        
        if len (tracks) == 0:
            self._send_finished_event (
                operations.ERROR,
                _("There were no valid files for writing. "
                  "Please select at least one.")
            )
            return
        
        self.recorder.connect ("progress-changed", self.__on_progress)
        self.recorder.connect ("insert-media-request", self.__insert_cd)
        self.recorder.connect ("warn-data-loss", self.__on_data_loss)
        gobject.idle_add (self.__thread, tracks)
    
    def __on_data_loss (self, recorder):
        # the return value of this signal is if we want to stop recording
        # in this case we don't because we've already warned the user
        # if there is going to be a data loss but it could be moved here
        return False
    
    def stop (self):
        # To cancel you have to send False, sending True just checks
        self.recorder.cancel (False)
        
    def __on_progress (self, source, progress, seconds = None):
        self.__progress = progress
    
    def __thread (self, tracks):
        error = None
        try:
            result = self.recorder.write_tracks (self.preferences.drive,
                                                 tracks,
                                                 self.preferences.speedWrite,
                                                 self.preferences.writeFlags)
        except gobject.GError, err:
            result = nautilusburn.RECORDER_RESULT_ERROR
            # Grab the error message
            error = str(err)
            
        if result == nautilusburn.RECORDER_RESULT_FINISHED:
            result = operations.SUCCESSFUL
        elif result == nautilusburn.RECORDER_RESULT_ERROR:
            result = operations.ERROR
        elif result == nautilusburn.RECORDER_RESULT_CANCEL:
            result == operations.ABORTED
        elif result == nautilusburn.RECORDER_RESULT_RETRY:
            #TODO: hanlde this
            result == operations.ERROR
        
        self._send_finished_event (result, error)
    
    def __insert_cd (self, rec, reload_media, can_rewrite, busy_cd):
        # messages from nautilus-burner-cd.c
        if busy_cd:
            msg = _("Please make sure another application is not using the drive.")
            title = _("Drive is busy")
        elif not reload_media and can_rewrite:
            msg = _("Please put a rewritable or blank disc into the drive.")
            title = _("Insert rewritable or blank disc")
        elif not reload_media and not can_rewrite:
            msg = _("Please put a blank disc into the drive.")
            title = _("Insert blank disc")
        elif can_rewrite:
            msg = _("Please replace the disc in the drive with a "
                    "rewritable or blank disc.")
                    
            title = _("Reload rewritable or blank disc")
        else:
            msg = _("Please replace the disc in the drive a blank disc.")
            title = _("Reload blank disc")
        return gtkutil.dialog_ok_cancel (title, msg, parent = self.parent) == gtk.RESPONSE_OK


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
