# LGPL License
#
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

"""Loads directory filters."""
from os import path
from glob import glob

from serpentine.mastering import HintsFilter
from serpentine import urlutil

class DirectoryFilter (HintsFilter):
    def filter_location (self, location):
        url = urlutil.UrlParse(location)
        if not url.is_local or not path.isdir(url.path):
            return
            
        files = glob(path.join(location, "*"))
        files.sort()
        
        to_hints = lambda loc: {"location": urlutil.normalize(loc)}
        return map(to_hints, files)


def create_plugin(app):
    app.add_hints_filter(DirectoryFilter())
