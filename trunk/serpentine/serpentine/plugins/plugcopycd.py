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

import gtk, weakref, DiscID, gst, os

raise Exception

from serpentine import gtkutil, audio, operations
from serpentine.recording import WriteAudioDisc

def silent_unlink (f):
    try:
        os.unlink (f)
    except:
        pass

class CopyCD (object):
    def __init__ (self, app):
        self.__app = weakref.ref (app)
    
    app = property (lambda self: self.__app)
    
    def count_tracks (self):
        dev = DiscId.open (self.device)
        disc_id = DiscId.disc_id (dev)
        return disc_id[1]
    
    count_tracks = property (count_tracks)
    device = property (lambda self: self.app.preferences.drive.get_device ())
    temporary_dir = property (lambda self: self.app.preferences.temporary_dir)
    
    def extract_audio_cd (self):
        """Extract all the tracks and return the operation and the filenames."""
        
        extract_queue = operations.OperationQueue ()
        filenames = []
        
        for track_num in range (self.count_tracks):
            handle, filename = tempfile.mkstemp(suffix = ".wav", dir = self.temporary_dir)
            os.close (handle)
            extract_queue.append (audio.extract_audio_track_file (self.device, track_num, filename))
            filenames.append (filename)
        
        return extract_queue, filenames
    
    def copy_cd (self):
        # TODO: add error reporting
        # extract the cd contents
        extract_cd, filenames = self.extract_audio_cd ()
        
        # Write them to a CD
        write_cd = WriteAudioDisc (music_list, self.app.preferences)
        
        extract_and_write = operations.OperationsQueue ((extract_cd, write_cd))
        
        # Remove the temporary files
        remove_files = operations.OperationQueue ()
        
        for filename in filenames:
            
            oper = operations.CallableOperation (
                lambda: silent_unlink (filename)
            )
            remove_files.append (oper)
        
        oper = operations.OperationsQueue ((extract_and_write, remove_files))
        oper.abort_on_failure = False
        return oper
        
    def on_activate (*args):
        self.copy_cd.start ()
        

def create_plugin (app):

    if not hasattr (app, "window_widget"):
        return
    
    file_menu = gtkutil.find_widget (app.window_widget, "file_menu")
    assert file_menu is not None
    
    copy_cd = CopyCD (app)
    
    mni = gtk.MenuItem ("Copy Audio-CD...")
    mni.connect ("activate", copy_cd.on_activate)
    mni.show ()
    
    file_menu.prepend (mni)
    
    return copy_cd