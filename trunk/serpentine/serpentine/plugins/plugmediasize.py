"""Plugin that looks up the system and tries to change the media size selection
widget accordingly.
"""
import nautilusburn, gobject

# DBus breaks my app :(
from serpentine import mediaprober
#mediaprober = None

class SerpentineMediaLookup (object):
	def __init__ (self, serpentine_object):
		self.__serpentine = serpentine_object
		self.__drive = None
		self.serpentine.preferences.drive_listeners.append (self.__on_drive_changed)
		
		if mediaprober is not None:
			self.__media_prober = mediaprober.BlockVolumeManager ()
		else:
			gobject.timeout_add (100, self.__probe_media)
			self.__media_prober = None
			#self.__media_cache = {'type': None, 'size': None}
		
		self.drive = self.serpentine.preferences.drive

		
	
	serpentine = property (lambda self: self.__serpentine)
	
	def __get_media_size (self, vol):
		if self.drive is None:
			return None
			
		if mediaprober is not None:
			if vol is None:
				return None
			print "Is blank:", vol.GetProperty ("volume.disc.is_blank")
			print "Is RW:", vol.GetProperty ("volume.disc.is_rewritable")
			if vol.GetProperty ("volume.disc.is_blank") or    \
			   vol.GetProperty ("volume.disc.is_rewritable"):
				return None
				
			del vol
			return None
			
		media_type = self.drive.get_media_type ()
			
		if media_type not in [nautilusburn.MEDIA_TYPE_CDR,
		                      nautilusburn.MEDIA_TYPE_CDRW]:
			return None
		
		size_in_bytes = self.drive.get_media_size ()
		size_in_secs = nautilusburn.bytes_to_seconds (size_in_bytes)
		disc_sizes = self.serpentine.window_widget.music_list_widget.disc_sizes
		if size_in_secs not in disc_sizes:
			return None
		return size_in_secs
		
	# Updates media widget according to the contained media in the selected
	# drive.
	def __on_media_changed (self, block_manager, vol):
		widget = self.serpentine.window_widget.music_list_widget.disc_size_widget
		media_size = self.__get_media_size (vol)
		
		if media_size is not None:
			widget.set_sensitive (False)
			self.serpentine.window_widget.music_list_widget.disc_size = media_size
		else:
			widget.set_sensitive (True)
	
	# Drive property
	def __set_drive (self, drive):
		# Unregister old drive
		if self.__drive is not None and mediaprober is not None:
			self.__media_prober.unregister_block_device (self.__drive.get_device ())
		
		self.__drive = drive
		
		# Define new drive
		if drive is not None:
			if mediaprober is not None:
				self.__media_prober.register_block_device (drive.get_device (), self.__on_media_changed)
			# Update media status
			dev = drive.get_device ()
			if mediaprober is None:
				vol = None
			else:
				
				vol = self.__media_prober.get_volume_from_block_device (dev)
			self.__on_media_changed (self.__media_prober, vol)
				
	drive = property (lambda self: self.__drive, __set_drive)
	
	# When drive is updated
	def __on_drive_changed (self, event, drive):
		self.drive = drive
		
	def __probe_media (self):
		self.__on_media_changed (None, None)
		return True

def create_plugin (serpentine_object):
	return SerpentineMediaLookup (serpentine_object)
