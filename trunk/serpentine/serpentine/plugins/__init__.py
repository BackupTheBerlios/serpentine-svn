from os import path
from glob import glob
import imp

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
		if hasattr (module, "create_plugin") and hasattr (module.create_plugin, "__call__"):
			tmp_plugins[plug] = module
	except Exception, e:
		print "Error loading plugin:", plug
		print e

plugins = tmp_plugins
del tmp_plugins, imp, plugins_filename, plugins_dir, plug, path, glob, filename
