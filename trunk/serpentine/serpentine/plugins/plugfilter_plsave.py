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

# PLS and M3U specs: http://www.scvi.net/pls.htm

from serpentine import operations, xspf
from serpentine.common import SafeFileWrite
from xml.dom import minidom
import traceback

class SavePlaylist (operations.Operation):
    def __init__ (self, music_list, filename):
        super (SavePlaylist, self).__init__ ()
        
        self.music_list = music_list
        self.filename = filename

    def start (self):
        status = operations.SUCCESSFUL
        fp = SafeFileWrite (self.filename)
        try:
            self._save (fp)
            fp.close ()
            
        except:
            traceback.print_exc()
            status = operations.ERROR
            # Abort changes
            fp.abort ()
            
        
        self._send_finished_event (status)
    
    def _save (fp):
        raise NotImplementedError

class SavePLS (SavePlaylist):
    def _save (self, fp):
        fp.write ("[playlist]\n")
        counter = 0
        for row in self.music_list:
            counter += 1
            fp.write ("File%d=%s\n" % (counter, row["location"]))
            if row.has_key("title"):
                fp.write ("Title%d=%s\n" % (counter, row["title"]))
                
            fp.write ("Length%d=%d\n" % (counter, row.get ("duration", -1)))
        
        fp.write ("NumberOfEntries=%d\n" % counter)
        fp.write ("Version=2\n")

class SaveM3U (SavePlaylist):
    music_list = None
    filename = None
    
    def _save (self, fp):
        fp.write ("#EXTM3U\n")
        
        for row in self.music_list:
            fp.write (
                "#EXTINF:%d,%s\n" % (
                    row.get("duration", -1),
                    row.get("title", "")
                )
            )
            fp.write ("%s\n" % row["location"])

class SaveXSPF (SavePlaylist):
    def _save (self, fp):
        p = xspf.Playlist ()
        self.music_list.to_playlist (p)
        
        p = xspf.Playlist (creator="Serpentine")
        self.music_list.to_playlist (p)
        doc = p.toxml()
        doc.writexml (fp, addindent = "\t", newl = "\n")
        del p

def create_plugin (app):
    # Register factories
    app.savePlaylist.register (factory=SaveM3U,  extension = ".m3u",  description = "MP3 Playlist File")
    app.savePlaylist.register (factory=SavePLS,  extension = ".pls",  description = "PLS Audio Playlist")
    app.savePlaylist.register (factory=SaveXSPF, extension = ".xspf", description = "XML Shareable Playlist Format")