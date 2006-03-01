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

from os import path
from glob import glob
import imp, sys, traceback

plugins_dir = path.abspath (path.dirname (__file__))
plugins = glob (path.join (plugins_dir, "plug*.py"))
plugins_filename = plugins

plugins = {}
for filename in plugins_filename:
	# Get file basename and remove the .py extension
	plugins[path.basename (filename)[:-3]] = filename

# Now load the modules
tmp_plugins = {}
for plug in plugins:
	
	try:
		module = imp.load_source (plug, plugins[plug])
		
		# Make sure it has a create_plugin method
		if hasattr (module, "create_plugin") and callable (module.create_plugin):
			tmp_plugins[plug] = module
	except Exception, e:
		print >> sys.stderr, "Error loading '%s' plugin:" % plug[4:]
		traceback.print_exc (file = sys.stderr)

plugins = tmp_plugins
del tmp_plugins, imp, plugins_filename, plugins_dir, plug, path, glob, filename
