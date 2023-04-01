import numpy as np
import DARCalculator
from astropy.coordinates import SkyCoord
from astropy import units as u

fldcenx=0
fldceny=270

centerRADeg=259.47083333
centerDEC=57.93333333
haDeg=100.52916667*np.pi/180 #in radians

telLatitude = 19.826561 # deg
telLongitude = -155.474234 # deg
referencewavelen = 0.75 # um

def rotate(xs, ys, rotDeg):
    rotRad = np.radians(rotDeg)
    sina = np.sin(rotRad)
    cosa = np.cos(rotRad)
    outxs = xs * cosa - ys * sina
    outys = xs * sina + ys * cosa
    return outxs, outys



def toPNTCenter(paDeg, haDeg):
    """
    Rotates vector to center of telescope and adds refraction correction to center of mask
    Result is pointing center to be stored in FITS file.
    Returns pntRaDeg and pntDecDeg
    """
    ra1, dec1 = calcRefrCoords(centerRADeg, centerDEC, haDeg)
    pntX, pntY = 0,270#self.config.properties["fldcenx"], self.config.properties["fldceny"]

    ra2, dec2 = rotate(pntX, pntY, -paDeg - 90.0)
    cosd = np.cos(np.radians(dec1[0]))
    if abs(cosd) > 1e-5:
        ra2 = ra2 / cosd
    pntRaDeg = ra1[0] + ra2 / 3600
    pntDecDeg = dec1[0] + dec2 / 3600

    return pntRaDeg, pntDecDeg


def calcRefrCoords(centerRADeg, centerDECDeg, haDeg):
    """
    Applies refraction on the center of mask coordinates
    """
    atRefr = DARCalculator.DARCalculator(
       telLatitude, referencewavelen * 1000, 615, 0,
    )

    raDeg, decDeg, refr = atRefr.getRefr([centerRADeg], [centerDECDeg], centerRADeg, haDeg)
    print('getrefr:',refr)
    return raDeg, decDeg



ra,dec=toPNTCenter(0,haDeg)
c0=SkyCoord(centerRADeg*u.deg,centerDEC*u.deg)
c1=SkyCoord(ra*u.deg,dec*u.deg)
cdsim=SkyCoord(259.61207035*u.deg, 57.92550243*u.deg)
print(c1)
sep=c1.separation(c0)
sepdsim=cdsim.separation(c1)
print('From Orig:',sep.arcsec)
print('From Dsim:',sepdsim.arcsec)

