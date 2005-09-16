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

import dbus, gobject

class BlockVolumeManager (object):
	"""This classes uses Hal to probe block devices which contain volumes (eg: optical drives) and is able to:
		- register callbacks when these volumes are inserted.
		- get the volume associated with a certain volume."""
		
	def __init__ (self):
		self.__devices = {}
		bus = dbus.SystemBus ()
		self.__service = bus.get_service ("org.freedesktop.Hal")
		self.__manager = self.hal_service.get_object ("/org/freedesktop/Hal/Manager",
		                                              "org.freedesktop.Hal.Manager")
		bus.add_signal_receiver (self.__on_device_added,
		                         "DeviceAdded",
		                         "org.freedesktop.Hal.Manager",
					 "org.freedesktop.Hal",
					 "/org/freedesktop/Hal/Manager")

		bus.add_signal_receiver (self.__on_device_removed,
		                         "DeviceRemoved",
					 "org.freedesktop.Hal.Manager",
					 "org.freedesktop.Hal",
					 "/org/freedesktop/Hal/Manager")
	
	hal_service = property (lambda self: self.__service)
	
	udi_to_device = lambda self, udi: self.hal_service.get_object (udi, "org.freedesktop.Hal.Device")
		
	
	def __on_device_added_loop (self, udi):
		#udi, = message.get_args_list ()
		dev = self.udi_to_device (udi)
		if dev.QueryCapability ("volume") and dev.QueryCapability ("block"):
			block_device = dev.GetProperty ("block.device")
			if self.__devices.has_key (block_device):
				self.__devices[block_device] (self, dev)
		
	def __on_device_added (self, interface, signal_name, service, path, message):
		print message
#		udi, = message.get_args_list ()
#		gobject.idle_add (self.__on_device_added_loop, udi)
#		return
#		dev = self.udi_to_device (udi)
#		if dev.QueryCapability ("volume") and dev.QueryCapability ("block"):
#			block_device = dev.GetProperty ("block.device")
#			if self.__devices.has_key (block_device):
#				self.__devices[block_device] (self, dev)
	
	def __on_device_removed (self, interface, signal_name, service, path, message):
		print message
	
	def register_block_device (self, block_device, callback):
		"""Registers a block deviced a callback which will be called when a volume is added to the
		block device.
		It can be used as following:
		
		block_man = BlockDeviceVolumeManager ()
		
		# Define the callback function
		def callback (block_manager, dbus_device):
			print "Source:", block_manager
			print "Label:", dbus_device.GetProperty ("volume.label")
			print "Block device:", dbus_device.GetProperty ("block.device")

		# Registrate the callback
		block_man.regiter_block_device ("/dev/hdd", callback)
		"""
		print "REGISTER BD:", block_device
		self.__devices[block_device] = callback
	
	def unregister_block_device (self, block_device, callback):
		"""Removes the callback associated with the given block device."""
		print "UNREGISTER BLOCK DEVICE", block_device
		del self.__devices[block_device]
	
	def get_volume_from_block_device (self, block_device):
		"""Returns the device volume object, if any, associated with a certain block device."""
		print "GET VOLUME"
		# XXX: segfaults
		return None
		devices = self.__manager.FindDeviceStringMatch ("block.device", block_device)
		for udi in devices:
			dev = self.udi_to_device (udi)
			if dev.QueryCapability ("volume"):
				return dev
		return None
	
