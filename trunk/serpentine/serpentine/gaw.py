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
"""
GConf Aware Widgets is a module for wrapping gtk widgets and keeping them in
sync with gconf keys.
"""
import gconf, gobject

class Spec (object):
	def __init__ (self, name, gconf_type, py_type, default):
		self.__gconf_type = gconf_type
		self.__py_type = py_type
		self.__default = default
		self.__name = name
	
	gconf_type = property (lambda self: self.__gconf_type)
	py_type = property (lambda self: self.__py_type)
	default = property (lambda self: self.__default)
	name = property (lambda self: self.__name)

Spec.STRING = Spec ('string', gconf.VALUE_STRING, str, '')
Spec.FLOAT = Spec ('float', gconf.VALUE_FLOAT, float, 0.0)
Spec.INT = Spec ('int', gconf.VALUE_INT, int, 0)
Spec.BOOL = Spec ('bool', gconf.VALUE_BOOL, bool, True)


def data_file_chooser (button, key, use_directory = False, use_uri = True,client = None):
	"""
	Returns a gaw.Data.
	
	use_directory - boolean variable setting if it's we're using files or directories.
	use_uri - boolean variable setting if we're using URI's or normal filenames.
	
	Associates a gaw.Data to a gtk.FileChooserButton. 
	"""
	if not use_directory and not use_uri:
		getter = button.get_filename
		setter = button.set_filename
	elif not use_directory and use_uri:
		getter = button.get_uri
		setter = button.set_uri
	elif use_directory and not use_uri:
		getter = button.get_current_folder
		setter = button.set_current_folder
	elif use_directory and use_uri:
		getter = button.get_current_folder_uri
		setter = button.set_current_folder_uri
		
	return Data (button, getter, setter, "selection-changed", key, Spec.STRING, client)

def data_entry (entry, key, data_spec = Spec.STRING, client = None):
	return Data (entry, entry.get_text, entry.set_text, "changed", key, data_spec, client)

def data_spin_button (spinbutton, key, use_int = True, client = None):
	if use_int:
		return Data (spinbutton, spinbutton.get_value_as_int, spinbutton.set_value, "value-changed", key, Spec.INT, client)
	else:
		return Data (spinbutton, spinbutton.get_value, spinbutton.set_value, 'value-changed', key, Spec.FLOAT, client)

def data_toggle_button (toggle, key, client = None):
	return Data (toggle, toggle.get_active, toggle.set_active, 'toggled', key, Spec.BOOL, client)

class Data (object):
	"""
	This utility class acts as a synchronizer between a widget and gconf entry.
	This data is considered to have problematic backends, since widgets can be
	destroyed and gconf can have problems (for example permissions). So in case
	of both data source have failed then we return the default value.
	"""
	
	def __init__ (self, widget, widget_getter, widget_setter, changed_signal, key, data_spec, client = None):
		self.__widget = widget
		self.__widget_getter = widget_getter
		self.__widget_setter = widget_setter
		self.__data_spec = data_spec
		
		if not client:
			client = gconf.client_get_default ()
			
		self.client = client
		
		self.key = key
		self.__gconf_getter = getattr (self.client, 'get_' + self.data_spec.name)
		self.__gconf_setter = getattr (self.client, 'set_' + self.data_spec.name)
		
		widget.connect (changed_signal, self.__on_widget_changed)
		widget.connect ('destroy', self.__on_destroy)
		self.__notify_id = self.client.notify_add (key, self.__on_gconf_changed)
		
		self.sync_widget ()
		
	widget = property (lambda self: self.__widget)
	data_spec = property (lambda self: self.__data_spec)
	
	def __set_client (self, client):
		assert isinstance (client, gconf.Client)
		self.__client = client
	
	def __set_key (self, key):
		assert isinstance (key, str), type(key)
		self.__key = key
		
	key = property (lambda self: self.__key, __set_key, None, "Associated gconf key.")
	
	def __get_data (self):
		if self.widget:
			# policy is widget has the most up to date data
			self.sync_gconf ()
		try:
			val = self.__gconf_getter (self.key)
			return val == None and self.data_spec.default or val
		except gobject.GError:
			if self.widget:
				# gconf is broken, return widget data
				val = self.__widget_getter ()
			else:
				# no widget return default
				return self.data_spec.default
	
	def __set_data (self, data):
		assert isinstance (data, self.data_spec.py_type)
		try:
			self.__gconf_setter (self.key, data)
		except gobject.GError:
			# when something goes wrong there's nothing we can do about it
			pass

	data = property (__get_data, __set_data, None, "The data contained in this component.")

	def __del__ (self):
		self.client.notify_remove (self.__notify_id)
		
	def __on_destroy (self, widget):
		self.__widget = None
		
	def __on_widget_changed (self, *args):
		self.sync_gconf ()
			
	def __on_gconf_changed (self, client, conn_id, entry, user_data = None):
		if not self.widget:
			return
			
		self.widget.set_sensitive (client.key_is_writable (self.key))
		if entry.value and entry.value.type == self.data_spec.gconf_type:
			converter = getattr (entry.value, 'get_' + self.data_spec.name)
			self.__widget_setter (converter ())
		else:
			self.__widget_setter (self.data_spec.default)
		# Because widgets can validate data, sync the gconf entry again
		self.sync_gconf()
	
	def sync_widget (self):
		"""
		Synchronizes the widget in favour of the gconf key. You must check if
		there is a valid widget before calling this method.
		"""
		assert self.widget, "Checking if there's a valid widget is a prerequisite."
		try:
			val = self.__gconf_getter (self.key)
			if val:
				self.__widget_setter (val)
		except gobject.GError:
			self.__widget_setter (self.data_spec.default)
		# Because some widgets change the value, update it to gconf again
		self.sync_gconf ()
		
	
	def sync_gconf (self):
		"""
		Synchronizes the gconf key in favour of the widget. You must check if
		there is a valid widget before calling this method.
		"""
		assert self.widget, "Checking if there's a valid widget is a prerequisite."
		val = self.__widget_getter ()
		try:
			self.__gconf_setter (self.key, val)
		except gobject.GError:
			pass
