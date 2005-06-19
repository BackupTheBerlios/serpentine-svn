# Copyright (C) 2005 Tiago Cogumbreiro <cogumbreiro@users.sf.net>
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

import gtkutil, gtk, operations, os, os.path

import constants

from components import SimpleComponent
from operations import MapProxy, OperationListener, OperationsQueue
from operations import CallableOperation
from mastering import AudioMastering, GtkMusicList, MusicListGateway
from mastering import ErrorTrapper
from recording import RecordMusicList, RecordingMedia

from serpentine.common import *

class GladeComponent (SimpleComponent):

    def _setup_glade (self, g):
        """This method is called when the SerpentineWindow object is created."""

class FileDialogComponent (GladeComponent):
    def __init__ (self, parent):
        super (FileDialogComponent, self).__init__ (parent)
        
        # Open playlist file dialog
        self.file_dlg = gtk.FileChooserDialog (buttons = (gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        self.file_dlg.set_title ("")
        self.file_dlg.set_transient_for (self.parent)
        self.__file_filters = None
    
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
    def _setup_glade (self, g):
        g.get_widget ("add").connect ("clicked", self.run_dialog)
        g.get_widget ("add_mni").connect ("activate", self.run_dialog)
        
        self.file_dlg.set_select_multiple (True)
        
    def _on_response_ok (self):
        files = self.file_dlg.get_uris()
        self.parent.music_list_widget.music_list_gateway.add_files (files).start ()

    _get_file_filters = lambda self: self.parent.application.music_file_filters

    
class PlaylistComponent (FileDialogComponent):
    def _setup_glade (self, g):
        g.get_widget ("open_playlist_mni").connect ("activate", self.run_dialog)
    
    
    _get_file_filters = lambda self: self.parent.application.playlist_file_filters

    def _on_response_ok (self):
        playlist = self.file_dlg.get_uri()
        self.parent.music_list_widget.music_list_gateway.add_files ([playlist]).start ()
        self.parent.clear_files ()
import tempfile

class SavePlaylistComponent (SimpleComponent):
    def _setup_glade (self, g):
        g.get_widget ("save_playlist_mni").connect ("activate", self.run_dialog)
        self.file_dlg = gtk.FileChooserDialog (
            action = gtk.FILE_CHOOSER_ACTION_SAVE,
            buttons = (
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_SAVE, gtk.RESPONSE_OK
            )
        )
        self.file_dlg.set_title ("")
        self.file_dlg.set_transient_for (self.parent)
        app = self.parent.application
        app.save_playlist.listeners.append (self)
        self.__sync = True
    
    def on_registred (self, factory, extension, description):
        self.__sync = True
    
    def on_finished (self, evt):
        win = self.parent
            
        if evt.id == operations.SUCCESSFUL:
            gtkutil.dialog_warn (
                "Playlist Saved",
                "Playlist was saved successfully.",
                win
            )
        else:
            gtkutil.dialog_error (
                "Playlist Not Saved",
                "There was an error while saving the playlist.",
                win
            )
        
    def __sync_file_filters (self):
        if not self.__sync:
            return
        
        app = self.parent.application
        
        # Remove old filters
        for f in self.file_dlg.list_filters ():
            self.file_dlg.remove_filter (f)
        
        # Now fill the real filters
        for f in app.save_playlist.file_filters:
            self.file_dlg.add_filter (f)
        
        # Sync is complete
        self.__sync = False
    
    def run_dialog (self, *args):
        app = self.parent.application
        win = self.parent
        
        self.__sync_file_filters ()
        
        if self.file_dlg.run () == gtk.RESPONSE_OK:
            filename = self.file_dlg.get_filename ()
            basename = os.path.basename (filename)
            if os.path.exists (filename) and gtkutil.dialog_ok_cancel (
                "Replace existing file",
                "A file named <i>%s</i> already exists. "\
                "Do you want to replace it with the one "\
                "you are saving?" % basename,
                win
            ) != gtk.RESPONSE_OK:
                
                self.file_dlg.unselect_all()
                self.file_dlg.hide()
                return
                
            try:
                oper = app.save_playlist.save (filename)
            except SerpentineNotSupportedError:
                gtkutil.dialog_error (
                    "Unsupported Format",
                    "The playlist format you used (by the file extension) is " \
                    "currently not supported.",
                    win
                )
            oper.listeners.append (self)
            oper.start ()
        
        self.file_dlg.unselect_all()
        self.file_dlg.hide()

class SerpentineWindow (gtk.Window, OperationListener, operations.Operation, SimpleComponent):
    # TODO: finish up implementing an Operation
    components = (AddFileComponent, PlaylistComponent, SavePlaylistComponent)
    
    def __init__ (self, application):
        gtk.Window.__init__ (self, gtk.WINDOW_TOPLEVEL)
        operations.Operation.__init__ (self)
        SimpleComponent.__init__ (self, application)
            
        self.__application = application
        self.__masterer = AudioMastering ()
        # Variable related to this being an Operation
        self.__running = False
        self.connect ("show", self.__on_show)
        # We listen for GtkMusicList events
        self.music_list_widget.listeners.append (self)

        glade_file = os.path.join (constants.data_dir, "serpentine.glade")
        g = gtk.glade.XML (glade_file, "main_window_container")
        
        # Send glade to setup subcomponents
        for c in self._components:
            if hasattr (c, "_setup_glade"):
                c._setup_glade (g)

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
