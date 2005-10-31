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
            return
            
        if mime == "audio/x-mpegurl" or mime == "audio/x-scpls":
            hints_list = []
            p = plparser.Parser()
            p.connect("entry", self.__on_pl_entry, hints_list)
            p.parse(location, False)

            return hints_list
            
        return
    
def create_plugin (serpentine_object):
    serpentine_object.register_playlist_file_pattern ("PLS Audio Playlist", "*.pls")
    serpentine_object.register_music_file_pattern ("PLS Audio Playlist", "*.pls")
    
    serpentine_object.register_playlist_file_pattern ("MP3 Playlist File", "*.m3u")
    serpentine_object.register_music_file_pattern ("MP3 Playlist File", "*.m3u")
    
    serpentine_object.add_hints_filter (PlparserFilter ())
    
