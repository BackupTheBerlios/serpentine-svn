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

from serpenetine import operations, xspf


class SavePlaylist (operations.Operation):
    def __init__ (self, music_list, filename):
        super (SavePlaylist, self).__init__ ()
        
        self.music_list = music_list
        self.filename = filename

    def start (self):
        status = True
        fp = open (self.filename, "w")
        try:
            self._save (fp)
            
        except:
            status = False
            
        fp.close ()
        
        self._send_finished_event (status)
    
    def _save (fp):
        raise NotImplementedError

class SavePLS (operations.Operation):
    def _save (self, fp):
        fp.write ("[playlist]\n")
        counter = 1
        for row in self.music_list:
            fp.write ("File%d=%s\n" % (counter, row["location"]))
            if row.has_key("title"):
                fp.write ("Title%d=%s\n" % (counter, row["title"]))
                
            fp.write ("Length%d=%d\n" % (counter, row.get ("duration", -1)))
        
        fp.write ("NumberOfEntries=%d\n" % (counter - 1))
        fp.write ("Version=2\n")

class SaveM3U (operations.Operation):
    music_list = None
    filename = None
    
    def _save (self, fp):
        fp.write ("#EXTM3U")
        
        for row in self.music_list:
            fp.write (
                "#EXTINF:%d,%s\n" % (
                    row.get("duration", -1),
                    row.get("title", "")
                )
            )
            fp.write ("%s\n", row["location"])

class SaveXSPF (SavePlaylist):
    def _save (self, fp):
        pls = xspf.Playlist ()
        music_list.to_playlist (p)
        
        p = xspf.Playlist (creator="Serpentine")
        self.music_list.to_playlist (p)
        doc = minidom.parseString (p.toxml())
        doc.writexml (fp, addindent = "\t", newl = "\n")
        del p

def create_plugin (app):
    # Register factories
    app.save_playlist_registry.register (extension = ".m3u", factory=SaveM3U, description = "MP3 Playlist File")
    app.save_playlist_registry.register (extension = ".pls", factory=SavePLS, description = "PLS Audio Playlist")
    app.save_playlist_registry.register (extension = ".xspf", factory=SaveXSPF, description = "XML Shareable Playlist Format")