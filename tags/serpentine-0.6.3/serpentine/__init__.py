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

import os
import os.path
import gtk
import gtk.glade
import gobject
import sys
import statvfs
import gnome.ui
import nautilusburn

from xml.parsers.expat import ExpatError

# Private modules
import operations
import gtkutil
import constants
import urlutil

from mastering import AudioMastering, GtkMusicList, MusicListGateway
from mastering import ErrorTrapper
from recording import ConvertAndWrite
from preferences import RecordingPreferences
from operations import MapProxy, OperationListener, OperationsQueue
from operations import CallableOperation
from components import Component
from mainwindow import SerpentineWindow
from common import *
from plugins import plugins

class SavePlaylistRegistry (Component):
    def __init__ (self, parent):
        super (SavePlaylistRegistry, self).__init__ (parent)
        
        # all files filter
        all_files = gtk.FileFilter ()
        all_files.set_name (_("All files"))
        all_files.add_pattern ("*.*")
        
        self.__global_filter = gtk.FileFilter()
        self.__global_filter.set_name ("Playlists")
        self.__file_filters = [self.__global_filter, all_files]
        self.__factories = {}
        self.listeners = []
        
    file_filters = property (lambda self: self.__file_filters)
    
    def register (self, factory, extension, description):
        self.__global_filter.add_pattern ("*" + extension)
        
        filter = gtk.FileFilter ()
        filter.set_name (description)
        filter.add_pattern ("*" + extension)
        
        self.file_filters.append (filter)
        
        for listener in self.listeners:
            listener.on_registred (factory, extension, description)
        
        self.__factories[extension] = factory
    
    def save (self, filename):
        file, ext = os.path.splitext (filename)

        if not self.__factories.has_key (ext):
            raise SerpentineNotSupportedError
        
        return  self.__factories[ext] (self.parent.music_list, filename)
    
class Application (operations.Operation, Component):
    components = ()
    def __init__ (self):
        operations.Operation.__init__ (self)
        Component.__init__ (self, None)
        self.savePlaylist = SavePlaylistRegistry (self)
        
        self.__preferences = RecordingPreferences ()
        self.__operations = []
        
        self._music_file_patterns = {}
        self._playlist_file_patterns = {}
        self._music_file_filters = None
        self._playlist_file_filters = None
        self.register_music_file_pattern (_("All files"), "*.*")
        self.register_music_file_pattern ("MPEG Audio Stream, Layer III", "*.mp3")
        self.register_music_file_pattern ("Ogg Vorbis Codec Compressed WAV File", "*.ogg")
        self.register_music_file_pattern ("Free Lossless Audio Codec", "*.flac")
        self.register_music_file_pattern ("PCM Wave audio", "*.wav")
        self.register_playlist_file_pattern (_("All files"), "*.*")
    
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
        self.preferences.savePlaylist (self.music_list)
        self.preferences.pool.clear()
        # Warn listeners
        evt = operations.FinishedEvent (self, operations.SUCCESSFUL)
        for listener in self.listeners:
            listener.on_finished (evt)
            
        # Cleanup plugins
        del self.__plugins


    def write_files (self, window = None):
        # TODO: we should add a confirmation dialog

        r = ConvertAndWrite (self.music_list, self.preferences, window)
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
            _("Supported files")
        )
    )

    playlist_file_filters = property (
        lambda self: self.__get_file_filter (
            "_playlist_file_filters",
            "_playlist_file_patterns",
            _("Playlists")
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
    files = map (urlutil.normalize, files)
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
        

    


gobject.type_register (SerpentineWindow)

if __name__ == '__main__':
    s = Serpentine ()
    s.preferences.simulate = len(sys.argv) == 2 and sys.argv[1] == '--simulate'
    s.show()
    gtk.main()
