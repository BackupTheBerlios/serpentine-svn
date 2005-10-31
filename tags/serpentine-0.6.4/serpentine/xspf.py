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

"""
This is a very simple utility module for retrieving basic XSPF playlist data.
Basically it retrieves the playlist tracks' title, artist, location and duration.
"""
from xml.dom import minidom
from xml.xpath import Evaluate
from xml.dom.minidom import getDOMImplementation

class _Field (object):
	def __init__ (self, id = None, convert = None):
		self.id = id
		self.convert = convert
		
	data = None
		
	def toxml (self, doc, root):
		if self.data is not None:
			node = doc.createElement (self.id)
			node.appendChild (doc.createTextNode (str (self.data)))
			root.appendChild (node)

class _Struct (object):
	_fields = {}
	
	def __init__ (self, **kw):
		for key in kw:
			assert key in self._fields
			self._fields[key].data = kw[key]
			
	def __setattr__ (self, attr, value):
		if attr in self._fields:
			self._fields[attr].data = value
		else:
			self.__dict__[attr] = value
	
	def __getattr__ (self, attr):
		if attr in self._fields:
			return self._fields[attr].data
		else:
			raise AttributeError, "Instance has no attribute '%s'" % (attr)
	
	def toxml (self, doc, root):
		
		for key in self._fields:
			self._fields[key].toxml(doc, root)
	
	def _parse_node (self, node):
		for field in self._fields:
			try:
				avail_fields = Evaluate ("%s"  % (field), node)
				if len(avail_fields) == 0:
					# No fields skip this one
					continue
				# Get the first field
				field_node = avail_fields[0]
				val = Evaluate ("string()", field_node).strip()
				convert = self._fields[field].convert
				if convert:
					val = convert (val)
				self._fields[field].data = val
			except ValueError:
				pass

class Track (_Struct):
	def __init__ (self, **kw):
		self._fields = {"title": _Field("title"),
		                "creator": _Field("creator"),
		                "duration": _Field("duration", int),
		                "location": _Field("location")}
		_Struct.__init__ (self, **kw)
	           
	def toxml (self, doc, root):
		node = doc.createElement ("track")
		root.appendChild (node)
		return _Struct.toxml(self, doc, node)

class Playlist (_Struct):
	def __init__ (self, **kw):
		self._fields = {"title": _Field("title"),
		                "creator": _Field("creator"),
		                "duration": _Field("duration", int),
		                "location": _Field("location")}
		_Struct.__init__ (self, **kw)
		self.tracks = []
	
	def toxml (self):
		"""Returns a xml.dom.Document representing the XSPF playlist"""
		
		DOM = getDOMImplementation ()
		doc = DOM.createDocument (None, "playlist", None)
		root = doc.documentElement
		root.setAttribute ("version", "0")
		
		trackList = doc.createElement ("trackList")
		root.appendChild (trackList)
		
		for t in self.tracks:
			t.toxml (doc, trackList)
		
		return doc

	def parse (self, file_or_filename):
		root = minidom.parse (file_or_filename)
		# Iterate over tracks
		for track_node in Evaluate ("/playlist/trackList/track", root):
			t = Track()
			# Get each field
			#for field in t._fields:
			#	try:
			#		val = Evaluate ("string(%s)" % (field), track_node).strip()
			#		convert = t._fields[field].convert
			#		if convert:
			#			val = convert (val)
			#		setattr (t, field, val)
			#	except ValueError:
			#		pass
			t._parse_node (track_node)
			self.tracks.append(t)

if __name__ == '__main__':
	import sys
	p = Playlist ()
	for arg in sys.argv[1:]:
		print to_xml_string (p.parse_filename (arg))
