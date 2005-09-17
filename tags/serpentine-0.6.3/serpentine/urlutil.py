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

import urllib

from urlparse import urlparse, urlunparse

__all__ = ("UrlParsed", "get_path", "to_uri")

class PropertyGen (object):
    def __init__ (self, index):
        self.index = index
    
    def __get__ (self, obj, type = None):
        return obj.data[self.index]
    
    def __set__ (self, obj, value):
        obj.data[self.index] = value
    

class UrlParse (object):
    """UrlParse objects represent a wrapper above urlparse.urlparse with some
    improvements:
       - access the parsed fields as the object field, instead of indexes of
          a tuple
          
       - filename path are converted to the appropriate URL path, with "file"
          scheme. A filename path is one with no associated "scheme" and it is
          unquoted.
       - allows field alterations (after calling the `make_writable` method)
       
       - 'path' field is unquoted, whereas the 'quoted_path' is the real one.
    """
    
    data = None
    
    def __init__ (self, data):
        if data is not None:
            self.parse (data)
    
    def parse (self, data):
        self.data = urlparse (data)
        # We a
        if self.scheme == "":
            # quoted path is actually not quoted
            self.make_writable ()
            self.quoted_path = urllib.quote (self.quoted_path)
            self.scheme = "file"
    
    scheme      = PropertyGen (0)
    netloc      = PropertyGen (1)
    quoted_path = PropertyGen (2)
    params      = PropertyGen (3)
    query       = PropertyGen (4)
    fragment    = PropertyGen (5)
    
    is_local = property (lambda self: self.scheme == "file" or self.scheme == "")
    is_writable = property (lambda self: isinstance (self.data, list))
    
    def get_path (self):
        return urllib.unquote(self.quoted_path)
    
    def set_path (self, value):
        self.quoted_path = urllib.quote (value)

    path = property (get_path, set_path)
    
    # Methods
    
    unparse = lambda self: urlunparse (self.data)
    
    def make_writable (self):
        self.data = list (self.data)
    
    
def get_path (uri_or_path):
    """Returns a path from a path or from a URI"""
    
    s = UrlParse (uri_or_path)
    path = s.path
    
    if s.scheme != "":
        # Remove %20, which is only present when there is a scheme (it is a URI)
        path = urllib.unquote (path)
    
    return path

def normalize (uri_or_path):
    """Converts a path or a URI to a URI"""
    return UrlParse (uri_or_path).unparse ()

def is_local (uri_or_path):
    """Checks if a path (paths are always local) or a URI is local (when it
    contains the file scheme)"""
    return UrlParse (uri_or_path).is_local
