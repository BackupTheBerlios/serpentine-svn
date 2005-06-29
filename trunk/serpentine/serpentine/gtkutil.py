# Copyright (C) 2004 Tiago Cogumbreiro <cogumbreiro@users.sf.net>
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

import gtk, gobject

class DictModelIterator:
	def __init__ (self, parent):
		self.parent = parent
		self.index = 0
		
	def __iter__ (self):
		return self
	
	def next (self):
		if len(self.parent) <= self.index:
			raise StopIteration
		
		ret = self.parent.get(self.index)
		self.index += 1
		return ret
		
class DictStore (gtk.ListStore):
	def __init__ (self, *cols):
		self.indexes = {}
		self.cols = []
		spec = []
		index = 0
		for c in cols:
			# Generate indexes dict
			self.indexes[c["name"]] = index
			spec.append (c["type"])
			self.cols.append (c["name"])
			index += 1
		gtk.ListStore.__init__ (self, *tuple(spec))
		
	def __dict_to_list (self, row):
		values = []
		for key in self.cols:
			values.append (row[key])
		return values
		
	def append (self, row):
		gtk.ListStore.append (self, self.__dict_to_list (row))
	
	def insert_before (self, iter, row):
		gtk.ListStore.insert_before (self, iter, self.__dict_to_list (row))
	
	def insert_after (self, iter, row):
		gtk.ListStore.insert_after (self, iter, self.__dict_to_list (row))
		
	def index_of (self, key):
		return self.indexes[key]
	def get (self, index):
		return DictModelRow(self, self[index])
	def __iter__ (self):
		return DictModelIterator(self)
		
gobject.type_register (DictStore)

class DictModelRow (object):
	def __init__ (self, parent, row):
		self.parent = parent
		self.row = row
		
	def __getitem__ (self, key):
		return self.row[self.parent.indexes[key]]
		
	def __setitem__ (self, key, value):
		self.row[self.parent.indexes[key]] = value
		
	def __delitem__ (self, key):
		del self.row[self.parent.indexes[key]]
	
	def keys(self):
		return self.parent.cols
	
	def get (self, key, default):
		if self.has_key (key):
			return self[key]
		return default
	
	def has_key (self, key):
		return key in self.keys()

	__contains__ = has_key

class SimpleListWrapper:
	def __init__ (self, store):
		self.store = store
		
	def __getitem__ (self, index):
		return self.store[index][0]
		
	def append (self, item):
		self.store.append ([item])

class SimpleList (gtk.TreeView):
	def __init__ (self, column_title, editable = True):
		gtk.TreeView.__init__(self)
		store = gtk.ListStore(str)
		self.set_model (store)
		r = gtk.CellRendererText()
		if editable:
			r.set_property ('editable', True)
			r.connect ('edited', self.__on_text_edited)
			
		if not column_title:
			self.set_headers_visible (False)
			column_title = ""
		col = gtk.TreeViewColumn(column_title, r, text = 0)
		self.append_column (col)
		self.wrapper = SimpleListWrapper (store)
		
	def get_simple_store(self):
		return self.wrapper
	
	def __on_text_edited (self, cell, path, new_text, user_data = None):
		self.get_model()[path][0] = new_text

gobject.type_register (SimpleList)

dialog_error = \
	lambda primary_text, secondary_text, parent = None:\
		hig_alert (primary_text,
		           secondary_text,
		           parent,
		           stock = gtk.STOCK_DIALOG_ERROR,
		           buttons = (gtk.STOCK_CLOSE, gtk.RESPONSE_OK))
	

dialog_warn = \
	lambda primary_text, secondary_text, parent = None:\
		hig_alert (primary_text,
		           secondary_text,
		           parent,
		           stock = gtk.STOCK_DIALOG_WARNING,
		           buttons = (gtk.STOCK_CLOSE, gtk.RESPONSE_OK))

dialog_ok_cancel = \
	lambda primary_text, secondary_text, parent = None, ok_button = gtk.STOCK_OK: \
		hig_alert (primary_text,
		           secondary_text,
		           parent,
		           stock = gtk.STOCK_DIALOG_WARNING,
		           buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
		                      ok_button, gtk.RESPONSE_OK))

def hig_label (text = None):
	lbl = gtk.Label ()
	lbl.set_alignment (0, 0)
	if text:
		lbl.set_markup (text)
	lbl.set_selectable (True)
	lbl.set_line_wrap (True)
	return lbl

def hig_alert (primary_text, secondary_text, parent = None, flags = 0, buttons = (gtk.STOCK_OK, gtk.RESPONSE_OK), stock = gtk.STOCK_DIALOG_INFO, default = gtk.STOCK_OK):
	dlg = gtk.Dialog (parent = parent, flags = flags, buttons = buttons)
	dlg.set_border_width (6)
	dlg.set_resizable (False)
	dlg.set_has_separator (False)
	dlg.get_child().set_spacing (12)
	dlg.set_title ('')
	
	hbox = gtk.HBox(spacing = 12)
	hbox.set_border_width (6)
	hbox.show ()
	dlg.get_child().pack_start (hbox)
	
	img = gtk.Image()
	img.set_from_stock (stock, gtk.ICON_SIZE_DIALOG)
	img.set_alignment (img.get_alignment()[0], 0.0)
	img.show ()
	hbox.pack_start (img, False, False)
	
	vbox = gtk.VBox (spacing = 6)
	vbox.show ()
	hbox.pack_start(vbox)
	
	lbl = hig_label ('<span weight="bold" size="larger">'+primary_text+'</span>')
	lbl.show ()
	vbox.pack_start (lbl, False, False)
	
	lbl = hig_label (secondary_text)
	lbl.show ()
	vbox.pack_start (lbl, False, False)
	reply = dlg.run()
	dlg.destroy()
	return reply
	
class HigProgress (gtk.Window):
	"""
	HigProgress returns a window that contains a number of properties to
	access what a common Progress window should have.
	"""
	def __init__ (self):
		gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
		self.set_border_width (6)
		self.set_resizable (False)
		self.set_title ('')
		# defaults to center location
		self.set_position (gtk.WIN_POS_CENTER)
		self.connect ("delete-event", self.__on_close)
		
		# main container
		main = gtk.VBox (spacing = 12)
		main.set_spacing (12)
		main.set_border_width (6)
		main.show()
		self.add (main)
		
		# primary text
		alg = gtk.Alignment ()
		alg.set_padding (0, 6, 0, 0)
		alg.show()
		main.pack_start (alg, False, False)
		lbl = hig_label()
		lbl.set_selectable (False)
		lbl.show()
		self.__primary_label = lbl
		alg.add (lbl)
		
		# secondary text
		lbl = hig_label()
		lbl.set_selectable (False)
		lbl.show()
		main.pack_start (lbl, False, False)
		self.__secondary_label = lbl
		
		# Progress bar
		vbox = gtk.VBox()
		vbox.show()
		main.pack_start (vbox, False, False)
		
		prog = gtk.ProgressBar ()
		prog.show()
		self.__progress_bar = prog
		vbox.pack_start (prog, expand = False)
		
		lbl = hig_label ()
		lbl.set_selectable (False)
		lbl.show ()
		self.__sub_progress_label = lbl
		vbox.pack_start (lbl, False, False)
		
		# Buttons box
		bbox = gtk.HButtonBox ()
		bbox.set_layout (gtk.BUTTONBOX_END)
		bbox.show ()
		
		# Cancel Button
		cancel = gtk.Button (gtk.STOCK_CANCEL)
		cancel.set_use_stock (True)
		cancel.show ()
		self.__cancel = cancel
		bbox.add (cancel)
		main.add (bbox)
		
		# Close button, which is hidden by default
		close = gtk.Button (gtk.STOCK_CLOSE)
		close.set_use_stock (True)
		close.hide ()
		bbox.add (close)
		self.__close = close
		
	primary_label = property (lambda self: self.__primary_label)
	secondary_label = property (lambda self: self.__secondary_label)
	progress_bar = property (lambda self: self.__progress_bar)
	sub_progress_label = property (lambda self: self.__sub_progress_label)
	cancel_button = property (lambda self: self.__cancel)
	close_button = property (lambda self: self.__close)
	
	def primary_text (self, text):
		self.primary_label.set_markup ('<span weight="bold" size="larger">'+text+'</span>')
		self.set_title (text)
	
	primary_text = property (fset = primary_text)
		
	def secondary_text (self, text):
		self.secondary_label.set_markup (text)
	
	secondary_text = property (fset = secondary_text)
	
	def progress_fraction (self, fraction):
		self.progress_bar.set_fraction (fraction)
	
	progress_fraction = property (fset = progress_fraction)
	
	def progress_text (self, text):
		self.progress_bar.set_text (text)
	progress_text = property (fset = progress_text)
	
	def sub_progress_text (self, text):
		self.sub_progress_label.set_markup ('<i>'+text+'</i>')
	sub_progress_text = property (fset = sub_progress_text)
	
	def __on_close (self, *args):
		if not self.cancel_button.get_property ("sensitive"):
			return True
		# click on the cancel button
		self.cancel_button.clicked ()
		# let the clicked event close the window if it likes too
		return True
		
gobject.type_register (HigProgress)

def find_widget_up (widget, name):
	"""Finds a widget by name upwards the tree, by searching self and its
	parents"""
	
	assert widget is not None
	
	if widget.get_name () == name:
		return widget
	
	parent = widget.get_parent ()
	if parent is not None:
		return find_widget (parent, name)
	
	return None

def find_widget (widget, name):
	"""Finds the widget by name downwards the tree, by searching self and its
	children."""
	
	assert widget is not None
	
	if widget.get_name () == name:
		return widget
		
	get_children = getattr (widget, "get_children", None)

	if get_children is None:
		return None
	
	for child in get_children ():
		w = find_widget (child, name)
		if w is not None:
			return w
	
	get_submenu = getattr (widget, "get_submenu", None)
	
	if get_submenu is None:
		return None
	
	sub_menu = get_submenu ()
	
	if sub_menu is not None:
		return find_widget (sub_menu, name)
	
	return None

def get_root_parent (widget):
	assert widget is not None
	p = widget.get_parent ()
	if not p:
		return widget
	return get_root_parent (p)

import traceback
def traceback_main_loop ():
	idle_add = gobject.idle_add
	
	def tb_idle_add (callback, *args, **kwargs):
		def wrapper (*args, **kwargs):
			try:
				return callback (*args, **kwargs)
			except:
				traceback.print_exc ()
		
		return idle_add (wrapper, *args, **kwargs)
	gobject.idle_add = tb_idle_add
	gobject.idle_add.idle_add = idle_add
	
	timeout_add = gobject.timeout_add
	
	def tb_timeout_add (interval, callback, *args, **kwargs):
		def wrapper (*args, **kwargs):
			try:
				return callback (*args, **kwargs)
			except:
				traceback.print_exc ()
		
		return timeout_add (interval, wrapper, *args, **kwargs)
		
	gobject.timeout_add = tb_timeout_add
	gobject.timeout_add.timeout_add = timeout_add

def untraceback_main_loop ():
	if hasattr (gobject.idle_add, "idle_add"):
		gobject.idle_add = gobject.idle_add.idle_add
		
	if hasattr (gobject.timeout_add, "timeout_add"):
		gobject.timeout_add = gobject.timeout_add.timeout_add
