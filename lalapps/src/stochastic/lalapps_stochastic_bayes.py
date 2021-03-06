"""
stochastic_bayes.in - SGWB Standalone Analysis Pipeline
                    - Bayesian Pipeline DAG Driver Script

Copyright (C) 2004-2006 Adam Mercer

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
"""

__author__ = 'Adam Mercer <ram@star.sr.bham.ac.uk>'
__date__ = '$Date$'
__version__ = '$Revision$'

# import required modules
import sys
import os
import getopt
import re
import string
import tempfile
import ConfigParser

# import the lalapps pipeline modules
from glue import pipeline
import stochastic

# program usage
def usage():
  msg = """\
Usage: lalapps_stochastic_bayes [options]

  -h, --help               display this message
  -v, --version            print version information and exit
  -u, --user-tag TAG       tag the jobs with TAG

  -d, --datafind           run LSCdataFind to create frame cache files
  -s, --stochastic         run lalapps_stochastic

  -P, --priority PRIO      run jobs with condor priority PRIO

  -f, --config-file FILE   use configuration file FILE
  -l, --log-path PATH      directory to write condor log file
  """
  print >> sys.stderr, msg

# parse the command line options to figure out what we should do
shortop = "hvu:dsP:f:l:"
longop = [
  "help",
  "version",
  "user-tag=",
  "datafind",
  "stochastic",
  "priority=",
  "config-file=",
  "log-path="
  ]

try:
  opts, args = getopt.getopt(sys.argv[1:], shortop, longop)
except getopt.GetoptError:
  usage()
  sys.exit(1)

# default options
usertag = None
do_datafind = None
do_stochastic = None
condor_prio = None
config_file = None
log_path = None

# process options
for o, a in opts:
  if o in ("-v", "--version"):
    print "lalapps_stochastic_bayes version", __version__
    print "Built on top of stochastic.py version", stochastic.version()
    sys.exit(0)
  elif o in ("-h", "--help"):
    usage()
    sys.exit(0)
  elif o in ("-u", "--user-tag"):
    usertag = a
  elif o in ("-d", "--datafind"):
    do_datafind = 1
  elif o in ("-s", "--stochastic"):
    do_stochastic = 1
  elif o in ("-P", "--priority"):
    condor_prio = a
  elif o in ("-f", "--config-file"):
    config_file = a
  elif o in ("-l", "--log-path"):
    log_path = a
  else:
    print >> sys.stderr, "Unknown option:", o
    usage()
    sys.exit(1)

if not config_file:
  print >> sys.stderr, "No configuration file specified."
  print >> sys.stderr, "Use --config-file FILE to specify location."
  sys.exit(1)

if not log_path:
  print >> sys.stderr, "No log file path specified."
  print >> sys.stderr, "Use --log-path PATH to specify a location."
  sys.exit(1)

# try and make a directory to store the cache files and job logs
try: os.mkdir('cache')
except: pass
try: os.mkdir('logs')
except: pass

# create the config parser object and read in the ini file
cp = ConfigParser.ConfigParser()
cp.read(config_file)

# create a log file that the Condor jobs will write to
basename = re.sub(r'\.ini',r'',config_file)
tempfile.tempdir = log_path
if usertag:
  tempfile.template = basename + '.' + usertag + '.dag.log'
else:
  tempfile.template = basename + '.dag.log.'
logfile = tempfile.mktemp()
fh = open( logfile, "w" )
fh.close()

# create the DAG writing the log to the specified directory
dag = pipeline.CondorDAG(logfile)
if usertag:
  dag.set_dag_file(basename + '.' + usertag)
else:
  dag.set_dag_file(basename)

# create the Condor jobs that will be used in the DAG
df_job = stochastic.LSCDataFindJob('cache','logs',cp)
stoch_job = stochastic.StochasticJob(cp)

# set file names
if usertag:
  subsuffix = '.' + usertag + '.sub'
else:
  subsuffix = '.sub'
df_job.set_sub_file( basename + '.datafind'+ subsuffix )
stoch_job.set_sub_file( basename + '.stochastic' + subsuffix )

# set the condor job priority
if condor_prio:
  df_job.add_condor_cmd('priority',condor_prio)
  stoch_job.add_condor_cmd('priority',condor_prio)

# get the pad and chunk lengths from the values in the ini file
min_length = int(cp.get('input','min_length'))
max_length = int(cp.get('input','max_length'))

# read science segs that are greater or equal to a chunk from the input file
data = pipeline.ScienceData()
data.read(cp.get('input','segments'),min_length)

# create the chunks from the science segments
data.make_chunks(max_length)
data.make_short_chunks_from_unused(min_length)

# get the ifos
ifo1 = cp.get('detectors','detector-one')
ifo2 = cp.get('detectors','detector-two')

# get the frame types
type1 = cp.get('datafind','type-one')
type2 = cp.get('datafind','type-two')

# get the LSCdataFindServer
server = cp.get('datafind','server')

# get the min/max frequency
f_min = float(cp.get('frequency','f-min'))
f_max = float(cp.get('frequency','f-max'))

# get the band over which to loop
f_band = float(cp.get('frequency','f-band'))

# check that f_band is an integer multiple of f_max - f_min
if ((f_max - f_min)/f_band - int(f_max - f_min)/int(f_band)) != 0:
  sys.exit("f-band must be a mutliple of f_max - f_max")

# get range of minimum frequencies over which to search
min_range = range(0, int((f_max - f_min)/f_band), 1)

# create all the LSCdataFind jobs to run in sequence
prev_df = None

# loop through the analysis data
for seg in data:
  # find the data with LSCdataFind
  df1 = stochastic.LSCDataFindNode(df_job)
  df1.set_start(seg.start())
  df1.set_end(seg.end())
  df1.set_observatory(ifo1[0])
  df1.set_type(type1)
  df1.set_server(server)
  if prev_df:
    df1.add_parent(prev_df)
  prev_df = df1

  # find data with LSCdataFind for different detector
  if ifo1[0] != ifo2[0]:
    df2 = stochastic.LSCDataFindNode(df_job)
    df2.set_start(seg.start())
    df2.set_end(seg.end())
    df2.set_observatory(ifo2[0])
    df2.set_type(type2)
    df2.set_server(server)
    df2.add_parent(prev_df)
    prev_df = df2

  # add LSCdataFind node(s) if required
  if do_datafind:
    dag.add_node(df1)
    if ifo1[0] != ifo2[0]:
      dag.add_node(df2)

  # if same site, only one LSCdataFind job is run
  if ifo1[0] == ifo2[0]:
    df2 = df1

  # set up stochastic job
  for chunk in seg:
    # loop over band
    for i in min_range:
      # get band for analysis
      min = f_min + (i * f_band)
      max = min + f_band
      # try and make a directory to store the xml files
      dir = "%.0f-%.0f" % (min, max)
      try: os.mkdir(dir)
      except: pass
      # set up job
      stoch = stochastic.StochasticNode(stoch_job)
      stoch.set_start(chunk.start())
      stoch.set_end(chunk.end())
      stoch.set_ifo_one(ifo1)
      stoch.set_ifo_two(ifo2)
      stoch.set_cache_one(df1.get_output())
      stoch.set_cache_two(df2.get_output())
      stoch.set_calibration_one(ifo1,chunk.start())
      stoch.set_calibration_two(ifo2,chunk.start())
      stoch.set_f_min(min)
      stoch.set_f_max(max)
      stoch.set_f_ref((float)(min + max)/2)
      stoch.set_output_dir(dir)

      # add dependancy on LSCdataFind jobs, if required
      if do_datafind:
        stoch.add_parent(df1)
        if ifo1[0] != ifo2[0]:
          stoch.add_parent(df2)

      # add stochastic node
      if do_stochastic:
        dag.add_node(stoch)

# write out the DAG
dag.write_sub_files()
dag.write_dag()

# write a message telling the user that the DAG has been written
print "Created DAG file", dag.get_dag_file()
if do_datafind:
  print """\nAs you are running LSCdataFind jobs, do not forget to initialise your
grid proxy certificate on the condor submit machine by running the
commands

  $ unset X509_USER_PROXY
  $ grid-proxy-init -hours 72

Enter your pass phrase when promted. The proxy will be valid for 72 hours.
If you expect the LSCdataFind jobs to take longer to complete, increase
the time specified in the -hours option to grid-proxy-init. You can check
that the grid proxy has been sucessfully created by executing the command:

  $ grid-cert-info -all -file /tmp/x509up_u`id -u`

This will also give the expiry time of the proxy."""

print """\nThe DAG can now be summitted by executing the following command
on a condor submit machine

  $ condor_submit_dag""", dag.get_dag_file()
print """\nIt is currently recommended that you pass condor_submit_dag the option
-maxjobs 30, to limit the maximum of jobs. This is due to condor being
designed to run jobs that take several hours to complete, whereas the
stochastic jobs are complete within a few minutes. Running the stochastic
pipeline on a cluster without the -maxjobs option will essentially bring
the cluster to a standstill."""

# write out a logfile
if usertag:
  log_fh = open(basename + '.' + usertag + '.pipeline.log', 'w')
else:
  log_fh = open(basename + '.pipeline.log', 'w')

# FIXME: the following code uses obsolete CVS ID tags.
# It should be modified to use git version information.
log_fh.write("$Id$" + "\n\n")
log_fh.write("Invoked with arguments:\n")
for o, a in opts:
  log_fh.write(o + ' ' + a + '\n')

log_fh.write("\nConfig file has the CVS strings:\n")
log_fh.write(cp.get('pipeline','version') + "\n\n")

log_fh.write( "Parsed " + str(len(data)) + " science segments\n" )
total_data = 0
for seg in data:
  for chunk in seg:
    total_data += len(chunk)
print >> log_fh, "total data =", total_data

print >> log_fh, "\n", data
for seg in data:
  print >> log_fh, seg
  for chunk in seg:
    print >> log_fh, chunk

sys.exit(0)

# vim: et syntax=python
