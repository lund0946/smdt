"""
Created on Mar 20, 2018

@author: skwok
"""

from targetSelector import TargetSelector
from smdtLogger import SMDTLogger
from smdtLibs.inOutChecker import InOutChecker
from maskLayouts import MaskLayouts
from smdtLibs import utils, dss2Header, DARCalculator
from astropy.modeling import models
import datetime
import json
import traceback
import pandas as pd
import numpy as np
import sys
import io
import math
import os
import dsim

os.environ["NUMEXPR_MAX_THREADS"] = "4"
os.environ["NUMEXPR_NUM_THREADS"] = "4"

MyJsonEncoder = json.JSONEncoder


M_RCURV = 2120.9
R_IMSURF = 2133.6
M_ANGLE = 6.0
M_ANGLERAD = math.radians(M_ANGLE)
ZPT_YM = 128.803  # Dist to tel.axis, in SMCS-XXX (mm) 5.071in
MASK_HT0 = 3.378
PPLDIST = 20018.4

DIST_C0 = 0
DIST_C2 = -1.111311e-8


class TargetList:
    """
    This class represents the Slitmask Design Tool target list.
    The input and output lists have the same format.
    Note that some colunms are optional.

    If line contains 'PA=nnnn' then the format is
        name RA DEC Eqn PA=nnnnn

    Columns of the input file:
        name: 16 chars, no white space
        ra: right ascension in hour
        dec: declination in deg
        equinox: 2000
        magn: magnitude
        passband: V, I, ...
        pcode: high +value = high priority, -2:align, -1:guide star, 0: ignore

        Optional:
        sampleNr: 1,2,3
        selected: 0 or 1
        slitLPA: PA of the slit
        length1: 4 arcsec
        length2: 4 arcsec
        slitWidth: 1 arcsec

    Input can be a string, a pandas data frame, or a file.
    After reading the input, the targets are stored in a pandas data frame.
    Then targets are projected on the the focal plane, via loadDSSInfo.
    If DSS is not desired (default) then the DSS image is a blank image and
    a header is generated using WCS using cenRA/cenDEC.

    """

    def __init__(self, input, config):
        """
        Reads the target list from file of from string.
        """
        self.config = config
        self.positionAngle = None
        self.centerRADeg = None
        self.centerDEC = None
        self.fileName = None
        self.maskName = "Unknown"
        if type(input) == type(io.StringIO()):
            self.targets = self.readRaw(input)
        elif type(input) == type(pd.DataFrame()):
            self.targets = input
        elif input is None:
            self.targets = pd.DataFrame()
        else:
            self.fileName = input
            self.targets = self.readFromFile(input)

        instrument = "deimos"
        if config is not None:
            instrument = config.properties["instrument"]

        self.xgaps = []
        self.layout = MaskLayouts[instrument]
        self.project2FocalPlane()
        self.__updateDate()

    def getNrTargets(self):
        return self.targets.shape[0]

    def __updateDate(self):
        """
        Remembers the creation date.
        """
        self.createDate = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def project2FocalPlane(self):
        targets = self.targets
        if self.positionAngle is None:
            self.positionAngle = 0
        if len(targets) <= 0:
            self.centerRADeg = self.centerDEC = 0, 0
        else:
            if self.centerRADeg is None and self.centerDEC is None:
                self.centerRADeg = np.mean(targets.raHour) * 15
                self.centerDEC = np.mean(targets.decDeg)

            self.reCalcCoordinates(self.centerRADeg, self.centerDEC, self.positionAngle)

    def _checkPA(self, inLine):
        """
        Checks if input line contains the center RA/DEC and PA
        Used in readRaw
        """
        if not "PA=" in inLine.upper():
            return False
        parts = inLine.split()

        # name, ra, dec, eqx, pa = parts

        for i, s in enumerate(parts):
            if "PA=" in s.upper():
                self.centerRADeg = utils.sexg2Float(parts[i - 3]) * 15
                self.centerDEC = utils.sexg2Float(parts[i - 2])
                parts1 = (" ".join(parts[i:])).split("=")
                self.positionAngle = float(parts1[1].strip())
                self.maskName = parts[i - 4]
                return True
        return False

    def readFromFile(self, fname):
        """
        Reads target list from file
        Returns a Pandas dataframe
        """
        with open(fname, "r") as fh:
            try:
                return self.readRaw(fh)
            except:
                SMDTLogger.info(f"Failed to open {fname}")
                return None

    def readRaw(self, fh):
        """
        Reads target list from file handle
        Returns a Pandas dataframe
        """

        def toFloat(x):
            try:
                return float(x)
            except:
                return 0

        out = []
        cols = (
            "objectId",
            "raHour",
            "decDeg",
            "eqx",
            "mag",
            "pBand",
            "pcode",
            "sampleNr",
            "selected",
            "slitLPA",
            "length1",
            "length2",
            "slitWidth",
            "orgIndex",
            "inMask",
            "raRad",
            "decRad",
        )
        cnt = 0
        params = self.config.getValue("params")
        slitLength = params.getValue("minslitlength", 10)[0]
        halfLen = slitLength / 2
        slitWidth = params.getValue("slitwidth", 1)[0]
        slitpa = params.getValue("slitpa", 0)[0]

        for nr, line in enumerate(fh):
            if not line:
                continue
            line = line.strip()
            p1, p2, p3 = line.partition("#")
            parts = p1.split()
            if len(parts) == 0:
                # line empty
                continue

            objectId = parts[0]
            parts = parts[1:]
            if len(parts) < 3:
                continue
            # print (nr, "len", parts)

            template = ["", "", "2000", "99", "I", "0", "-1", "0", slitpa, halfLen, halfLen, slitWidth, "0", "0"]
            minLength = min(len(parts), len(template))
            template[:minLength] = parts[:minLength]
            if self._checkPA(p1):
                continue

            sampleNr, selected, slitLPA, length1, length2, slitWidth = 1, 1, 0, 4, 4, 1.5
            mag, pBand, pcode = 99, "I", 99

            try:
                raHour = utils.sexg2Float(template[0])
                if raHour < 0 or raHour > 24:
                    raise Exception("Bad RA value " + raHour)
                decDeg = utils.sexg2Float(template[1])
                if decDeg < -90 or decDeg > 90:
                    raise Exception("Bad DEC value " + decDeg)

                eqx = float(template[2])
                if eqx > 3000:
                    eqx = float(template[2][:4])
                    tmp = template[2][4:]
                    template[3 : minLength + 1] = parts[2:minLength]
                    template[3] = tmp

                mag = toFloat(template[3])
                pBand = template[4].upper()
                pcode = int(template[5])
                sampleNr = int(template[6])
                selected = int(template[7])
                slitLPA = toFloat(template[8])
                length1 = toFloat(template[9])
                length2 = toFloat(template[10])
                slitWidth = toFloat(template[11])
                inMask = int(template[12])
            except Exception as e:
                SMDTLogger.info("line {}, error {}, {}".format(nr, e, line))
                # traceback.print_exc()
                # break
                pass
            raRad = math.radians(raHour * 15)
            decRad = math.radians(decDeg)
            target = (
                objectId,
                raHour,
                decDeg,
                eqx,
                mag,
                pBand,
                pcode,
                sampleNr,
                selected,
                slitLPA,
                length1,
                length2,
                slitWidth,
                cnt,
                inMask,
                raRad,
                decRad,
            )
            out.append(target)
            cnt += 1
        df = pd.DataFrame(out, columns=cols)
        # df["inMask"] = np.zeros_like(df.name)

        if self.centerRADeg is None or self.centerRADeg is None:
            msg = "Center RA and DEC undefined. Using averge of input RA and DEC."
            SMDTLogger.info(msg)
            # print(msg)
            self.centerRADeg = df.raHour.mean() * 15
            self.centerDEC = df.decDeg.mean()
            self.positionAngle = 0

        return df

    def getROIInfo(self):
        """
        Returns a dict with keywords that look like fits headers
        Used to show the footprint of the DSS image
        """
        hdr = dss2Header.DssWCSHeader(self.centerRADeg, self.centerDEC, 60, 60)
        north, east = hdr.skyPA()

        nlist = "platescl", "xpsize", "ypsize"  # , 'raDeg', 'decDeg'
        out = {n: hdr.__dict__[n] for n in nlist}

        out["centerRADeg"] = "%.7f" % self.centerRADeg
        out["centerDEC"] = "%.7f" % self.centerDEC
        out["NAXIS1"] = hdr.naxis1
        out["NAXIS2"] = hdr.naxis2

        out["northAngle"] = north
        out["eastAngle"] = east
        out["xpsize"] = hdr.xpsize  # pixel size in micron
        out["ypsize"] = hdr.ypsize  # pixel size in micron
        out["platescl"] = hdr.platescl  # arcsec / mm
        out["positionAngle"] = self.positionAngle
        return out

    def toJson(self):
        """
        Returns the targets in JSON format
        """
        tgs = self.targets
        data = [list(tgs[i]) for i in tgs]
        data1 = {}
        for i, colName in enumerate(tgs.columns):
            data1[colName] = data[i]

        return json.dumps(data1, cls=MyJsonEncoder)

    def toJsonWithInfo(self):
        """
        Returns the targets and ROI info in JSON format
        """
        tgs = self.targets
        data = [list(tgs[i]) for i in tgs]
        data1 = {}
        for i, colName in enumerate(tgs.columns):
            data1[colName] = data[i]

        data2 = {"info": self.getROIInfo(), "targets": data1, "xgaps": self.xgaps}

        return json.dumps(data2, cls=MyJsonEncoder)

    def setColum(self, colName, value):
        """
        Updates the dataframe by column name
        """
        self.targets[colName] = value

    def calcSlitPosition(self, minX, maxX, minSlitLength, minSep, ext):
        """
        Selects the targets to put on slits
        ext: extends to fill gaps
        """
        self.markInside()
        selector = TargetSelector(self.targets, minX, maxX, minSlitLength, minSep)
        self.targets = selector.performSelection(extendSlits=ext)
        self.xgaps = selector.xgaps
        self.selector = selector
        self.calcSlitXYs()

    def findTarget(self, targetName):
        """
        Finds entry with the given targName.
        Returns idx, or -1 if not found
        """
        for i, stg in self.targets.iterrows():
            if stg.objectId == targetName:
                return stg.orgIndex
        return -1

    def updateTarget(self, jvalues):
        """
        Used by GUI to change values in a target.
        """
        values = json.loads(jvalues)
        tgs = self.targets

        pcode = int(values["prior"])
        selected = int(values["selected"])
        slitLPA = float(values["slitLPA"])
        slitWidth = float(values["slitWidth"])
        len1 = float(values["len1"])
        len2 = float(values["len2"])
        targetName = values["targetName"]

        raSexa = values["raSexa"]
        decSexa = values["decSexa"]
        raHour = utils.sexg2Float(raSexa)
        decDeg = utils.sexg2Float(decSexa)

        raRad = math.radians(raHour * 15)
        decRad = math.radians(decDeg)

        idx = self.findTarget(targetName)

        if idx >= 0:
            # Existing entry
            tgs.at[idx, "pcode"] = pcode
            tgs.at[idx, "selected"] = selected
            tgs.at[idx, "slitLPA"] = slitLPA
            tgs.at[idx, "slitWidth"] = slitWidth
            tgs.at[idx, "length1"] = len1
            tgs.at[idx, "length2"] = len2

            tgs.at[idx, "raHour"] = raHour
            tgs.at[idx, "decDeg"] = decDeg
            tgs.at[idx, "raRad"] = raRad
            tgs.at[idx, "decRad"] = decRad

            SMDTLogger.info(
                f"Updated target {idx}, ra {raSexa}, dec {decSexa}, pcode={pcode}, selected={selected}, slitLPA={slitLPA:.2f}, slitWidth={slitWidth:.2f}, len1={len1}, len2={len2}"
            )
        else:
            # Add a new entry
            idx = self.targets.obejctName.shape[0]
            newItem = {
                "objectId": targetName,
                "raHour": raHour,
                "decDeg": decDeg,
                "eqx": 2000,
                "mag": int(values["mag"]),
                "pBand": values["pBand"],
                "pcode": int(values["prior"]),
                "sampleNr": 1,
                "selected": selected,
                "slitLPA": slitLPA,
                "inMask": 0,
                "length1": len1,
                "length2": len2,
                "slitWidth": slitWidth,
                "orgIndex": idx,
                "raRad": raRad,
                "decRad": decRad,
            }

            self.targets = tgs.append(newItem, ignore_index=True)

            SMDTLogger.info(
                f"New target {targetName}, ra {raSexa}, dec {decSexa}, pcode={pcode}, selected={selected}, slitLPA={slitLPA:.2f}, slitWidth={slitWidth:.2f}, len1={len1}, len2={len2}, idx={idx}"
            )

        self.reCalcCoordinates(self.centerRADeg, self.centerDEC, self.positionAngle)
        return idx

    def deleteTarget(self, idx):
        """
        Remove a row idx from the data frame
        """
        if idx < 0:
            return
        tgs = self.targets
        self.targets = tgs.drop(tgs.index[idx])
        SMDTLogger.info("Delete target idx")

    def markInside(self):
        """
        Sets the inMask flag to 1 (inside) or 0 (outside)
        """
        inOutChecker = InOutChecker(self.layout)
        tgs = self.targets
        inMask = []
        for i, stg in tgs.iterrows():
            isIn = 1 if inOutChecker.checkPoint(stg.xarcs, stg.yarcs) else 1##Test1setto0
            inMask.append(isIn)
        self.targets["inMask"] = inMask









    def reCalcCoordinates(self, raDegfld, decDegfld, posAngleDegfld):
        """
        Recalculates xarcs and yarcs for new center RA/DEC and positionAngle
        Results saved in xarcs, yarcs

        Returns xarcs, yarcs in focal plane coordinates in arcs.
        """


        from astropy import units as u
        from astropy.coordinates import Angle


#        telRaRad, telDecRad = self._fld2telax(raDeg, decDeg, posAngleDeg)
#        self.telRaRad, self.telDecRad = telRaRad, telDecRad
#        xarcs, yarcs = self._calcTelTargetCoords(telRaRad, telDecRad, self.targets.raRad, self.targets.decRad, posAngleDeg)
#        self.targets["xarcs"] = xarcs
#        self.targets["yarcs"] = yarcs


        params=dsim.readparams('temp_config.params')
        tofloat=['ra0','dec0','pa0','ha0','min_slit','sep_slit','slit_width','box_sz','blue','red','lambda_cen','temp','pressure']
        for k in tofloat:
            params[k]=float(params[k])


### Note -- make sure center is updated

        print(params)

#        data=pd.read_table(params['objfile'],skiprows=0,comment='#',delim_whitespace=True)
   
        ra=self.targets["raHour"]
        dec=self.targets["decDeg"]
        mag=self.targets["mag"]
        magband=self.targets["pBand"]
        pcode=self.targets["pcode"]
        sel=self.targets["selected"]
        slitpa=self.targets["slitLPA"]
        pcode=self.targets["pcode"]

        raDeg,decDeg=[],[]
        _pcode=[]
        _mag,_magband=[],[]
        ra=Angle(ra,unit=u.hour)
        dec=Angle(dec,unit=u.deg)
        for i in range(len(ra)):
            raDeg.append(ra[i].degree)
            decDeg.append(dec[i].degree)
  
        from datetime import datetime
        params['descreate']=datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        obs,site=dsim.init_dicts(params,raDeg,decDeg,slitpa,pcode,mag,magband)
        obs=dsim.refr_coords(obs,site)
        obs=dsim.fld2telax(obs,'ra_fldR','dec_fldR','ra_telR','dec_telR')
        obs=dsim.tel_coords(obs,'raRadR','decRadR','ra_telR','dec_telR')
        self.obs=obs
        self.site=site
        self.targets["xarcs"],self.targets["yarcs"]=obs['xarcs'],obs['yarcs']
        self.__updateDate()



        
    def calcSlits(self,minX, maxX, minSlitLength, minSep, ext):

        self.markInside()
        selector = TargetSelector(self.targets, minX, maxX, minSlitLength, minSep)
        self.targets = selector.performSelection(extendSlits=ext)
        self.xgaps = selector.xgaps
        self.selector = selector
#        self.calcSlitXYs()

        slit=dsim.gen_slits(self.obs)
        slit=dsim.sky_coords(slit)
        slit=dsim.unrefr_coords(slit,self.site)
        slit=dsim.fld2telax(slit,'ra0_fldU','dec0_fldU','ra_telU','dec_telU')
        slit=dsim.tel_coords(slit,'raRadU','decRadU','ra_telU','dec_telU')
        slit=dsim.mask_coords(slit)


