import sys
import os
import logging
import argparse
import datetime
import json
import traceback
import pandas as pd
import numpy as np
import io
import math

from astropy import units as u
from astropy.coordinates import Angle


from smdtLibs import sl
from smdtLibs.configFile import ConfigFile
from smdtLibs import utils, dss2Header
from diffSlitMask import DiffSlitMask
from maskDesignFile import MaskDesignOutputFitsFile
import maskLayouts
from smdtLibs import drawUtils, utils





####
##Currently reading in the dsim output##
####

#data=pd.read_table('/Users/mlundquist/Projects/KECK/DSIMULATOR/iraf_docker/newdsim/NGC_3001_tilt.sel',skiprows=0,comment='#',delim_whitespace=True)

data=pd.read_table('engtask/mNGC2459_315.sel',skiprows=0,comment='#',delim_whitespace=True)

print(data)



ra=data.iloc[:,1]
dec=data.iloc[:,2]
mag=data.iloc[:,4]
magband=data.iloc[:,5]
pcode=data.iloc[:,6]
sel=data.iloc[:,8]

try:
    print('Found tilts')
    slit_pa=data.iloc[:,9]
    print(slit_pa)
    tilt=True
except:
    print('No slit tilt')
    tile=False
raDeg,decDeg=[],[]
slitpa=[]
_pcode=[]
_mag,_magband=[],[]
ra=Angle(ra,unit=u.hour)
dec=Angle(dec,unit=u.deg)
for i in range(len(ra)):

    if sel[i]==1:
        if tilt==True:
            print('range-len(ra)',slit_pa[i])
            slitpa.append(slit_pa[i])
        else:
            slitpa.append(-9999)
        raDeg.append(ra[i].degree)
        decDeg.append(dec[i].degree)
        _pcode.append(pcode[i])
        _mag.append(mag[i])
        _magband.append(magband[i])

pcode=_pcode
mag=_mag
magband=_magband

