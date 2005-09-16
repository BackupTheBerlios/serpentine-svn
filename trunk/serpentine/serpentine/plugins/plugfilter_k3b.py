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

import zipfile, gnomevfs

from xml.dom import minidom
from xml.xpath import Evaluate
from serpentine.mastering import HintsFilter
from serpentine import urlutil
from xml.parsers.expat import ExpatError

import traceback

def safe_method (func):
    def wrapper (self, *args, **kwargs):
        try:
            return func (self, *args, **kwargs)
        except:
            traceback.print_exc ()
    
    return wrapper

class K3BFilter (HintsFilter):
    def filter_location (self, location):
        url = urlutil.UrlParse (location)
        if not url.is_local:
            fd = gnomevfs.open (url.unparse ())
            def read_all ():
                buff = ""
                try:
                    while 1:
                        buff += fd.read (1024)
                except gnomevfs.EOFError:
                    pass
                return buff
            fd.read = read_all
        else:
            fd = open (url.path)

        try:
            zfile = zipfile.ZipFile (fd)
        except zipfile.BadZipfile:
            return
        except IOError:
            # it's not a file
            return
        
        try:
            buff = zfile.read ("maindata.xml")
        except KeyError:
            # zip file does not contain the file
            return
        
        try:
            root = minidom.parseString (buff)
        except ExpatError:
            # Malformed xml
            return
            
        # Iterate over tracks
        hints_list = []
        for node in Evaluate ("/k3b_audio_project/contents/track", root):
            try:
                hints_list.append ({"location": node.attributes["url"].value})
            except KeyError:
                # skip elements with not 'url' attribute set
                pass
        
        return hints_list
    
    filter_location = safe_method (filter_location)

def create_plugin (app):
    app.add_hints_filter (K3BFilter ())
    app.register_playlist_file_pattern ("K3B Audio Project", "*.k3b")
    app.register_music_file_pattern ("K3B Audio Project", "*.k3b")
    