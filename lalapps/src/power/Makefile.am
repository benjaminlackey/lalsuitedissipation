BUILT_SOURCES =
MOSTLYCLEANFILES =
EXTRA_DIST =
include $(top_srcdir)/gnuscripts/lalsuite_python.am
include $(top_srcdir)/gnuscripts/lalapps.am

if LALFRAME
if LALMETAIO
if LALBURST
BURSTPROGS = lalapps_binj
lalapps_binj_SOURCES = binj.c
if LALINSPIRAL
INSPPROGS = lalapps_power
lalapps_power_SOURCES = power.c
endif
endif
endif
endif

bin_PROGRAMS = $(BURSTPROGS) $(INSPPROGS)

noinst_PROGRAMS = sense_compare
sense_compare_SOURCES = sense_compare.c

if HAVE_PYTHON
pybin_scripts = lalapps_power_pipe lalapps_power_online_pipe lalapps_power_likelihood_pipe
pkgpython_PYTHON = power.py
endif

pkgdata_DATA = power_pipe.ini power_online_pipe.ini

EXTRA_DIST += power_pipe.ini power_online_pipe.ini
