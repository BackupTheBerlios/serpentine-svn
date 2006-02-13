import gtk
from math import cos, sin
import math

TWO_PI = math.pi * 2


X = 0
Y = 1
_getx = lambda x, radius, angle: x + cos(angle) * radius
_gety = lambda y, radius, angle: y + sin(angle) * radius
_getxy = lambda center, radius, angle: (_getx(center[X], radius, angle), _gety(center[Y], radius, angle))

def sketch_arc(ctx, center, radius, offset, apperture):
    
    angle1 = offset
    angle2 = offset + apperture
    corner1 = _getxy(center, radius, angle1)
    corner2 = _getxy(center, radius, angle2)
    
    ctx.move_to(*center)
    ctx.line_to(*corner1)
    ctx.arc(center[X], center[Y], radius, angle1, angle2)
    ctx.line_to(center[X], center[Y])

def sketch_radius(ctx, center, radius, angle):
    ctx.move_to(*center)
    ctx.line_to(*_getxy(center, radius, angle))


class CairoPieChart(gtk.DrawingArea):
    def __init__(self, values, getter):
        super(CairoPieChart, self).__init__()
        self.connect("expose-event", self._on_exposed)
        self.values = values
        self.selected = []
        self.getter = getter
        self.values = values
    

    def _on_exposed(self, me, evt):
        self.draw(evt)
    
    def draw_slice(self, center, radius, offset, percentage, color, ctx):
        offset *= math.pi * 2
        apperture = percentage * math.pi * 2
        
        ctx.set_source_color(color)
        sketch_arc(ctx, center, radius, offset, apperture)
        ctx.close_path()
        ctx.fill()
        
        ctx.set_source_color(self.get_border_color())
        sketch_radius(ctx, center, radius, offset)
        ctx.stroke()

    def draw_background(self, center, radius, ctx):
        ctx.set_source_color(self.style.bg[gtk.STATE_NORMAL])
        ctx.arc(center[X], center[Y], radius, 0, TWO_PI)
        ctx.fill()

    def draw_border(self, center, radius, ctx):
        ctx.set_source_color(self.get_border_color())
        ctx.arc(center[X], center[Y], radius, 0, TWO_PI)
        ctx.stroke()

        
    def get_border_color(self):
        return self.style.dark[gtk.STATE_NORMAL]
    
    def get_normal_background_color(self):
        return self.style.base[gtk.STATE_NORMAL]

    def get_selected_background_color(self):
        return self.style.base[gtk.STATE_SELECTED]

    def get_empty_background_color(self):
        return self.style.mid[gtk.STATE_NORMAL]

    def get_background_color(self):
        return self.style.bg[gtk.STATE_NORMAL]


       
    def draw(self, evt):
        rect = self.allocation
        radius = min(rect.width / 2.0, rect.height / 2.0) - 5
        if radius <= 0:
            return
        
        x = rect.width / 2.0
        y = rect.height / 2.0
        center = (x, y)
        
        small_radius = radius * 0.20
        self.total = float(self.total)
        
        ctx = self.window.cairo_create()
        ctx.set_line_width(0.75)
 
        offset = 0.0
        for index, val in enumerate(self.values):
            apperture = self.getter(val) / self.total
            selected = index in self.selected

            if selected:
                bg = self.get_selected_background_color()
            else:
                bg = self.get_normal_background_color()
                
                
            assert offset + apperture <= 1
            self.draw_slice(center, radius, offset, apperture, bg, ctx)
            offset += apperture
        
        if offset < 1:
            bg = self.get_empty_background_color()
            self.draw_slice(center, radius, offset, 1.0 - offset, bg, ctx)

        self.draw_background(center, small_radius, ctx)
        self.draw_border(center, small_radius, ctx)
        self.draw_border(center, radius, ctx)




def main():
    window = gtk.Window()
    chart = CairoPieChart([10,12], lambda x: x)
    chart.total = 22
    chart.selected = [0]
    chart.show()
    chart.set_size_request(64, 64)

    btn = gtk.Button("Hi")
    btn.show()
    vbox = gtk.VBox()
    vbox.show()
    vbox.add(btn)
    vbox.add(chart)
    window.add(vbox)

    #window.add(chart)
    window.connect("destroy", gtk.main_quit)
    window.show()
    gtk.main()

if __name__ == '__main__':
    main()
