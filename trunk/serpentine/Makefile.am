# Source files
serpentinedir = $(pythondir)/serpentine
serpentine_PYTHON = \
	serpentine/audio.py        \
	serpentine/gaw.py          \
	serpentine/__init__.py     \
	serpentine/preferences.py  \
	serpentine/converting.py   \
	serpentine/mastering.py    \
	serpentine/recording.py    \
	serpentine/export.py       \
	serpentine/gtkutil.py      \
	serpentine/operations.py   \
	serpentine/xspf.py         \
	serpentine/services.py     \
	serpentine/constants.py    \
	serpentine/mediaprober.py  \
	serpentine/release.py

serpentine_pluginsdir = $(pythondir)/serpentine/plugins

serpentine_plugins_PYTHON = \
	serpentine/plugins/plugmediasize.py       \
	serpentine/plugins/plugfilter_plparser.py \
	serpentine/plugins/plugfilter_xspf.py     \
	serpentine/plugins/plugfilter_dir.py      \
	serpentine/plugins/__init__.py

# Launcher
desktopdir = $(datadir)/applications
desktop_DATA = data/serpentine.desktop
#desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
#INTLTOOL_DESKTOP_RULE

# Glade files
uidir= $(datadir)/serpentine
ui_DATA = data/serpentine.glade

# Executable
bin_SCRIPTS = scripts/serpentine

#DISTCLEANFILES =           \
#	intltool-extract    \
#	intltool-merge      \
#	intltool-update     \
#	$(desktop_DATA)

# Files to be packaged
EXTRA_DIST =                \
	$(ui_DATA)          \
	$(bin_SCRIPTS)      \
	$(desktop_DATA)     

#SUBDIRS = po
