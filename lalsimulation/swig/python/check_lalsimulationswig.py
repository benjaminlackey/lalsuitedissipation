# Check SWIG Python module wrapping lalsimulation
# Author: Karl Wette, 2011, 2012

# check module load
import lal
import lalsimulation
from lalsimulation import cvar as lalsimulationcvar
from lal import cvar as lalcvar
lalcvar.lalDebugLevel = 1
print("passed module load")

# check object parent tracking
if not lalcvar.swig_debug:
    print("skipping object parent tracking")
else:
    a = lalsimulation.lalsimulationswig_test_parent_map_struct()
    for i in range(0, 7):
        b = a.s
        c = lalsimulationcvar.lalsimulationswig_test_parent_map.s
        lalsimulationcvar.lalsimulationswig_test_parent_map.s = lalcvar.lalswig_test_struct_const
    del a, b, c
    lal.CheckMemoryLeaks()
    print("passed object parent tracking")

# passed all tests!
print("PASSED all tests")
