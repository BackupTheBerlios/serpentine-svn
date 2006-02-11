# -*- encoding: utf-8 -*-
import gtk
import os.path
import weakref

from xml.xpath import Evaluate
from xml.dom import minidom
from gettext import gettext as _

if __name__ == '__main__':
    import sys
    basedir = os.path.join (os.path.join(os.path.dirname (__file__), ".."), "..")
    sys.path.insert (0, basedir)

from serpentine import gtkutil

PLAYLISTS = os.path.join (os.path.expanduser("~"), ".gnome2", "rhythmbox", "playlists.xml")

def rhythmbox_list_names ():
    root = minidom.parse (PLAYLISTS)
    getvalue = lambda node: node.attributes["name"].value
    return map(getvalue, Evaluate ("/rhythmdb-playlists/playlist", root))

def rhythmbox_get_playlist (playlist_name):
    root = minidom.parse (PLAYLISTS)
    path = "/rhythmdb-playlists/playlist[@name = '%s']/location/text()" % playlist_name
    getvalue = lambda node: node.nodeValue
    return map(getvalue, Evaluate (path, root))

class RhythmboxListener (object):
    def __init__ (self, app):
        self._app = weakref.ref (app)
        self.create_window (self.app.window_widget)
    
    app = property (lambda self: self._app())
    
    def create_window (self, parent):
        setup = gtkutil.SetupDialog()
        
        dlg = gtk.Dialog (
            title='',
            parent = parent,
            buttons = (gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT)
        )
        dlg.set_has_separator (False)
        
        hbox = gtk.HBox (spacing = 6)
        hbox.show ()
        
        lbl = gtk.Label (_("Select playlist:"))
        lbl.show ()
        hbox.pack_start (lbl, False, False)
        
        cmb = gtk.combo_box_new_text ()
        cmb.show ()
        hbox.pack_start (cmb, False, False)
        
        dlg, vbox = setup(dlg, dlg.vbox)
        vbox.add (hbox)
        
        self.dlg = dlg
        self.cmb = cmb
        
    
    def populate (self):
        self.cmb.get_model ().clear ()
        elements = rhythmbox_list_names ()
        map(self.cmb.append_text, elements)
        self.cmb.set_active (0)
        return len(elements) > 0
        
    def on_clicked (self, menu):
        if not self.populate ():
            gtkutil.dialog_warn(
                _("No Rhythmbox playlist found"),
                _("Please create a playlist using <i>Music&#8594;Playlist&#8594;New Playlist...</i>"),
                parent=self.app.window_widget
            )
            return
            
        response = self.dlg.run ()
        self.dlg.hide ()
        
        if response == gtk.RESPONSE_ACCEPT:
            self.app.music_list.clear ()
            files = rhythmbox_get_playlist (self.cmb.get_active_text ())
            self.app.add_files (files).start ()
    
def create_plugin (app):
    if not hasattr (app, "window_widget"):
        return
    
    window = app.window_widget
    theme = gtk.icon_theme_get_default ()
    rhyt = gtk.ImageMenuItem (_("Open Rhythmbox Playlist..."))

    if theme.has_icon("rhythmbox"):
        img = gtk.image_new_from_icon_name("rhythmbox", gtk.ICON_SIZE_MENU)
        img.show ()
        rhyt.set_image (img)

    rhyt.show ()
    listener = RhythmboxListener (app)
    rhyt.connect ("activate", listener.on_clicked)
    
    file_menu = gtkutil.find_widget (window, "file_menu")
    file_menu.add (rhyt)
    file_menu.reorder_child (rhyt, 4)

if __name__ == '__main__':
    import sys

    if len (sys.argv) != 2:
        print rhythmbox_list_names ()
    
    else:
        print rhythmbox_get_playlist (sys.argv[1])