# LGPL License
#
# Copyright(C) 2005 Tiago Cogumbreiro <cogumbreiro@users.sf.net>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or(at your option) any later version.
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

from os import path
from urlparse import urlparse, urlunparse

class _PropertyGen(object):
    """This is a simple descriptor that uses 'data' array to retrieve its data"""
    def __init__(self, index):
        self.index = index
    
    def __get__(self, obj, type = None):
        return obj.data[self.index]
    
    def __set__(self, obj, value):
        obj.data[self.index] = value
    

class UrlParse(object):
    """UrlParse objects represent a wrapper above urlparse.urlparse with some
    improvements:
       - access the parsed fields as the object field, instead of indexes of
          a tuple
          
       - filename path are converted to the appropriate URL path, with "file"
          scheme. A filename path is one with no associated "scheme" and it is
          unquoted.
       - allows field alterations(after calling the `make_writable` method)
       
       - 'path' field is unquoted, whereas the 'quoted_path' is the real one.
    """
    
    data = None
    
    def __init__(self, data, basepath=None):
        if data is not None:
            self.parse(data, basepath)
    
    def parse(self, data, basepath=None):
        data = data.encode("utf-8")
        self.data = urlparse(data)
        # if the scheme is empty then we're locating a local file
        if self.scheme == "":
            # quoted path is actually not quoted
            self.make_writable()
            if basepath is None:
                unqpath = path.abspath(self.quoted_path)
            else:
                unqpath = path.join(basepath, self.quoted_path)
                
            self.quoted_path = urllib.quote(unqpath)
            self.scheme = "file"
    
    scheme      = _PropertyGen(0)
    netloc      = _PropertyGen(1)
    quoted_path = _PropertyGen(2)
    params      = _PropertyGen(3)
    query       = _PropertyGen(4)
    fragment    = _PropertyGen(5)
    
    is_local = property(lambda self: self.scheme == "file")
    is_writable = property(lambda self: isinstance(self.data, list))
    
    def get_path(self):
        return urllib.unquote(self.quoted_path)
    
    def set_path(self, value):
        self.quoted_path = urllib.quote(value)

    path = property(get_path, set_path)
    
    # Methods
    
    unparse = lambda self: urlunparse(self.data)
    
    def make_writable(self):
        self.data = list(self.data)
    
    
def get_path(uri_or_path, basepath=None):
    """Returns a path from a path or from a URI"""
    return UrlParse(uri_or_path, basepath).path

def normalize(uri_or_path, basepath=None):
    """Converts a path or a URI to a URI"""
    return UrlParse(uri_or_path, basepath).unparse()

def is_local(uri_or_path, basepath=None):
    """Checks if a path(paths are always local) or a URI is local(when it
    contains the file scheme)"""
    return UrlParse(uri_or_path, basepath).is_local

def basename(uri_or_path, basepath=None):
    return path.basename(UrlParse(uri_or_path, basepath).path)
    
