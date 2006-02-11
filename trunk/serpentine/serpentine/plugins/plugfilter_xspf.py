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

"""Loads XSPF filters."""
from os import path

from serpentine import urlutil
from serpentine.mastering import HintsFilter
from serpentine import xspf

class XspfFilter(HintsFilter):
    def filter_location (self, location):
        url = urlutil.UrlParse(location)
        
        if not url.is_local:
            return

        hints_list = []
        p = xspf.Playlist()
        try:
            p.parse (url.path)
        except Exception:
            return
            
        basename = path.basename(url.path)
        
        for t in p.tracks:
            if t.location is None:
                continue
            r = {'location': urlutil.normalize(t.location, basename)}
            if t.title is not None:
                r['title'] = t.title
            if t.creator is not None:
                r['artist'] = t.creator
            hints_list.append(r)
            
        return hints_list

def create_plugin(serpentine_object):
    serpentine_object.register_playlist_file_pattern(
        "XML Shareable Playlist Format",
        "*.xspf"
    )
    serpentine_object.register_music_file_pattern(
        "XML Shareable Playlist Format",
        "*.xspf"
    )
    serpentine_object.add_hints_filter(XspfFilter())
