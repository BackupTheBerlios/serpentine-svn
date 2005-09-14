AC_PREREQ(2.53)
AC_INIT(scripts/serpentine)
AM_INIT_AUTOMAKE([1.7])

dnl AM_INIT_AUTOMAKE(serpentine, 0.6.1)
AC_INIT(serpentine, 0.6.2, http://s1x.homelinux.net/projects/serpentine)
AM_MAINTAINER_MODE



dnl put the ACLOCAL flags in the makefile
ACLOCAL="$ACLOCAL $ACLOCAL_FLAGS"
m4_define(required_pygtk_version, 2.6.0)

dnl check for python
AM_PATH_PYTHON(2.3)

dnl Translation
ALL_LINGUAS="pt"
GETTEXT_PACKAGE=serpentine
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [Gettext package])
AM_GLIB_GNU_GETTEXT
AC_PROG_INTLTOOL

dnl -===- <gconf> -===-
AC_PATH_PROG(GCONFTOOL, gconftool-2, no)
if test x"$GCONFTOOL" = xno; then
  AC_MSG_ERROR([gconftool-2 executable not found in your path - should be installed with GConf])
fi
AM_GCONF_SOURCE_2
dnl -===- </gconf> -===-


AC_CONFIG_FILES([
Makefile
serpentine/release.py
])

AC_OUTPUT
