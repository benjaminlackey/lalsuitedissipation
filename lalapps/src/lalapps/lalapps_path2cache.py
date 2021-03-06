#
# Copyright (C) 2006  Kipp Cannon
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


#
# =============================================================================
#
#                                   Preamble
#
# =============================================================================
#


import os.path
import re
import sys
from optparse import OptionParser


from glue import lal
from glue import segments
#from lalapps import git_version


__author__ = "Kipp Cannon <kipp.cannon@ligo.org>"
#__version__ = "git id %s" % git_version.id
#__date__ = git_version.date


#
# =============================================================================
#
#                                 Command Line
#
# =============================================================================
#


def parse_command_line():
	parser = OptionParser(
		#version = "Name: %%prog\n%s" % git_version.verbose_msg,
		usage = "usage: %prog [options]\n\nExample:\n\tls *.xml | %prog"
	)
	parser.add_option("-a", "--include-all", action = "store_true", help = "Include all files in output.  Unparseable file names are assigned empty metadata.")
	parser.add_option("-f", "--force", action = "store_true", help = "Ignore errors.  Unparseable file names are removed from the output.  This has no effect if --include-all is given.")
	parser.add_option("-i", "--input", metavar="filename", help="Read input from this file (default = stdin).")
	parser.add_option("-o", "--output", metavar="filename", help="Write output to this file (default = stdout).")
	parser.add_option("-v", "--verbose", action="store_true", help="Be verbose.")
	return parser.parse_args()[0]


#
# =============================================================================
#
#                                     Main
#
# =============================================================================
#


#
# Parse command line
#


options = parse_command_line()


#
# Open input and output streams
#


if options.input is not None:
	input = open(options.input)
else:
	input = sys.stdin

if options.output is not None:
	output = open(options.output, "w")
else:
	output = sys.stdout

#
# Other initializations
#


path_count = 0
seglists = segments.segmentlistdict()


#
# Filter input one line at a time
#


for line in input:
	path, file = os.path.split(line.strip())
	url = "file://localhost%s" % os.path.abspath(os.path.join(path, file))
	try:
		cache_entry = lal.CacheEntry.from_T050017(url)
	except ValueError, e:
		if options.include_all:
			cache_entry = lal.CacheEntry(None, None, None, url)
		elif options.force:
			continue
		else:
			raise e
	print >>output, str(cache_entry)
	path_count += 1
	if cache_entry.segment is not None:
		seglists |= cache_entry.segmentlistdict.coalesce()


if options.verbose:
	print >>sys.stderr, "Size of cache: %d URLs" % path_count
	for instrument, seglist in seglists.items():
		print >>sys.stderr, "Interval spanned by %s: [%s s ... %s s) (%s s total)" % (instrument, str(seglist[0][0]), str(seglist[-1][1]), str(abs(seglist)))
	span = seglists.union(seglists)
	print >>sys.stderr, "Interval spanned by union: [%s s ... %s s) (%s s total)" % (str(span[0][0]), str(span[-1][1]), str(abs(span)))
