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

import dbus, nautilusburn

import mastering
SERVICE_DOMAIN = "de.berlios.Serpentine"
OBJECT_DOMAIN = "/de/berlios/Serpentine"


class Manager (dbus.Object):
	"""Provides services for Serpentine. It launches all needed services.
	It registers the de.berlios.Serpentine.Manager, 
	de.berlios.Serpentine.Playlist and de.berlios.Serpentine.Recorder
	interfaces.
	"""
	def __init__ (self, service, serpentine_object):
		dbus.Object.__init__ (self,
		                      OBJECT_DOMAIN + "/Manager",
		                      service, [
			self.Quit,
			self.RecordPlaylist
		])
		self.__serp = serpentine_object
		# Register the Playlist
		self.__playlist = Playlist (OBJECT_DOMAIN + "/Playlist", self.serpentine.masterer.source)
		self.__update_drives ()
	
	def __update_drives (self):
		self.__drives = {}
		for dev in nautilusburn.get_drives_list (True):
			device = dev.get_device ()
			self.__drives[device] = Recorder (serpentine_object, device)
	
	serpentine = property (lambda self: self.__serp)
	playlist = property (lambda self: self.__playlist)
	
	def Quit (self, message):
		self.serpentine.quit ()
	
	def RecordPlaylist (self, message):
		self.serpentine.burn ()
	

class Playlist (dbus.Object):
	"""Represents the serpentine storage."""
	def __init__ (self, domain, service, music_list):
		dbus.Object.__init__ (self,
		                      domain,
		                      service, [
			self.Clear,
			self.Remove,
			self.Add
		])
		self.__music_list = music_list
		
	music_list = property (lambda self: self.__music_list)
	
	def Clear (self, message):
		self.music_list.clear ()
		
	def Remove (self, message, music):
		for music in self.music_list:
			if music['location'] == music:
				music_list.remove (music)
				return

	def Add (self, message, music):
		hints = {"location": music}
		add_oper = mastering.AddFile (self.music_list, hints)
		# TODO: add a listener and a signal event for this
		add_oper.start ()


class AudioRecorder (dbus.Object):
	"""Represents a recorder that can write audio tracks directly."""
	def __init__ (self, domain, device):
		if device.startswith ("/"):
			name = device[1:].replacewith ("/", ".")
		
		dbus.Object.__init__ (self,
		                      domain + "/" + name,
		                      "de.berlios.Serpentine.AudioRecorder", [
			self.WriteFiles,
			self.IsRecording,
			self.GetDevice
		])
		
		self.__device = device
	
	device = property (lambda self: self.__device)
	
	def WriteFiles (self, message, files):
		return "There is no multiple drives preference yet."
		
	def IsRecording (self, message):
		return self.device in self.serpentine.recording
	
	def GetDevice (self, message):
		return self.device
