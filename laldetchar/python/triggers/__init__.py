# Copyright (C) 2011 Duncan Macleod
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation,.

"""A collesction of modules for manipulating the output of LIGO-Virgo
event trigger generators (ETGs)
"""

from __future__ import division

import re
import sys

from glue.ligolw import (ligolw, lsctables, utils, table)

from laldetchar import git_version

__author__ = "Duncan Macleod <duncan.macleod@ligo.org>"
__version__ = git_version.id
__date__ = git_version.date

_re_etg_kw = re.compile("\A(kw|kleinewelle)\Z", re.I)
_re_etg_omega = re.compile("\Aomega\Z", re.I)
_re_etg_ep = re.compile("\A(ep|excesspower|gstlal_excesspower)\Z", re.I)
_re_etg_sngl_burst = re.compile("\A(kw|kleinewelle|omega|ep|excesspower|"
                                  "gstlal_excesspower|hacr)\Z", re.I)

_re_etg_cwb = re.compile("(cwb|waveburst)", re.I)
_re_etg_multi_burst = re.compile("(cwb|waveburst)", re.I)

_re_etg_di = re.compile("\Adaily*ihope\Z", re.I)
_re_etg_ihope = re.compile("\Aihope\Z", re.I)
_re_etg_sngl_insp = re.compile("ihope", re.I)

_re_etg_cohptf = re.compile("\Acoh_PTF", re.I)
_re_etg_multi_insp = re.compile("\Acoh_PTF", re.I)

_re_etg_ring = re.compile("ring", re.I)
_re_etg_sngl_ring = re.compile("ring", re.I)


def new_ligolw_table(etg, columns=None):
    """@returns a new glue.ligolw.table relevant for the given event
    trigger generator (etg)
    """

    if _re_etg_sngl_burst.search(etg):
        out = lsctables.New(lsctables.SnglBurstTable, columns=columns)
    elif _re_etg_multi_burst.search(etg):
        out = lsctables.New(lsctables.MultiBurstTable, columns=columns)
    elif _re_etg_sngl_insp.search(etg):
        out = lsctables.New(lsctables.SnglInspiralTable, columns=columns)
    elif _re_etg_multi_insp.search(etg):
        out = lsctables.New(lsctables.MultiInspiralTable, columns=columns)
    elif _re_etg_sngl_ring.search(etg):
        out = lsctables.New(lsctables.SnglRingdownTable, columns=columns)

    if columns is not None:
        if isinstance(columns[0], str):
            columns = map(str.lower, columns)
        if isinstance(columns[0], unicode):
            columns = map(unicode.lower, columns)
        for c in out.columnnames:
            if c.lower() not in columns:
                idx = out.columnnames.index(c)
                out.columnnames.pop(idx)
                out.columntypes.pop(idx)

    return out


def load_table_from_fileobj(fileobj, etg, columns=None, start=None,
                            end=None):
    """@returns a glue.ligolw.table of triggers read from the given
    LIGOLw XML fileobj
    """
    out = new_ligolw_table(etg, columns=columns)
    get_time = _get_time(out.tableName)
    keep = lambda t: ((start and start <= float(get_time(t)) or True) &
                      (end and float(get_time(t)) < end or True))
    xmldoc, digest = utils.load_fileobj(fileobj,
                                        gz=fileobj.name.endswith("gz"))
    out.extend(row for row in table.get_table(xmldoc, out.tableName) if
               keep(row))
    xmldoc.unlink()
    return out


def load_table_from_filenames(filelist, etg, columns=None, verbose=False,
                              load_func=load_table_from_fileobj, **load_args):
    """@returns a glue.ligolw.table containing the triggers from each
    file in the list, in the correct format for the given etg.

    @param filelist
        list of filepaths from which to read the data
    @param etg
        name of event trigger generator that produced LIGO_LW files
    @param columns
        set of valid SnglBurst columns to read from data
    @param verbose
        print verbose progress, default False
    @param load_func
        function to use when loading the events, defaults to
        load_ligolw_from_fileobj

    All other keyword arguments will be passed directory to load_func
    """
    out = new_ligolw_table(etg, columns=columns)
    extend = out.extend
    if verbose:
        N = len(filelist)
        sys.stdout.write("Extracting %s triggers from %d files...     \r"
                         % (etg, N))
        sys.stdout.flush()
    for i,fp in enumerate(filelist):
        with open(fp, "r") as f:
            extend(load_func(f, etg, columns=columns, **load_args))
        if verbose:
            progress = int((i+1)/N*100)
            sys.stdout.write("Extracting %s triggers from %d files... "
                             "%.2d%%\r" % (etg, N, progress))
            sys.stdout.flush()
    if verbose:
        sys.stdout.write("Extracting %s triggers from %d files... "
                         "100%%\n" % (etg, N))
        sys.stdout.flush()
    return out


def load_table_from_lal_cache(cache, etg, columns=None, verbose=False,
                              load_func=load_table_from_fileobj, **load_args):
    """@returns a glue.ligolw.table containing the triggers from each
    file in the cache, in the correct format for the given etg.

    @param filelist
        list of filepaths from which to read the data
    @param etg
        name of event trigger generator that produced LIGO_LW files
    @param columns
        set of valid SnglBurst columns to read from data
    @param verbose
        print verbose progress, default False
    @param load_func
        function to use when loading the events, defaults to
        load_ligolw_from_fileobj

    All other keyword arguments will be passed directory to load_func
    """
    return load_table_from_filenames(cache.pfnlist(), etg, columns=columns,
                                     verbose=verbose, load_func=load_func,
                                     **load_args)


def _get_time(table_name, ifo=None):
    """@returns a function to return the 'time' of an event in any table
    with the given name.

    @param table_name
        name of the relevant LIGO_LW table
    @param ifo
        interferometer prefix if extracting single-detector time
    """
    if re.search("burst", table_name, re.I):
        return lambda row: row.get_peak()
    elif re.search("inspiral", table_name, re.I):
        return lambda row: row.get_end()
    elif re.search("sim*inspiral", table_name, re.I):
        site = ifo and ifo[0] or None
        return lambda row: row.get_end(site)
    elif re.search("ringdown", table_name, re.I):
        return lambda row: row.get_start()
    else:
        raise ValueError("No known time method for table_name=\'%s\'"
                         % table_name)