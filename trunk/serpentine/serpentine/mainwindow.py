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

import gtk
import os
import os.path
import gobject
import webbrowser

# Local imports
import operations
import gaw
import gtkutil
import gconf

from components import Component
from operations import MapProxy, OperationListener
from mastering import AudioMastering

from serpentine.common import SerpentineNotSupportedError
from serpentine.common import SerpentineCacheError
from gettext import gettext as _

D_G_INTERFACE = "/desktop/gnome/interface"

# Make sure the URLs are clickable
def open_url(dlg, url):
    webbrowser.open_new(url)

gtk.about_dialog_set_url_hook(open_url)

for gconf_dir in (D_G_INTERFACE,):
    gconf.client_get_default ().add_dir (gconf_dir, gconf.CLIENT_PRELOAD_NONE)

class GladeComponent (Component):

    def _setup_glade (self, g):
        """This method is called when the SerpentineWindow object is created."""

class FileDialogComponent (GladeComponent):
    def __init__ (self, parent):
        super (FileDialogComponent, self).__init__ (parent)
        
        # Open playlist file dialog
        self.file_dlg = gtk.FileChooserDialog (
            parent = self.parent,
            buttons = (
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OPEN, gtk.RESPONSE_OK
            )
        )
        self.file_dlg.set_title("")
        self.file_dlg.set_transient_for(self.parent)
        self.file_dlg.set_current_folder(os.path.expanduser("~"))
        self.file_dlg.set_property("local-only", False)
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

class SavePlaylistComponent (GladeComponent):
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
        self.file_dlg.set_current_folder (os.path.expanduser("~"))
        hbox = gtk.HBox (spacing = 6)
        hbox.show ()
        
        lbl = gtk.Label(_("Save playlist in format:"))
        lbl.show ()
        hbox.pack_start (lbl, False, False)
        
        store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        cmb = gtk.ComboBox (store)
        cmb.show ()
        cell = gtk.CellRendererText()
        cmb.pack_start(cell, True)
        cmb.add_attribute(cell, 'text', 0)
        self.combo = cmb
        hbox.pack_start (cmb, False, False)

        self.store = store
        store.append ((_("Detect by extension"), ""))
        cmb.set_active (0)
        
        self.file_dlg.set_extra_widget (hbox)
        app = self.parent.application
        app.savePlaylist.listeners.append (self)
        self.__sync = True
    
    def on_registred (self, factory, extension, description):
        self.__sync = True
        self.store.append (("%s (%s)" % (description, extension), extension))
    
    def on_finished (self, evt):
        win = self.parent
            
        if evt.id != operations.SUCCESSFUL:
            gtkutil.dialog_error (
                _("Playlist Not Saved"),
                _("There was an error while saving the playlist."),
                parent = win
            )
        
    def __sync_file_filters (self):
        if not self.__sync:
            return
        
        app = self.parent.application
        
        # Remove old filters
        for f in self.file_dlg.list_filters ():
            self.file_dlg.remove_filter (f)
        
        # Now fill the real filters
        for f in app.savePlaylist.file_filters:
            self.file_dlg.add_filter (f)
        
        # Sync is complete
        self.__sync = False
    
    def run_dialog (self, *args):
        app = self.parent.application
        win = self.parent
        
        self.__sync_file_filters ()
        
        while self.file_dlg.run () == gtk.RESPONSE_OK:
            filename = self.file_dlg.get_filename ()
            basename = os.path.basename (filename)
            index = self.combo.get_active ()
            if index == 0:
                extension = None
            else:
                extension = self.store[index][1]
                
            if os.path.exists (filename) and gtkutil.dialog_ok_cancel (
                _("Replace existing file"),
                _("A file named <i>%s</i> already exists. "
                "Do you want to replace it with the one "
                "you are saving?") % basename,
                parent = win
            ) != gtk.RESPONSE_OK:
                
                self.file_dlg.unselect_all()
                self.file_dlg.hide()
                return
            
            try:
                oper = app.savePlaylist.save (filename, extension)
                oper.listeners.append (self)
                oper.start ()
                break

            except SerpentineNotSupportedError:
                # In this case the user supplied a wrong extension
                # let's ask for him to choose one
                
                if extension is None:
                    # convert to strings
                    items = map(lambda row: row[0], self.store)
                    # First row is useless
                    del items[0]
                    
                    indexes, response = gtkutil.choice_dialog(
                        _("Select one playlist format"),
                        _("Serpentine will open any of these formats so the "
                          "one you choose only matters if you are going to "
                          "open with other applications."),
                        one_text_item = _("Do you want to save as the %s "
                                          "format?"),
                        min_select = 1,
                        max_select = 1,
                        parent = win,
                        items = items,
                        ok_button = gtk.STOCK_SAVE,
                    )
                    if len(indexes) != 0:
                        index, = indexes
                        # Since we deleted the first row from the items then
                        # the index have an offset of 1
                        index += 1
                        row = self.store[index]
                        extension = row[1]
                        
                        # Save the file
                        oper = app.savePlaylist.save (filename, extension)
                        oper.listeners.append (self)
                        oper.start ()
                        
                        # Select the option in the list store
                        self.combo.set_active(index)
                        break
                        
                        
                else:
                    gtkutil.dialog_error (
                        _("Unsupported Format"),
                        _("The playlist format you used (by the file extension) is "
                        "currently not supported."),
                        parent = win
                    )
                    
            
        self.file_dlg.unselect_all()
        self.file_dlg.hide()

class ToolbarComponent (GladeComponent):
    Style = {
        "both": gtk.TOOLBAR_BOTH,
        "both-horiz": gtk.TOOLBAR_BOTH_HORIZ,
        "icons": gtk.TOOLBAR_ICONS,
        "text": gtk.TOOLBAR_TEXT
    }
    
    def _setup_glade (self, g):
        # Toolbar style
        self.__style = gaw.GConfValue (
            key = "/desktop/gnome/interface/toolbar_style",
            data_spec = gaw.Spec.STRING,
        )
        self.__style.set_callback (self.__on_style_change)
        
        # Detachable toolbar
        self.__detachable = gaw.GConfValue (
            key = "/desktop/gnome/interface/toolbar_detachable",
            data_spec = gaw.Spec.BOOL
        )
        self.__detachable.set_callback (self.__on_detachable_change)
        
        self.toolbar = g.get_widget ("main_toolbar")
        self.handle = g.get_widget ("main_handle")
        self.wrapper = g.get_widget ("main_toolbar_wrapper")
        
        # Show hide toolbar
        view_toolbar = g.get_widget ("view_toolbar_mni")
        self.__visible = gaw.data_toggle_button (
            toggle = view_toolbar,
            key = "/apps/serpentine/view_toolbar",
            default = True
        )
        view_toolbar.connect ("toggled", self.__on_toolbar_visible)
        
        # Update to current state
        self.__on_style_change ()
        self.__on_detachable_change ()
        self.__on_toolbar_visible ()
    
    def __on_toolbar_visible (self, *args):
        if self.__visible.data:
            self.wrapper.show ()
        else:
            self.wrapper.hide ()
        
    def __on_detachable_change (self, *args):
        widget = self.wrapper.get_children()[0]
        
        if self.detachable:
            if widget == self.handle:
                return
            
            self.wrapper.remove (widget)
            self.wrapper.add (self.handle)
            self.handle.add (self.toolbar)
        else:
            if widget == self.toolbar:
                return
            self.handle.remove (self.toolbar)
            self.wrapper.remove (widget)
            self.wrapper.add (self.toolbar)
            
    def __on_style_change (self, *args):
        self.toolbar.set_style (self.style)
    
    def detachable (self):
        try:
            detachable = self.__detachable.data
        except:
            detachable = False
        if not isinstance (detachable, bool):
            detachable = False
        
        return detachable
    detachable = property (detachable)
    
    def style (self):
        try:
            style = self.__style.data
        except:
            style = "both"
        
        if style in ToolbarComponent.Style:
            return ToolbarComponent.Style[style]
        else:
            return ToolbarComponent.Style["both"]
            
    style = property (style)

class SerpentineWindow (gtk.Window, OperationListener, operations.Operation, Component):
    # TODO: finish up implementing an Operation
    components = (
        AddFileComponent,
        PlaylistComponent,
        SavePlaylistComponent,
        ToolbarComponent
    )
    
    def __init__ (self, application):
        gtk.Window.__init__ (self, gtk.WINDOW_TOPLEVEL)
        operations.Operation.__init__ (self)
        Component.__init__ (self, application)
            
        self.__application = application
        self.__masterer = AudioMastering (application)
        # Variable related to this being an Operation
        self.__running = False
        self.connect ("show", self.__on_show)
        # We listen for GtkMusicList events
        self.music_list_widget.listeners.append(self)
        
        glade_file = application.locations.get_data_file("serpentine.glade")
        g = gtk.glade.XML (glade_file, "main_window_container")
        
        # Send glade to setup subcomponents
        for c in self._components:
            if hasattr (c, "_setup_glade"):
                c._setup_glade (g)

        self.add (g.get_widget ("main_window_container"))
        self.set_title ("Serpentine")
        self.set_default_size (450, 350)
        self.application.preferences.update_window_prefs(self)
        self.connect("delete-event", self.on_delete_window)
        
        self.set_icon_name ("gnome-dev-cdrom-audio")
        
        
        # record button
        # setup record button
        self.__write_to_disc = MapProxy (dict(
            button = g.get_widget ("write_to_disc"),
            menu   = g.get_widget ("write_to_disc_mni")
        ))
        
        self.__write_to_disc.set_sensitive (False)
        self.__write_to_disc["button"].connect ("clicked", self.__on_write_files)
        self.__write_to_disc["menu"].connect ("activate", self.__on_write_files)
        
        # masterer widget
        box = self.get_child()
        self.music_list_widget.show()
        box.add (self.music_list_widget)
        
        # preferences
        g.get_widget ("preferences_mni").connect ("activate", self.__on_preferences)
        
        # setup remove buttons
        self.remove = MapProxy ({"menu": g.get_widget ("remove_mni"),
                                 "button": g.get_widget ("remove")})

        self.remove["menu"].connect ("activate", self.__on_remove_file)
        self.remove["button"].connect ("clicked", self.__on_remove_file)
        self.remove.set_sensitive (False)
        
        # setup clear buttons
        self.clear = MapProxy ({"menu": g.get_widget ("clear_mni"),
                                "button": g.get_widget ("clear")})
        self.clear["button"].connect ("clicked", self.clear_files)
        self.clear["menu"].connect ("activate", self.clear_files)
        self.clear.set_sensitive (False)
        
        # setup quit menu item
        g.get_widget ("quit_mni").connect ("activate", self.stop)
        self.connect("delete-event", self.stop)
        
        # About dialog
        g.get_widget ("about_mni").connect ("activate", self.__on_about)
        
        # update buttons
        self.on_contents_changed()
        
        if self.__application.preferences.drive is None:
            gtkutil.dialog_warn (
                _("No recording drive found"),
                _("No recording drive found on your system, therefore some of "
                  "Serpentine's functionalities will be disabled."),
                parent = self
            )
            g.get_widget ("preferences_mni").set_sensitive (False)
            self.__write_to_disc.set_sensitive (False)
    
        # Load internal XSPF playlist
        self.__load_playlist()
        
    music_list_widget = property (lambda self: self.__masterer)
    
    music_list = property (lambda self: self.__masterer.music_list)
    
    can_start = property (lambda self: True)
    # TODO: handle the can_stop property better
    can_stop = property (lambda self: True)
    
    masterer = property (lambda self: self.__masterer)
    
    application = property (lambda self: self.__application)
    
    def on_delete_window(self, win, evt):
        self.application.preferences.store_window_prefs(self)
    
    def __on_show (self, *args):
        self.__running = True
    
    def __load_playlist (self):
        #TODO: move it to SerpentineApplication ?
        """Private method for loading the internal playlist."""
        try:
            self.__application.preferences.loadPlaylist (self.music_list_widget.source)
        except:
            import traceback
            traceback.print_exc()
            
    def on_selection_changed (self, *args):
        self.remove.set_sensitive (self.music_list_widget.count_selected() > 0)
        
    def on_contents_changed (self, *args):
        is_sensitive = len(self.music_list_widget.source) > 0
        self.clear.set_sensitive (is_sensitive)
        # Only set it sentitive if the drive is available and is not recording
        if self.__application.preferences.drive is not None:
            self.__write_to_disc.set_sensitive (is_sensitive)

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
        a = gtk.AboutDialog()
        a.set_name("Serpentine")
        a.set_version(self.__application.preferences.version)
        a.set_website("http://developer.berlios.de/projects/serpentine")
        a.set_copyright("2004-2006 Tiago Cogumbreiro <cogumbreiro@users.sf.net>")
        a.set_transient_for(self)
        a.set_authors(
            ("Tiago Cogumbreiro <cogumbreiro@users.sf.net>",
             "Alessandro Decina <alessandro@nnva.org>",)
        )
        a.set_translator_credits(_("translator-credits"))
        a.set_comments(_("Audio CD Creator"))
        a.run()
        a.destroy()
    
    def __on_write_files (self, *args):
        # TODO: move this to SerpentineApplication.write_files ?
        try:
            self.__application.validate_files()
            
        except SerpentineCacheError, err:
            show_prefs = False
            
            if err.error_id == SerpentineCacheError.INVALID:
                title = _("Cache directory location unavailable")
                show_prefs = True
                
            elif err.error_id == SerpentineCacheError.NO_SPACE:
                title = _("Not enough space on cache directory")
            
            gtkutil.dialog_warn (title, err.error_message, parent = self)
            return
        
        # TODO: move this to recording module?
        if self.music_list_widget.source.total_duration > self.music_list_widget.disc_size:
            title = _("Do you want to overburn your disc?")
            msg = _("You are about to record a media disc in overburn mode. "
                    "This may not work on all drives and shouldn't give you "
                    "more then a couple of minutes.")
            btn = _("Write to Disc (Overburning)")
            self.__application.preferences.overburn = True
        else:
            title = _("Do you want to record your music?")
            msg = _("You are about to record a media disc. "
                    "Canceling a writing operation will make "
                    "your disc unusable.")
                    
            btn = _("Write to Disc")
            self.__application.preferences.overburn = False
        
        if gtkutil.dialog_ok_cancel (title, msg, parent = self, ok_button = btn) != gtk.RESPONSE_OK:
            return
        
        self.application.write_files().start()
    
    # Start is the same as showing a window, we do it every time
    start = gtk.Window.show

    def stop (self, *args):
        self._send_finished_event (operations.SUCCESSFUL)
        self.hide ()
