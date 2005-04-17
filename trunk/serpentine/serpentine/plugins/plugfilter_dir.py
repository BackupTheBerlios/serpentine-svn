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
		if scheme == 'file':
			location = urllib.unquote (s[2])
		elif scheme == '':
			location = s[2]
		else:
			return None
		hints_list = []
		for location in glob (os.path.join (location, "*")):
			hints_list.append ({"location": location})
		return hints_list


def create_plugin (serpentine_object):
	serpentine_object.add_hints_filter (DirectoryFilter ())
