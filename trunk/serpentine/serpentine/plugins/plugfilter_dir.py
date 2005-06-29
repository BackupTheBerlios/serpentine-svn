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
import gnomevfs, urllib, os.path
from urlparse import urlparse
from glob import glob
from serpentine.mastering import HintsFilter

class DirectoryFilter (HintsFilter):
	def filter_location (self, location):

		try:
			mime = gnomevfs.get_mime_type (location)
		except RuntimeError:
			return None
			
		if mime != "x-directory/normal":
			return None
			
		s = urlparse (location)
		scheme = s[0]
		# TODO: handle more urls
		if scheme == "file":
			location = urllib.unquote (s[2])
		elif scheme == "":
			location = s[2]
		else:
			return None
		hints_list = []
		for location in glob (os.path.join (location, "*")):
			hints_list.append ({"location": location})
		return hints_list


def create_plugin (app):
	app.add_hints_filter (DirectoryFilter ())
