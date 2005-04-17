# Copyright (C) 2004 Tiago Cogumbreiro <cogumbreiro@users.sf.net>
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

def to_cue (music_list, output):
	track = 1
	for music in music_list:
		output.write ("FILE \"%s\" WAVE\r\n" % (music['filename']))
		output.write ("\tTRACK %2d AUDIO\r\n" % (track))
		if music.has_key ('title'):
			output.write ("\t\tTITLE \"%s\"\r\n" % (music['title']))
		if music.has_key ('artist'):
			output.write ("\t\tPERFORMER \"%s\"\r\n" % (music['artist']))
		output.write ("\t\tINDEX 01 00:00:00\r\n")
		track += 1
