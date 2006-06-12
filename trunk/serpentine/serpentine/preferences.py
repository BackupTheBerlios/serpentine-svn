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
import os
import gconf
import gtk

from gtk import glade
from os import path
from types import StringType
from gettext import gettext as _

# Local imports
import gaw
import xspf
import gtkutil
import release
import urlutil
import tempfile

from converting import GvfsMusicPool
from common import SafeFileWrite

GCONF_DIR = "/apps/serpentine"
RAT_GCONF_DIR = "/apps/rat"
NCB_GCONF_DIR = "/apps/nautilus-cd-burner"

# Get system's temporary dir
TEMP_DIR = tempfile.gettempdir()
HOME_DIR = path.expanduser("~")

def _is_dir_writable(dirname):
    # Try to open the local file
    try:
        is_ok = path.isdir(dirname) and os.access(dirname, os.W_OK)
    except OSError, err:
        is_ok = False
            
    return is_ok


for gconf_dir in (GCONF_DIR, RAT_GCONF_DIR, NCB_GCONF_DIR):
    gconf.client_get_default ().add_dir (gconf_dir, gconf.CLIENT_PRELOAD_NONE)

def recordingPreferencesWindow (preferences):
    prefs_widget = gtkutil.find_child_widget (preferences.dialog, "preferences")
    prefs_widget.show ()
    
    assert prefs_widget is not None
    parent = prefs_widget.get_parent ()
    parent.remove (prefs_widget)
    
    win = gtk.Window (gtk.WINDOW_TOPLEVEL)
    win.set_border_width (12)
    win.set_title (_("Serpentine Preferences"))
    
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

class HideCloseButton:
    """
    Monitors the 'rat' key for showing/hiding the close button.
    """
    def __init__(self, close_button):
        self.button = close_button
        self.use_button = gaw.GConfValue (
            key = RAT_GCONF_DIR + "/use_close_button",
            data_spec = gaw.Spec.BOOL,
            default = True
        )
        self.use_button.set_callback(self.on_update)
        self.on_update()
    
    def on_update(self, *args):
        if not self.use_button.data:
            self.button.hide()
        else:
            self.button.show()

class WriteSpeed:
    """
    Handles and monitors writing speed related widgets state.
    """
    def __init__(self, g, get_drive):
        self.get_drive = get_drive
        
        self.__speed = gaw.data_spin_button (g.get_widget("speed"),
                                             GCONF_DIR + "/write_speed")
        
        self.__specify_speed = g.get_widget ("specify_speed_wrapper")
                                             
        specify_speed = g.get_widget ("specify_speed")
        
        self.__speed_select = gaw.RadioButtonData (
            widgets = dict (
                specify_speed = specify_speed,
                use_max_speed = g.get_widget ("use_max_speed")
            ),
            
            key = GCONF_DIR + "/speed_select"
        )
        self.__speed_select.seleted_by_default = "use_max_speed"
        
        specify_speed.connect ("toggled", self.__on_specify_speed)
        g.get_widget ("refresh_speed").connect ("clicked", self.__on_refresh_speed)
        
        # No default value set, set it to 99
        if self.__speed.data == 0:
            self.__speed.data = 99

        self.__update_speed ()
        self.__speed.sync_widget()
        
        # init specify speed box sensitivity
        self.__on_specify_speed (specify_speed)
        
    def get(self):
        assert self.get_drive() is not None
        self.__update_speed()

        if self.__speed_select.data == "use_max_speed":
            return self.get_drive().get_max_speed_write ()
        return self.__speed.data

    def __on_refresh_speed (self, *args):
        self.__update_speed ()

    def __update_speed (self):
        drive = self.get_drive()
        if drive is None:
            self.__speed.widget.set_sensitive (False)
            return
            
        speed = drive.get_max_speed_write ()
        assert speed >= 0, speed

        val = self.__speed.data

        self.__speed.widget.set_range (1, speed)
        self.__speed.data = val
        
    def __on_specify_speed (self, widget, *args):
        # Sometimes the spinbox would get insensitive, so make sure it's not
        self.__speed.widget.set_sensitive(widget.get_active())
        self.__specify_speed.set_sensitive(widget.get_active())
    

class RecordingPreferences (object):
    debug = False
    overburn = False
    simulate = False
    
    def __init__ (self, locations):
        # By default use burnproof
        self.__write_flags = nautilusburn.RECORDER_WRITE_BURNPROOF
        # Sets up data dir and version
        self.version = release.version

        # setup ui
        filename = locations.get_data_file("serpentine.glade")
        g = glade.XML (filename, "preferences_dialog")
        self.__dialog = g.get_widget ("preferences_dialog")
        self.dialog.connect("destroy-event", self.__on_destroy)
        self.dialog.set_title(_("Serpentine Preferences"))
        
        # Drive selection
        drv = g.get_widget ("drive")
        cmb_drv = nautilusburn.DriveSelection ()
        cmb_drv.set_property ("show-recorders-only", True)
        cmb_drv.show ()
        
        self.__drive_selection = cmb_drv
        drv.pack_start (cmb_drv, False, False)
        
        # Speed selection
        self.__speed = WriteSpeed(g, self.__drive_selection.get_drive)
        
        # eject checkbox
        self.__eject = gaw.data_toggle_button (g.get_widget ("eject"),
                                               GCONF_DIR + "/eject")
        
        # use gap checkbox
        self.__use_gap = gaw.data_toggle_button (
            g.get_widget ("use_gap"),
            GCONF_DIR + "/use_gap",
            default = True
        )
        
        # temp
        ncb_temp_dir = NCB_GCONF_DIR + "/temp_iso_dir"
        gconf.client_get_default ().add_dir (ncb_temp_dir, gconf.CLIENT_PRELOAD_NONE)
        self.__tmp = gaw.GConfValue (
            key = ncb_temp_dir,
            data_spec = gaw.Spec.STRING,
            default = TEMP_DIR
        )
        
        # debug
        self.__debug = gaw.GConfValue (
            key = GCONF_DIR + "/debug_mode",
            data_spec = gaw.Spec.BOOL,
            default = False
        )
        
        # size
        self.__x = gaw.GConfValue(
            key = GCONF_DIR + "/x",
            data_spec = gaw.Spec.INT,
            default = 0,
        )
        
        self.__y = gaw.GConfValue(
            key = GCONF_DIR + "/y",
            data_spec = gaw.Spec.INT,
            default = 0,
        )

        self.__width = gaw.GConfValue(
            key = GCONF_DIR + "/width",
            data_spec = gaw.Spec.INT,
            default = 0,
        )

        self.__height = gaw.GConfValue(
            key = GCONF_DIR + "/height",
            data_spec = gaw.Spec.INT,
            default = 0,
        )
        
        # Pool
        self.__pool = GvfsMusicPool ()
        
        # Close button
        self.__close_button_handler = HideCloseButton(g.get_widget("close_btn"))

    
    ############################################################################
    # Properties
    
    ############
    # configDir
    __config_dir = path.join (path.expanduser ("~"), ".serpentine")
    def getConfigDir (self):
        return self.__config_dir
        
    configDir = property (lambda self: self.__config_dir)
    
    #########
    # dialog
    def getDialog (self):
        return self.__dialog
        
    dialog = property (getDialog)
    
    ##########
    # version
    def setVersion (self, version):
        assert isinstance (version, StringType)
        self.__version = version
        
    def getVersion (self):
        return self.__version
        
    version = property (getVersion, setVersion)
    
    ########
    # drive
    def getDrive (self):
        return self.__drive_selection.get_drive()
        
    drive = property (getDrive)
    
    ##############
    # useGnomeVfs
    def getUseGnomeVfs(self):
        return self.__pool.use_gnomevfs
    
    def setUseGnomeVfs(self, use_gnomevfs):
        self.__pool.use_gnomevfs = use_gnomevfs
    
    useGnomeVfs = property(getUseGnomeVfs, setUseGnomeVfs)
    
    ###############
    # temporary_dir
    
    def get_temporary_dir(self):
        return self.__tmp.data
    
    def set_temporary_dir(self, value):
        self.__tmp.data = value
        
    temporary_dir = property (get_temporary_dir, set_temporary_dir)
    
    def get_temporary_dirs(self):
        # First try the GConf temporary dir, then try the system TEMP dir
        # finally try on the HOME
        temps = (self.temporary_dir, TEMP_DIR, HOME_DIR)
        for temp in temps:
            if urlutil.is_local(temp) and _is_dir_writable(temp):
                yield urlutil.get_path(temp)
        
    def update_window_prefs(self, win):
        # get locations
        x = self.__x.data
        y = self.__y.data
        width = self.__width.data
        height = self.__height.data
        
        # Correct them
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if width < 200:
            width = 200
        if height < 200:
            height = 200

        # update them
        win.move(x, y)
        win.resize(width, height)
    
    def store_window_prefs(self, win):
        # store them on GConf
        self.__x.data, self.__y.data = win.get_position()
        self.__width.data, self.__height.data = win.get_size()
    
    ##############
    # useGap
    def getUseGap(self):
        return self.__use_gap.data
    
    useGap = property(getUseGap)

    #########
    # pool
    def getPool (self):
        return self.__pool
        
    pool = property (getPool)

    ##############
    # speedWrite
    def getSpeedWrite (self):
        return self.__speed.get()
        
    speedWrite = property (getSpeedWrite)
    
    ################
    # writeFlags
    def getWriteFlags (self):
        ret = self.__write_flags
        if not self.__use_gap.data:
            ret |= nautilusburn.RECORDER_WRITE_DISC_AT_ONCE
        if self.__eject.data:
            ret |= nautilusburn.RECORDER_WRITE_EJECT
        if self.debug:
            ret |= nautilusburn.RECORDER_WRITE_DEBUG
        if self.overburn:
            ret |= nautilusburn.RECORDER_WRITE_OVERBURN
        if self.simulate:
            ret |= nautilusburn.RECORDER_WRITE_DUMMY_WRITE

        return ret
        
    writeFlags = property (getWriteFlags)
    
    
    #############################
    # Methods
    def __on_destroy (self, *args):
        self.dialog.hide ()
        return False

    def savePlaylist (self, source):
        if not path.exists (self.configDir):
            os.makedirs (self.configDir)
        p = xspf.Playlist (title=_("Serpentine's playlist"), creator="Serpentine " + self.version)
        source.to_playlist (p)
        doc = p.toxml()
        
        out = SafeFileWrite (path.join (self.configDir, "playlist.xml"))
        try:
            doc.writexml (out, addindent = "\t", newl = "\n")
            del p
            out.close()
        except:
            out.abort ()
            return False
            
        return True
    
    def loadPlaylist (self, source):
        if not path.exists (self.configDir):
            os.makedirs (self.configDir)
        p = xspf.Playlist (title=_("Serpentine's playlist"), creator="Serpentine " + self.version)
        
        try:
            p.parse (path.join (self.configDir, "playlist.xml"))
        except IOError:
            return
            
        source.from_playlist (p)
