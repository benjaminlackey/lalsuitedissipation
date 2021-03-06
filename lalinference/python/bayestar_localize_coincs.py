#
# Copyright (C) 2013  Leo Singer
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
"""
Produce GW sky maps for all coincidences in a LIGO-LW XML file.

The filename of the (optionally gzip-compressed) LIGO-LW XML input is an
optional argument; if omitted, input is read from stdin.

The distance prior is controlled by the --prior-distance-power argument.
If you set --prior-distance-power=k, then the distance prior is
proportional to r^k. The default is 2, uniform in volume.

If the --min-distance argument is omitted, it defaults to zero. If the
--max-distance argument is omitted, it defaults to the SNR=4 horizon
distance of the most sensitive detector.

A FITS file is created for each sky map, having a filename of the form

  "X.toa_phoa_snr.fits.gz"
  "X.toa_snr_mcmc.fits.gz"
  "X.toa_phoa_snr_mcmc.fits.gz"

where X is the LIGO-LW row id of the coinc and "toa" or "toa_phoa_snr"
identifies whether the sky map accounts for times of arrival (TOA),
PHases on arrival (PHOA), and amplitudes on arrival (SNR).
"""
__author__ = "Leo Singer <leo.singer@ligo.org>"


# Command line interface.
from optparse import Option, OptionParser
from lalinference.bayestar import command

methods = '''
    toa_phoa_snr
    toa_snr_mcmc
    toa_phoa_snr_mcmc
    toa_snr_mcmc_kde
    toa_phoa_snr_mcmc_kde
    '''.split()
default_method = "toa_phoa_snr"
parser = OptionParser(
    formatter = command.NewlinePreservingHelpFormatter(),
    description = __doc__,
    usage = '%prog [options] [INPUT.xml[.gz]]',
    option_list = [
        Option("--nside", "-n", type=int, default=-1,
            help="HEALPix lateral resolution [default: auto]"),
        Option("--f-low", type=float, metavar="Hz",
            help="Low frequency cutoff [required]"),
        Option("--waveform",
            help="Waveform to use for determining parameter estimation accuracy from signal model [required]"),
        Option("--min-distance", type=float, metavar="Mpc",
            help="Minimum distance of prior in megaparsec [default: infer from effective distance]"),
        Option("--max-distance", type=float, metavar="Mpc",
            help="Maximum distance of prior in megaparsecs [default: infer from effective distance]"),
        Option("--prior-distance-power", type=int, metavar="-1|2",
            help="Distance prior [-1 for uniform in log, 2 for uniform in volume, default: 2]"),
        Option("--method", choices=methods, metavar='|'.join(methods), default=[], action="append",
            help="Sky localization method [may be specified multiple times, default: "
            + default_method + "]"),
        Option("--chain-dump", default=False, action="store_true",
            help="For MCMC methods, dump the sample chain to disk [default: no]"),
        Option("--keep-going", "-k", default=False, action="store_true",
            help="Keep processing events if a sky map fails to converge [default: no].")
    ]
)
opts, args = parser.parse_args()
infilename = command.get_input_filename(parser, args)
command.check_required_arguments(parser, opts, "f_low", "waveform")

if not opts.method:
    opts.method.append(default_method)


#
# Logging
#

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('BAYESTAR')

# LIGO-LW XML imports.
import lal.series
from glue.ligolw import utils as ligolw_utils

# BAYESTAR imports.
from lalinference.bayestar.decorator import memoized
from lalinference import fits
from lalinference.bayestar import ligolw as ligolw_bayestar
from lalinference.bayestar import filter
from lalinference.bayestar import timing
from lalinference.bayestar import ligolw_sky_map

# Other imports.
import healpy as hp
import numpy as np

# Read coinc file.
log.info('%s:reading input XML file', infilename)
xmldoc = ligolw_utils.load_filename(
    infilename, contenthandler=ligolw_bayestar.LSCTablesContentHandler)

reference_psd_filenames_by_process_id = ligolw_bayestar.psd_filenames_by_process_id_for_xmldoc(xmldoc)

@memoized
def reference_psds_for_filename(filename):
    xmldoc = ligolw_utils.load_filename(
        filename, contenthandler=lal.series.PSDContentHandler)
    psds = lal.series.read_psd_xmldoc(xmldoc)
    return dict(
        (key, timing.InterpolatedPSD(filter.abscissa(psd), psd.data.data))
        for key, psd in psds.iteritems() if psd is not None)

def reference_psd_for_ifo_and_filename(ifo, filename):
    return reference_psds_for_filename(filename)[ifo]

f_low = opts.f_low
approximant, amplitude_order, phase_order = timing.get_approximant_and_orders_from_string(opts.waveform)

count_sky_maps_failed = 0

# Loop over all coinc_event <-> sim_inspiral coincs.
for coinc, sngl_inspirals in ligolw_bayestar.coinc_and_sngl_inspirals_for_xmldoc(xmldoc):

    instruments = set(sngl_inspiral.ifo for sngl_inspiral in sngl_inspirals)

    # Look up PSDs
    log.info('%s:reading PSDs', coinc.coinc_event_id)
    psds = tuple(
        reference_psd_for_ifo_and_filename(sngl_inspiral.ifo,
        reference_psd_filenames_by_process_id[sngl_inspiral.process_id])
        for sngl_inspiral in sngl_inspirals)

    # Loop over sky localization methods
    for method in opts.method:
        log.info("%s:method '%s':computing sky map", coinc.coinc_event_id, method)
        if opts.chain_dump:
            chain_dump = '%s.chain.npy' % int(coinc.coinc_event_id)
        else:
            chain_dump = None
        try:
            sky_map, epoch, elapsed_time = ligolw_sky_map.ligolw_sky_map(
                sngl_inspirals, approximant, amplitude_order, phase_order, f_low,
                opts.min_distance, opts.max_distance, opts.prior_distance_power,
                psds=psds, method=method, nside=opts.nside, chain_dump=chain_dump)
        except (ArithmeticError, ValueError):
            log.exception("%s:method '%s':sky localization failed", coinc.coinc_event_id, method)
            count_sky_maps_failed += 1
            if not opts.keep_going:
                raise
        else:
            log.info("%s:method '%s':saving sky map", coinc.coinc_event_id, method)
            fits.write_sky_map('%s.%s.fits.gz' % (int(coinc.coinc_event_id), method),
                sky_map, objid=str(coinc.coinc_event_id), gps_time=float(epoch),
                creator=parser.get_prog_name(), runtime=elapsed_time,
                instruments=instruments, nest=True)


if count_sky_maps_failed > 0:
    raise RuntimeError("{0} sky map{1} did not converge".format(
        count_sky_maps_failed, 's' if count_sky_maps_failed > 1 else ''))
