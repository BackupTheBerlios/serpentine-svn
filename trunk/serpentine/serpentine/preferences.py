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

import gtk.glade, nautilusburn, gtk, gobject, os, os.path, gconf, gtk.gdk, urllib
from xml.dom import minidom
from urlparse import urlparse

import gaw, xspf, constants, gtkutil
from converting import GvfsMusicPool
from common import SafeFileWrite
# For testing purposes we try to import it
try:
    import release
except Exception:
    release = None
    
gconf.client_get_default ().add_dir ("/apps/serpentine", gconf.CLIENT_PRELOAD_NONE)

def recording_preferences_window (preferences):
    prefs_widget = gtkutil.find_widget (preferences.dialog, "preferences")
    prefs_widget.show ()
    
    assert prefs_widget is not None
    parent = prefs_widget.get_parent ()
    parent.remove (prefs_widget)
    
    win = gtk.Window (gtk.WINDOW_TOPLEVEL)
    win.set_border_width (12)
    win.set_title ("Serpentine Preferences")
    
    vbox = gtk.VBox ()
    vbox.set_spacing (18)
    vbox.show ()
    win.add (vbox)
    
    vbox.pack_start (prefs_widget)
    
    # Add a close button
    bbox = gtk.HButtonBox ()
    bbox.set_layout (gtk.BUTTONBOX_END)
    bbox.show ()
    vbox.add (bbox)
    
    close_btn = gtk.Button (stock = "gtk-close")
    close_btn.show ()
    close_btn.connect ("clicked", gtk.main_quit)
    bbox.add (close_btn)
    
    return win
    
class RecordingPreferences (object):
    def __init__ (self):
        # By default use burnproof
        self.__write_flags  = nautilusburn.RECORDER_WRITE_BURNPROOF
#        self.__write_flags |= nautilusburn.RECORDER_WRITE_DISC_AT_ONCE
#        self.__write_flags |= nautilusburn.RECORDER_WRITE_DEBUG

        # Sets up data dir and version
        if release:
            self.version = release.version
        else:
            self.version = "testing"
        
        # setup ui
        g = gtk.glade.XML (os.path.join(constants.data_dir, 'serpentine.glade'),
                           "preferences_dialog")
        self.__dialog = g.get_widget ("preferences_dialog")
        self.dialog.connect ("destroy-event", self.__on_destroy)
        
        # Drive selection
        drv = g.get_widget ("drive")
        cmb_drv = nautilusburn.DriveSelection ()
        cmb_drv.set_property ("show-recorders-only", True)
        cmb_drv.show ()
        cmb_drv.connect ("device-changed", self.__on_drive_changed)
        
        self.__drive_selection = cmb_drv
        drv.pack_start (cmb_drv, False, False)
        self.__drive_listeners = []
        
        # Speed selection
        self.__speed = gaw.data_spin_button (g.get_widget ("speed"),
                                             "/apps/serpentine/write_speed")
        
        self.__specify_speed = g.get_widget ("specify_speed_wrapper")
                                             
        specify_speed = g.get_widget ("specify_speed")
        
        self.__speed_select = gaw.RadioButtonData (
            widgets = dict (
                specify_speed = specify_speed,
                use_max_speed = g.get_widget ("use_max_speed")
            ),
            
            key = "/apps/serpentine/speed_select"
        )
        self.__speed_select.seleted_by_default = "use_max_speed"
        
        specify_speed.connect ("toggled", self.__on_specify_speed)
        # init specify speed box sensitivity
        self.__on_specify_speed (specify_speed)
        
        # No default value set, set it to 99
        if self.__speed.data == 0:
            self.__speed.data = 99

        self.__update_speed ()
        self.__speed.sync_widget()
        self.__speed.widget.set_sensitive (specify_speed.get_active ())
    
        # eject checkbox
        self.__eject = gaw.data_toggle_button (g.get_widget ("eject"),
                                               "/apps/serpentine/eject")
        
        g.get_widget ("refresh_speed").connect ("clicked", self.__on_refresh_speed)
        
        # temp
        self.__tmp = gaw.GConfValue (
            key = "/apps/serpentine/temporary_dir",
            data_spec = gaw.Spec.STRING
        )
        
        # Pool
        self.__pool = GvfsMusicPool ()
        
        # Close button
        self.__close = g.get_widget ("close_btn")
    
    __config_dir = os.path.join (os.path.expanduser ("~"), ".serpentine")
    config_dir = property (lambda self: self.__config_dir)
    
    def __on_refresh_speed (self, *args):
        self.__update_speed ()

    def __update_speed (self):
        if not self.drive:
            self.__speed.widget.set_sensitive (False)
            return
            
        speed = self.drive.get_max_speed_write ()
        assert speed >= 0, speed

        val = self.__speed.data

        self.__speed.widget.set_range (1, speed)
        self.__speed.data = val
        
    def __set_simulate (self, simulate):
        assert isinstance (simulate, bool)
        if simulate:
            self.__write_flags |= nautilusburn.RECORDER_WRITE_DUMMY_WRITE
        else:
            self.__write_flags &= ~nautilusburn.RECORDER_WRITE_DUMMY_WRITE
    
    def __get_simulate (self):
        return (self.__write_flags & nautilusburn.RECORDER_WRITE_DUMMY_WRITE) == nautilusburn.RECORDER_WRITE_DUMMY_WRITE
    
    simulate = property (__get_simulate, __set_simulate)

    def __set_overburn (self, overburn):
        assert isinstance (overburn, bool)
        if overburn:
            self.__write_flags |= nautilusburn.RECORDER_WRITE_OVERBURN
        else:
            self.__write_flags &= ~nautilusburn.RECORDER_WRITE_OVERBURN
    
    def __get_overburn (self):
        return (self.__write_flags & nautilusburn.RECORDER_WRITE_OVERBURN) == nautilusburn.RECORDER_WRITE_OVERBURN
    
    overburn = property (__get_overburn, __set_overburn)

    dialog = property (lambda self: self.__dialog)
    
    def __set_version (self, version):
        assert isinstance (version, str)
        self.__version = version
        
    version = property (lambda self: self.__version, __set_version)
    
    drive = property (lambda self: self.__drive_selection.get_drive())
    
    drive_listeners = property (lambda self: self.__drive_listeners, 
    doc = """"Drive listeners should register a callback function which is 
    called when the drive is changed. This can be done in the following form:
    
    prefs = Preferences ()
    
    def on_changed (event, drive):
        global prefs
        print "Object holder:", event.source, \
            "changed to the following drive:", drive
        assert event.source = prefs
    prefs.drive_listeners.append (on_changed)
    """)
    
    def temporary_dir (self):
        tmp = self.__tmp.data
        # tmp can be a url or a filename
        s = urlparse (tmp)
        scheme = s[0]
        # in case it is a url
        if scheme == "file":
            tmp = urllib.unquote (s[2])
        # in case it is a url but not file://
        elif scheme != "":
            return None
        return tmp
        
    temporary_dir = property (temporary_dir)
    pool = property (lambda self: self.__pool)
    
    def __get_speed_write (self):
        assert self.drive
        self.__update_speed()
        #if self.__use_max_speed.data:
        if self.__speed_select.data == "use_max_speed":
            return self.drive.get_max_speed_write ()
        return self.__speed.data
        
    speed_write = property (__get_speed_write)
    
    def __get_write_flags (self):
        ret = self.__write_flags
        if self.__eject.data:
            ret |= nautilusburn.RECORDER_WRITE_EJECT
        return ret
        
    write_flags = property (__get_write_flags)
    
    # Read only variable
    def temporary_dir_is_ok (self):
        tmp = self.temporary_dir
        # Try to open the local file
        try:
            is_ok = os.path.isdir (tmp) and os.access (tmp, os.W_OK)
        except OSError, err:
            print err
            is_ok = False
        return is_ok
    temporary_dir_is_ok = property (temporary_dir_is_ok,
                                    doc="Tests if temporary directory exists " \
                                    "and has write permissions.")
    
    def __on_tmp_choose (self, *args):
        if self.__tmp_dlg.run () == gtk.RESPONSE_OK:
            self.__tmp.data = self.__tmp_dlg.get_filename ()
        self.__tmp_dlg.hide ()

    def __on_destroy (self, *args):
        self.dialog.hide ()
        return False

    def __on_tmp_changed (self, *args):
        is_ok = self.temporary_dir_is_ok ()
        if is_ok:
            self.__tmp.widget.modify_base (gtk.STATE_NORMAL, gtk.gdk.color_parse ("#FFF"))
        else:
            self.__tmp.widget.modify_base (gtk.STATE_NORMAL, gtk.gdk.color_parse ("#F88"))
        self.__close.set_sensitive (is_ok)
        
    def __on_specify_speed (self, widget, *args):
        self.__specify_speed.set_sensitive (widget.get_active ())
    
    def save_playlist (self, source):
        if not os.path.exists (self.config_dir):
            os.makedirs (self.config_dir)
        p = xspf.Playlist (title="Serpentine's playlist", creator="Serpentine " + self.version)
        source.to_playlist (p)
        doc = p.toxml()
        
        out = SafeFileWrite (os.path.join (self.config_dir, "playlist.xml"))
        try:
            doc.writexml (out, addindent = "\t", newl = "\n")
            del p
            out.close()
        except:
            out.abort ()
            return False
            
        return True
    
    def load_playlist (self, source):
        if not os.path.exists (self.config_dir):
            os.makedirs (self.config_dir)
        p = xspf.Playlist (title="Serpentine's playlist", creator="Serpentine " + self.version)
        
        try:
            p.parse (os.path.join (self.config_dir, "playlist.xml"))
        except IOError:
            return
            
        source.from_playlist (p)
    
    def __on_drive_changed (self, device):
        event = operations.Event (self)
        for listener in self.drive_listeners:
            listener (event, self.drive)
