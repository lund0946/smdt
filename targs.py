import pandas as pd

import utils
import json
import math
import dss2Header
from inOutChecker import InOutChecker
from maskLayouts import MaskLayouts
import logging
logger = logging.getLogger('smdt')


def readRaw(fh, params):
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
    slitLength = float(params["MinSlitLength"])  # correct paramn name?
    halfLen = slitLength / 2.
    slitWidth = params["SlitWidth"]
    slitpa = params["SlitPA"]

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

        if 'PA=' in line:
            # line has dsim output first line
            continue
        # print (nr, "len", parts)

        template = ["", "", "2000", "99", "I", "0", "-1", "0",
                    slitpa, halfLen, halfLen, slitWidth, "0", "0"]
        minLength = min(len(parts), len(template))
        template[:minLength] = parts[:minLength]

        sampleNr, selected, slitLPA, length1, length2, slitWidth = 1, 1, 0, 4, 4, 1.5
        mag, pBand, pcode = 99, "I", 99

        try:
            try:
                raHour = float(template[0])
            except:
                raHour = utils.sexg2Float(template[0])
            if raHour < 0 or raHour > 24:
                raise Exception("Bad RA value " + raHour)
            try:
                decDeg = float(template[1])
            except:
                decDeg = utils.sexg2Float(template[1])
            if decDeg < -90 or decDeg > 90:
                raise Exception("Bad DEC value " + decDeg)

            eqx = float(template[2])
            if eqx > 3000:
                eqx = float(template[2][:4])
                tmp = template[2][4:]
                template[3: minLength + 1] = parts[2:minLength]
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
        except Exception as err:
            logger.error(err)
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

    fieldcenterRADeg = df.raHour.mean() * 15
    fieldcenterDEC = df.decDeg.mean()

    return df


def toJsonWithInfo(params, tgs, xgaps=[]):
    """
    Returns the targets and ROI info in JSON format
    """
    data = [list(tgs[i]) for i in tgs]
    data1 = {}
    for i, colName in enumerate(tgs.columns):
        data1[colName] = data[i]
    data2 = {"info": getROIInfo(params), "targets": data1, "xgaps": xgaps}
    return json.dumps(data2)


def getROIInfo(params):
    """
    Returns a dict with keywords that look like fits headers
    Used to show the footprint of the DSS image
    """

    centerRADeg, centerDEC, positionAngle = 15*utils.sexg2Float(
        params['InputRA']), utils.sexg2Float(params['InputDEC']), params['MaskPA']

    hdr = dss2Header.DssWCSHeader(centerRADeg, centerDEC, 60, 60)
    north, east = hdr.skyPA()

    nlist = "platescl", "xpsize", "ypsize"  # , 'raDeg', 'decDeg'
    out = {n: hdr.__dict__[n] for n in nlist}

    out["centerRADeg"] = "%.7f" % centerRADeg
    out["centerDEC"] = "%.7f" % centerDEC
    out["NAXIS1"] = hdr.naxis1
    out["NAXIS2"] = hdr.naxis2

    out["northAngle"] = north
    out["eastAngle"] = east
    out["xpsize"] = hdr.xpsize  # pixel size in micron
    out["ypsize"] = hdr.ypsize  # pixel size in micron
    out["platescl"] = hdr.platescl  # arcsec / mm
    out["positionAngle"] = positionAngle
    return out


def setColum(targets, colName, value):
    """
    Updates the dataframe by column name
    """
    targets[colName] = value
    return targets


def findTarget(targets, targetName):
    """
    Finds entry with the given targName.
    Returns idx, or -1 if not found
    """
    for i, stg in targets.iterrows():
        if stg.objectId == targetName:
            return stg.orgIndex
    return -1


def updateColumn(targets, col, value):
    """
    Used by GUI to change values to an entire column of a target.
    """


    if col == 'length1' or col == 'length2':
        targets['length1'] = float(value)
        targets['length2'] = float(value)
    else:
        targets[col] = float(value)
    logger.debug(f'updateColumn {targets[col]}')
    return targets


def updateTarget(targets, jvalues):
    """
    Used by GUI to change values in a target.
    """

    logger.debug('Running updateTarget')

    values = jvalues
    tgs = targets

    pcode = int(values["prior"])
    selected = int(values["selected"])
    slitLPA = float(values["slitLPA"])
    slitWidth = float(values["slitWidth"])
    len1 = float(values["len1"])
    len2 = float(values["len2"])
    targetName = values["targetName"]
    mag = float(values["mag"])
    raSexa = values["raSexa"]
    decSexa = values["decSexa"]
    raHour = utils.sexg2Float(raSexa)
    decDeg = utils.sexg2Float(decSexa)

    raRad = math.radians(raHour * 15)
    decRad = math.radians(decDeg)

    idx = findTarget(tgs, targetName)

    if idx >= 0:
        # Existing entry
        tgs.at[idx, "pcode"] = pcode
        tgs.at[idx, "selected"] = selected
        tgs.at[idx, "slitLPA"] = slitLPA
        tgs.at[idx, "slitWidth"] = slitWidth
        tgs.at[idx, "length1"] = len1
        tgs.at[idx, "length2"] = len2
        tgs.at[idx, "mag"] = mag
        tgs.at[idx, "raHour"] = raHour
        tgs.at[idx, "decDeg"] = decDeg
        tgs.at[idx, "raRad"] = raRad
        tgs.at[idx, "decRad"] = decRad

     # Missing targets=tgs????????

    else:
        # Add a new entry
        idx = len(targets.index)
        logger.debug(f'idx= {idx}')

        newItem = {
            "objectId": targetName,
            "raHour": raHour,
            "decDeg": decDeg,
            "eqx": 2000,
            "mag": values["mag"],
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

        targets = tgs.append(newItem, ignore_index=True)

    return targets, idx


def deleteTarget(targets, idx):
    """
    Remove a row idx from the data frame
    """
    tgs = targets
    logger.debug(f'Index to delete {idx}')
    if idx < 0:
        return
    targets = tgs.drop(tgs.index[idx])
    return targets


def markInside(targets):
    """
    Sets the inMask flag to 1 (inside) or 0 (outside)
    """
    layout = MaskLayouts['deimos']
    inOutChecker = InOutChecker(layout)
    tgs = targets
    inMask = []
    for i, stg in tgs.iterrows():
        isIn = 1 if inOutChecker.checkPoint(stg.xarcs, stg.yarcs) else 0
        inMask.append(isIn)
    targets["inMask"] = inMask
    return targets
