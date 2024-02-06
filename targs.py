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
        out.append(dict(zip(cols, target)))
        cnt += 1

    return out 


def to_json_with_info(params, targetList, xgaps=[]):
    """
    Returns the targets and ROI info in JSON format
    """
    data = {"info": getROIInfo(params), "targets": targetList, "xgaps": xgaps}
    return json.dumps(data)


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


def update_column(targetList, col, value):
    """
    Used by GUI to change values to an entire column of a target.
    """


    if col == 'length1' or col == 'length2':
        targetList = [ {**target, 'length1': float(value), 'length2': float(value)} for target in targetList]
    else:
        targetList = [ {**target, col: float(value)} for target in targetList]
    logger.debug(f'update_column {col}')
    return targetList


def update_target(targetList, jvalues):
    """
    Used by GUI to change values in a target.
    """

    logger.debug('Running update_target')

    values = jvalues

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

    idx = next((index for (index, d) in enumerate(targetList) if d["objectId"] == targetName), None)

    if not idx is None:
        # Existing entry
        targetList[idx]["pcode"] = pcode
        targetList[idx]["selected"] = selected
        targetList[idx]["slitLPA"] = slitLPA
        targetList[idx]["slitWidth"] = slitWidth
        targetList[idx]["length1"] = len1
        targetList[idx]["length2"] = len2
        targetList[idx]["mag"] = mag
        targetList[idx]["raHour"] = raHour
        targetList[idx]["decDeg"] = decDeg
        targetList[idx]["raRad"] = raRad
        targetList[idx]["decRad"] = decRad
    else:
        # Add a new entry
        idx = len(targetList)
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
        

        targetList.append(newItem)

    return targetList, idx

def mark_inside(targetList):
    """
    Sets the inMask flag to 1 (inside) or 0 (outside)
    """
    layout = MaskLayouts['deimos']
    inOutChecker = InOutChecker(layout)
    outTargets = [] 
    for target in targetList:
        isIn = int(inOutChecker.checkPoint(target.get('xarcs'), target.get('yarcs')))
        outTargets.append( {**target, 'inMask': isIn})
    return outTargets 
