#
# Copyright (C) 2011  Leo Singer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Overplot contours for a large number of sky maps, in geographical coordinates.
This can reveal patterns due to the priors (i.e., the network antenna pattern).
"""
__author__ = "Leo Singer <leo.singer@ligo.org>"


# Command line interface

from optparse import Option, OptionParser
from lalinference.bayestar import command
parser = OptionParser(
    description = __doc__,
    usage = "%prog [options] INPUT1.fits[.gz] INPUT2.fits[.gz] ...",
    option_list = [
        Option("-o", "--output", metavar="FILE.{pdf,png}",
            help="name of output file [default: plot to screen]"),
        Option("--figure-width", metavar="INCHES", type=float, default=8.,
            help="width of figure in inches [default: %default]"),
        Option("--figure-height", metavar="INCHES", type=float, default=6.,
            help="height of figure in inches [default: %default]"),
        Option("--dpi", metavar="PIXELS", type=int, default=300,
            help="resolution of figure in dots per inch [default: %default]"),
        Option("--contour", metavar="PERCENT", type=float, default=90,
            help="plot contour enclosing this percentage of"
            + " probability mass [default: %default]"),
        Option("--alpha", metavar="ALPHA", type=float, default=0.1,
            help="alpha blending for each sky map [default: %default]")
    ]
)
opts, args = parser.parse_args()

# Late imports

# Choose a matplotlib backend that is suitable for headless
# rendering if output to file is requested
import matplotlib
if opts.output is not None:
    matplotlib.use('agg')

import functools
import numpy as np
import matplotlib.pyplot as plt
import healpy as hp
import lal
from lalinference import fits
from lalinference import plot
from glue.text_progress_bar import ProgressBar


fig = plt.figure(figsize=(opts.figure_width, opts.figure_height), frameon=False)
ax = plt.subplot(111, projection='mollweide')
ax.cla()
ax.grid()

progress = ProgressBar()

progress.update(-1, 'obtaining filenames of sky maps')
fitsfilenames = tuple(command.chainglob(args))

progress.max = len(fitsfilenames)

matplotlib.rc('path', simplify=True, simplify_threshold=1)

for count_records, fitsfilename in enumerate(fitsfilenames):
    progress.update(count_records, fitsfilename)
    skymap, metadata = fits.read_sky_map(fitsfilename, nest=None)
    nside = hp.npix2nside(len(skymap))
    gmst = lal.GreenwichMeanSiderealTime(metadata['gps_time']) % (2*np.pi)

    indices = np.argsort(-skymap)
    region = np.empty(skymap.shape)
    region[indices] = 100 * np.cumsum(skymap[indices])
    plot.healpix_contour(
        region, nest=metadata['nest'], dlon=-gmst, colors='k', linewidths=0.5,
        levels=[opts.contour], alpha=opts.alpha)

progress.update(-1, 'saving figure')

# If we are using a new enough version of matplotlib, then
# add a white outline to all text to make it stand out from the background.
plot.outline_text(ax)

fig.patch.set_alpha(0.)
ax.patch.set_alpha(0.)
ax.set_alpha(0.)

if opts.output is None:
    plt.show()
else:
    plt.savefig(opts.output, dpi=opts.dpi)
