"""Loads XSPF filters."""
import gnomevfs, urllib, os.path
from urlparse import urlparse

from serpentine.mastering import HintsFilter
from serpentine import xspf

class XspfFilter (HintsFilter):
	def filter_location (self, location):
	
		try:
			mime = gnomevfs.get_mime_type (location)
		except RuntimeError:
			return None
			
		if mime == "text/xml":
			if not os.path.exists (location):
				s = urlparse (location)
				scheme = s[0]
				# TODO: handle more urls
				if scheme == 'file':
					location = urllib.unquote (s[2])
				else:
					return None
			hints_list = []
			p = xspf.Playlist()
			p.parse (location)
			for t in p.tracks:
				if t.location is None:
					continue
				r = {'location': t.location}
				if t.title is not None:
					r['title'] = t.title
				if t.creator is not None:
					r['artist'] = t.creator
				hints_list.append (r)
			return hints_list

		return None

def create_plugin (serpentine_object):
	serpentine_object.add_hints_filter (XspfFilter ())
