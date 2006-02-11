# Copyright (C) 2005 Tiago Cogumbreiro <cogumbreiro@users.sf.net>
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

import os
import statvfs
import sys
import tempfile

from gettext import gettext as _
from os import path


class ApplicationLocations:
    def __init__(self, root, appname):
        self.root = path.abspath(root)
        pyver = "python%d.%d" % sys.version_info[0:2]
        self.lib = path.join(root, "lib", pyver, "site-packages")
        self.data = path.join(root, "share", appname)
        self.bin = path.join(root, "bin")
        self.locale = path.join(root, "share", "locale")

    def get_data_file(self, filename):
        return path.join(self.data, filename)
    
    def get_lib_file(self, filename):
        return path.join(self.lib, filename)

    def get_bin_file(self, filename):
        return path.join(self.bin, filename)

    def get_locale_file(self, filename):
        return path.join(self.locale, filename)

    def get_root_file(self, filename):
        return path.join(self.root, filename)



class SerpentineError (StandardError): pass

class SerpentineCacheError (SerpentineError):
    INVALID = 1
    NO_SPACE = 2
    def __init__ (self, error_id, error_message):
        self.__error_id = error_id
        self.__error_message = error_message
    
    error_id = property (lambda self: self.__error_id)
    error_message = property (lambda self: self.__error_message)
    
    def __str__ (self):
        return "[Error %d] %s" % (self.error_id, self.error_message)

class SerpentineNotSupportedError (SerpentineError): pass

def __hig_bytes (bytes):
    hig_desc = [(_("GByte"), _("GBytes")),
                (_("MByte"), _("MBytes")),
                (_("KByte"), _("KByte") ),
                (_("byte") , _("bytes") )]
    value, strings = __decompose_bytes (bytes, 30, hig_desc)
    return "%.1f %s" % (value, __plural (value, strings))

def __decompose_bytes (bytes, offset, hig_desc):
    if bytes == 0:
        return (0.0, hig_desc[-1:])
    if offset == 0:
        return (float (bytes), hig_desc[-1:])
        
    part = bytes >> offset
    if part > 0:
        sub_part = part ^ ((part >> offset) << offset)
        return ((part * 1024 + sub_part) / 1024.0, hig_desc[0])
    else:
        del hig_desc[0]
        return __decompose_bytes (bytes, offset - 10, hig_desc)

def __plural (value, strings):
    if value == 1:
        return strings[0]
    else:
        return strings[1]


class SafeFileWrite:
    """This class enables the user to safely write the contents to a file and
    if something wrong happens the original file will not be damaged. It writes
    the contents in a temporary file and when the file descriptor is closed the
    contents are transfered to the real filename."""
    
    def __init__ (self, filename):
        self.filename = filename
        basedir = path.dirname (filename)
        # must be in the same directory so that renaming works
        fd, self.tmp_filename = tempfile.mkstemp (dir = basedir)
        os.close (fd)
        self.fd = open (self.tmp_filename, "w")
        
    def __getattr__ (self, attr):
        return getattr (self.fd, attr)
    
    def close (self):
        self.fd.close ()
        
        try:
            os.unlink (self.filename)
        except:
            pass
        os.rename (self.tmp_filename, self.filename)
    
    def abort (self):
        """Abort is used to cancel the changes made and remove the temporary
        file. The original filename will not be altered."""
        self.fd.close ()
        try:
            os.unlink (self.tmp_filename)
        except:
            pass

def validate_music_list (music_list, preferences):
    # Check if we have space available in our cache dir
    secs = 0
    for music in music_list:
        # When music is not available it will have to be converted
        if not preferences.pool.is_available (music["location"]):
            secs += music["duration"]
    # 44100hz * 16bit * 2channels / 8bits = 176400 bytes per sec
    size_needed = secs * 176400L
    
    # Now check if cache location is ok
    try:
        s = os.statvfs (preferences.temporaryDir)
        # Raise exception if temporary dir is not ok
        assert preferences.temporaryDirIsOk
    except OSError, AssertionError:
        raise SerpentineCacheError (SerpentineCacheError.INVALID, _("Please "
                                    "check if the cache location exists and "
                                    "has writable permissions."))
    
    size_avail = s[statvfs.F_BAVAIL] * long(s[statvfs.F_BSIZE])
    if (size_avail - size_needed) < 0:
        preferences.pool.clear ()
    
    size_avail = s[statvfs.F_BAVAIL] * long(s[statvfs.F_BSIZE])
    if (size_avail - size_needed) < 0:
        raise SerpentineCacheError (SerpentineCacheError.NO_SPACE, _("Remove " 
                                    "some music tracks or make sure your "     
                                    "cache location location has enough free " 
                                    "space (about %s).")
                                    % __hig_bytes(size_needed - size_avail))
