SUBDIRS = po

if MUINE
SUBDIRS += muine-plugin
endif

# Source files
EXTRA_DIST =
CLEAN_DIST =
CLEANFILES =

EXTRA_DIST += intltool-extract.in intltool-merge.in intltool-update.in
DISTCLEANFILES = intltool-extract intltool-merge intltool-update


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
	serpentine/gdkpiechart.py  \
	serpentine/components.py   \
	serpentine/mainwindow.py   \
	serpentine/common.py       \
	serpentine/urlutil.py      \
	serpentine/release.py

serpentine_pluginsdir = $(pythondir)/serpentine/plugins

serpentine_plugins_PYTHON = \
	serpentine/plugins/plugfilter_plparser.py \
	serpentine/plugins/plugfilter_xspf.py     \
	serpentine/plugins/plugfilter_dir.py      \
	serpentine/plugins/plugfilter_plsave.py   \
	serpentine/plugins/plugfilter_k3b.py      \
	serpentine/plugins/plugrhythmbox.py       \
	serpentine/plugins/__init__.py

#################################################################
# Launcher
@INTLTOOL_DESKTOP_RULE@

desktopdir = $(datadir)/applications
desktop_in_files = data/serpentine.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
EXTRA_DIST += $(desktop_in_files)
CLEANFILES += $(desktop_DATA)

#################################################################
# Glade files
uidir= $(datadir)/serpentine
ui_DATA = data/serpentine.glade

# Executable
bin_SCRIPTS = scripts/serpentine

#DISTCLEANFILES =       \
#	intltool-extract    \
#	intltool-merge      \
#	intltool-update     \
#	$(desktop_DATA)

# Files to be packaged
EXTRA_DIST +=                  \
	$(ui_DATA)             \
	$(bin_SCRIPTS)         \
        muine-plugin/Makefile  \
        muine-plugin/SerpentinePlugin.cs

#SUBDIRS = po
