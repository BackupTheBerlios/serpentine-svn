"""Uses totem.plparser to try and load playlists."""

import gnomevfs
from totem import plparser

from serpentine.mastering import HintsFilter

class PlparserFilter (HintsFilter):
	def __init__ (self):
		self.priority = 10
		
	def __on_pl_entry (self, parser, uri, title, genre, hints_list):
		hints = {'location': uri}
		if title is not None:
			hints['title'] = title
		hints_list.append(hints)

	def filter_location (self, location):
		try:
			mime = gnomevfs.get_mime_type (location)
		except RuntimeError:
			return None
			
		if mime == "audio/x-mpegurl" or mime == "audio/x-scpls":
			hints_list = []
			p = plparser.Parser()
			p.connect("entry", self.__on_pl_entry, hints_list)
			p.parse(location, False)
			print hints_list
			return hints_list
			
		return None
	
def create_plugin (serpentine_object):
	serpentine_object.register_playlist_file_pattern ("PLS Audio Playlist", "*.pls")
	serpentine_object.register_music_file_pattern ("PLS Audio Playlist", "*.pls")
	
	serpentine_object.register_playlist_file_pattern ("MP3 Playlist File", "*.m3u")
	serpentine_object.register_music_file_pattern ("MP3 Playlist File", "*.m3u")
	
	serpentine_object.add_hints_filter (PlparserFilter ())
	
