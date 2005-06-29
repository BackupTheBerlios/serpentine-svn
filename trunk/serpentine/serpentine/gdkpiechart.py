# Copyright (C) 2005 Tiago Cogumbreiro <cogumbreiro@users.sf.net>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# Authors: Tiago Cogumbreiro <cogumbreiro@users.sf.net>

from gtk import DrawingArea
import gobject, gtk.gdk, gtk

_CIRCLE = 360 * 64

class GdkPieChart (DrawingArea):
    def __init__ (self, values, getter):
        DrawingArea.__init__ (self)
        self.gc = None
        self.width = 0
        self.height = 0
        self.selected = []
        self.total = 0
        self.offset = 1
        self.getter = getter
        self.values = values
        self.connect ("size-allocate", self.__on_size_allocate)
        self.connect ("expose-event", self.__on_expose_event)
        self.connect ("realize", self.__on_realize)
    
    def __on_realize (self, widget):
        # self.gc = widget.window.new_gc ()
        
        style = self.get_style ()
        self.border_gc         = style.dark_gc[gtk.STATE_NORMAL]
        self.transparent_gc    = style.bg_gc[gtk.STATE_NORMAL]
        self.background_gc     = style.mid_gc[gtk.STATE_NORMAL]
        self.slice_gc          = style.base_gc[gtk.STATE_NORMAL]
        self.selected_slice_gc = style.base_gc[gtk.STATE_SELECTED]
    
    def __on_size_allocate (self, widget, allocation):
        self.width = allocation.width
        self.height = allocation.height
    
    def draw_slice (self, gc, offset, aperture):
        self.window.draw_arc (
            gc,
            True,
            0, # x
            0, # y
            self.radius, # width
            self.radius, # height
            offset,
            aperture,
        )
    
    def draw_circle (self, gc):
        self.draw_slice (gc, 0, _CIRCLE)
        
    def __on_expose_event (self, widget, event):
        offset = 0
        
        # Reset the selected index
        selected_slices = []
        index = 0
        
        # Get the real total
        total = 0
        for v in self.values:
            total  += self.getter (v)
        # Check if the gauge is filled    
        filled = total >= self.total
        
        self.draw_circle (self.background_gc)
        
        ratio = _CIRCLE / float (self.total)
        
        for value in self.values:
            # Get the angle aperture
            angle = int (self.getter (value) * ratio)
            
            if index in self.selected:
                #color = self.selected_color
                selected_slices.append ((offset, angle))
                
            elif not filled:
                self.draw_slice (self.slice_gc, offset, angle)
                
            offset += angle
            index += 1
        
        # When everything is filled we just paint a slice circle
        if filled:
            # Draw the border
            self.draw_circle (self.slice_gc)
        
        for offset, angle in selected_slices:
            self.draw_slice (self.selected_slice_gc, offset, angle)
        
        # Draw the little dial
        r = int (self.radius / 4)
        dx = self.radius/2 - r/2
        self.window.draw_arc (
            self.transparent_gc,
            True,
            dx,    # x
            dx,    # y
            r,
            r,
            0,
            _CIRCLE
        )
        # Draw inner dial border
        self.window.draw_arc (
            self.border_gc,
            False,
            dx,    # x
            dx,    # y
            r,
            r,
            0,
            _CIRCLE
        )

        
        # Draw the border
        self.window.draw_arc (
            self.border_gc,
            False,
            0,
            0,
            self.radius,
            self.radius,
            0,
            _CIRCLE
        )
    
    def draw ():
        self.__on_expose_event (self, self, self)
    
    def radius (self):
        return min (self.width, self.height) - self.offset
    radius = property (radius)
    

gobject.type_register (GdkPieChart)

from weakref import ref

class SerpentineUsage (object):
    def __init__ (self, parent):
        self.__parent = ref (parent)
        self.__overflow = False
        
        self.widget = GdkPieChart (values = self.parent.source,
                                   getter = lambda value: value['duration'])
                                   
        self.widget.total = self.parent.disc_size
        # Register as a GtkMusicList listener
        self.parent.source.listeners.append (self)
        # Register as a AudioMastering listener
        self.parent.listeners.append (self)
    
    # Basic properties
    def parent (self):
        return self.__parent()
    parent = property (parent)
    
    def __set_overflow (self, is_overflow):
        self.widget.filled = is_overflow
        self.__is_overflow = is_overflow
    
    def __get_overflow (self):
        return self.__overflow
    
    overflow = property (__get_overflow, __set_overflow)
    # Clean up references
    del __set_overflow, __get_overflow
    
    # GtkMusicList listener
    def on_contents_changed (self, *args):
        self.widget.queue_draw ()
        self.__update ()
        
    def on_musics_added (self, e, rows):
        self.widget.queue_draw ()
        self.__update ()
    
    on_musics_removed = on_musics_added
    
    def __update (self):
        self.overflow = self.widget.total < self.parent.source.total_duration
    
    # AudioMasterer listener
    def on_selection_changed (self, e):
        if not self.overflow:
            self.widget.selected = self.parent.get_selected ()
            self.widget.queue_draw ()
    
    def on_disc_size_changed (self, e):
        self.widget.total = self.parent.disc_size
        self.__update ()
        self.widget.queue_draw ()
        

if __name__ == '__main__':
    import gtk
    
    def cb (widget):
        widget.selected += 1
        widget.selected %= len (widget.values)
        widget.queue_draw ()
        return True
    
    w = gtk.Window (gtk.WINDOW_TOPLEVEL)
    vals = [dict(value=v) for v in [10, 3, 5]]
    pie = GdkPieChart (vals)
    pie.values = vals
    total = 0
    for v in vals:
        total += v['value']
    pie.total = total #* 2
    pie.selected = 1
    pie.show ()
    w.add (pie)
    w.show ()
    w.connect ("delete-event", gtk.main_quit)
    gobject.timeout_add (250, cb, pie)
    gtk.main ()