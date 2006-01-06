AC_PREREQ(2.53)
AC_INIT(serpentine, 0.6.5-testing, http://bugzilla.gnome.org/enter_bug.cgi?product=serpentine)
AC_CONFIG_SRCDIR(scripts/serpentine)
AM_INIT_AUTOMAKE([1.7])

AM_MAINTAINER_MODE

dnl put the ACLOCAL flags in the makefile
ACLOCAL="$ACLOCAL $ACLOCAL_FLAGS"
m4_define(required_pygtk_version, 2.6.0)

dnl check for python
AM_PATH_PYTHON(2.3)

dnl Translation
ALL_LINGUAS="de es fi fr hu nl pt_BR pt ru"
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

dnl Enable/Disable muine installation
AC_ARG_ENABLE(muine,
[  --enable-muine Build the Muine plguin],
[case "${enableval}" in
  yes) muine=true ;;
  no)  muine=false ;;
  *) AC_MSG_ERROR(bad value ${enableval} for --enable-muine) ;;
esac],[debug=false])
AM_CONDITIONAL(MUINE, test x$muine = xtrue)

dnl When we want to compile muine we need to make sure mono exists
if test x"$muine" = xtrue; then
    PKG_CHECK_MODULES(MUINE_PLUGIN, muine-plugin)
    
    dnl pkg-config
    AC_PATH_PROG(PKG_CONFIG, pkg-config, no)
    if test "x$PKG_CONFIG" = "xno"; then
            AC_MSG_ERROR([You need to install pkg-config])
    fi
    
    dnl C# compiler
    AC_PATH_PROG(CSC, csc, no)
    AC_PATH_PROG(MCS, mcs, no)
    AC_PATH_PROG(MONO, mono, no)

    CS="C#"
    if test "x$CSC" = "xno" -a "x$MCS" = "xno"  ; then
            dnl AC_MSG_ERROR([You need to install a C# compiler])
            AC_MSG_ERROR([No $CS compiler found])
    fi

    if test "x$MCS" = "xno" ; then
            MCS=$CSC
    fi

    if test "x$MONO" = "xno"; then
            AC_MSG_ERROR([No mono runtime found])
    fi
    AC_SUBST(MCS)
fi

AC_CONFIG_FILES([
Makefile
muine-plugin/Makefile
serpentine/release.py
po/Makefile.in
])

AC_OUTPUT
