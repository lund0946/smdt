import pandas as pd
import pdb
import numpy as np
import gslit
from writeMask import MaskDesignOutputFitsFile
from astropy import units as u
from astropy.coordinates import Angle
import sl
import utils
import dsimselector
import logging
logger = logging.getLogger('smdt')


def init_dicts(targetList, params):

    ra, dec, mag, magband, pcode, sel, slit_pa, objectId, dlength1, dlength2 = [], [], [], [], [], [], [], [], [], []
    for target in targetList:
        ra.append(target['raHour'])
        dec.append(target['decDeg'])
        mag.append(target['mag'])
        magband.append(target['pBand'])
        pcode.append(target['pcode'])
        sel.append(target['selected'])
        slit_pa.append(target.get('slitLPA', -9999))
        objectId.append(target['objectId'])
        # <---------  Needs an if since it's an optional parameter?
        dlength1.append(target['length1'])
        dlength2.append(target['length2'])

    tilt = True if -9999 not in slit_pa else False
    raDeg, decDeg = [], []
    slitpa = []
    ra = Angle(ra, unit=u.hour)
    dec = Angle(dec, unit=u.deg)
    for i in range(len(ra)):
        if tilt == True:
            slitpa.append(slit_pa[i])
        else:
            slitpa.append(-9999)
        raDeg.append(ra[i].degree)
        decDeg.append(dec[i].degree)

    # Check sexagesimal conversion
    centerRADeg = utils.sexg2Float(params['InputRA'])*15
    centerDECDeg = utils.sexg2Float(params['InputDEC'])

    haDeg = float(params['HourAngle'])
    positionAngle = float(params['MaskPA'])

    ra0_fld = np.radians(centerRADeg)
    dec0_fld = np.radians(centerDECDeg)
    ha0_fld = np.radians(15*haDeg)
    slitpa = np.radians(slitpa)
    raRad = np.radians(raDeg)
    decRad = np.radians(decDeg)
    lst = ra0_fld + ha0_fld
    pa0_fld = np.radians(positionAngle)

    length1, length2 = [], []
    rlength1, rlength2 = [], []

    slitLPA = []
    slitWidth = []
    for i in range(len(raRad)):  # Manual Hacks
        if pcode[i] != -2:
            # Set manually later???  #### <<<<------------
            slitWidth.append(float(params['SlitWidth']))
            length1.append(dlength1[i])
            length2.append(dlength2[i])
            rlength1.append(dlength1[i])
            rlength2.append(dlength2[i])
            slitLPA.append(slitpa[i])
        else:
            slitWidth.append(float(params['AlignBoxSize']))
            # slitlength manual
            length1.append(float(params['AlignBoxSize'])*0.5)
            length2.append(float(params['AlignBoxSize'])*0.5)
            # slitlength manual
            rlength1.append(float(params['AlignBoxSize'])*0.5)
            rlength2.append(float(params['AlignBoxSize'])*0.5)
            slitLPA.append(0)

    obs_lat = 19.8
    obs_alt = 4150.
    mm_arcs = 0.7253
    waver = float(params['CenterWaveLength'])
    wavemn = float(params['BlueWaveLength'])
    wavemx = float(params['RedWaveLength'])
    pres = float(params['Pressure'])
    temp = float(params['Temperature'])
    obs_rh = 0.4  # <--------- Add to webpage params!

    lat = np.radians(obs_lat)        # radians
    htm = obs_alt                   # meters
    tdk = temp + 273.15      # temp in K
    pmb = pres               # millibars
    rel_h20 = obs_rh                # relative humidity
    w = waver/10000.  # reference wavelength conv. to micron

    obs = []
    for idx in range(len(raRad)):
        ob = {'objectId': objectId[idx],
            'ra0_fld': ra0_fld,
            'dec0_fld': dec0_fld,
            'ha0_fld': ha0_fld,
            'raRad': raRad[idx],
            'decRad': decRad[idx],
            'lst': lst,
            'pa0_fld': pa0_fld,
            'length1': length1[idx],
            'length2': length2[idx],
            'rlength1': rlength1[idx],
            'rlength2': rlength2[idx],
            'slitLPA': slitLPA[idx],
            'pcode': pcode[idx],
            'slitWidth': slitWidth[idx],
            'slitpa': slitpa[idx],
            'mag': mag[idx],
            'magband': magband[idx],
            'selected': sel[idx]
            }
        obs.append(ob)
    site = {'lat': lat, 'htm': htm, 'tdk': tdk, 'pmb': pmb,
            'rel_h20': rel_h20, 'w': w, 'wavemn': wavemn, 'wavemx': wavemx}

    return obs, site


def refr_coords(obs, site):

    # Get the refraction coeffs (2 hardcodes suggested in SLALIB):
    r1, r3 = sl.slrfco(site['htm'], site['tdk'], site['pmb'],
                       site['rel_h20'], site['w'], site['lat'], 0.0065, 1.e-10)

    obsOut = []
    for ob in obs:

        # Apply to field center
        az, el = sl.slde2h(ob['ha0_fld'], ob['dec0_fld'], site['lat'])
        zd0 = np.pi/2. - el
        zd = sl.slrefz(zd0, r1, r3)
        elr = np.pi/2. - zd
        har, dec_fld = sl.sldh2e(az, elr, site['lat'])
        ra_fld = ob['lst'] - har

        zd = sl.slrefz(zd0, r1, r3)
        ha = ob['lst'] - ob['raRad']
        az, el = sl.slde2h(ha, ob['decRad'], site['lat'])
        zd0 = np.pi/2. - el
        zd = sl.slrefz(zd0, r1, r3)
        elr = np.pi/2. - zd

        har, _dec = sl.sldh2e(az, elr, site['lat'])
        _ra = ob['lst'] - har

        ob['raRadR'] = _ra 
        ob['decRadR'] = _dec 
        ob['ra_fldR'] = ra_fld
        ob['dec_fldR'] = dec_fld 
        # Save the refraction coeffs for later use:
        ob['orig_ref1'] = r1
        ob['orig_ref3'] = r3
        obsOut.append(ob)

    return obsOut 


def fld2telax(obs, ra_fld, dec_fld, ratel, dectel):
    # FLD2TELAX:  from field center and rotator PA, calc coords of telescope axis
    FLDCEN_X = 0.
    FLDCEN_Y = 270.
    # convert field center offset (arcsec) to radians
    r = np.radians(np.sqrt(FLDCEN_X*FLDCEN_X + FLDCEN_Y*FLDCEN_Y) / 3600.)
    # get PA of field center
    pa_fld = np.arctan2(FLDCEN_Y, FLDCEN_X)
    cosr = np.cos(r)
    sinr = np.sin(r)
    outObs = []
    for ob in obs:


        PA_ROT = ob['pa0_fld']
        cost = np.cos(PA_ROT - pa_fld)
        sint = np.sin(PA_ROT - pa_fld)

        cosd = np.cos(ob[dec_fld])
        sind = np.sin(ob[dec_fld])

        sina = sinr * sint / cosd               # ASSUME not at dec=90
        cosa = np.sqrt(1. - sina*sina)

        ra_tel = ob[ra_fld]- np.arcsin(sina)
        dec_tel = np.arcsin((sind*cosd*cosa - cosr*sinr*cost) /
                            (cosr*cosd*cosa - sinr*sind*cost))
        ob[ratel] = ra_tel
        ob[dectel] = dec_tel
        outObs.append(ob)
    return outObs

def tel_coords(obs, ra, dec, ra0, dec0, proj_len=False):
    flip = -1
    # PA_ROT better be in radians <-- should be pa_rot??  I think this needs to clearly be PA_ROT
    outObs = []
    for ob in obs:
        pa0 = ob['pa0_fld']
        dec_obj = ob[dec]
        del_ra = ob[ra] - ob[ra0]

        cosr = np.sin(dec_obj) * np.sin(ob[dec0]) + \
            np.cos(dec_obj) * np.cos(ob[dec0]) * np.cos(del_ra)
        r = np.arccos(cosr)
        sinp = np.cos(dec_obj) * np.sin(del_ra) / np.sqrt(1. - cosr*cosr)
        cosp = np.sqrt(np.max([(1. - sinp*sinp), 0.]))
        if (dec_obj < ob[dec0]):
            cosp = -cosp
        p = np.arctan2(sinp, cosp)

        # convert radii to arcsec
        # convert r to tan(r) to get tan projection
        r = np.tan(r) * 206264.8
        _xarcs = r * np.cos(pa0 - p)
        _yarcs = r * np.sin(pa0 - p)

        if ob['pcode'] == -2:  # No individual slit angles
            ob['slitpa'] = -9999
            _relpa = None
            rangle = 0.  # 90 not zero??
        else:
            _relpa = ob['slitpa'] - pa0  # check that slitLPA is available
            rangle = _relpa

        # For simplicity, we calculate the endpoints in X here; note use of FLIP
        xgeom = (flip) * np.cos(rangle)
        ygeom = np.sin(rangle)
        if (proj_len == True):
            xgeom = xgeom / np.abs(np.cos(rangle))
            ygeom = ygeom / np.abs(np.cos(rangle))

        # We always want X1 < X2, so:
        length1 = ob['length1']
        length2 = ob['length2']
        if (xgeom > 0):
            _X1 = _xarcs - length1 * xgeom
            _Y1 = _yarcs - length1 * ygeom
            _X2 = _xarcs + length2 * xgeom
            _Y2 = _yarcs + length2 * ygeom
        else:
            _X2 = _xarcs - length1 * xgeom
            _Y2 = _yarcs - length1 * ygeom
            _X1 = _xarcs + length2 * xgeom
            _Y1 = _yarcs + length2 * ygeom

        ob['X1'] =_X1 
        ob['X2'] =_X2 
        ob['Y1'] =_Y1
        ob['Y2'] =_Y2
        ob['xarcs'] =_xarcs
        ob['yarcs'] =_yarcs
        ob['relpa'] =_relpa
        outObs.append(ob)
    return outObs 

def gen_slits_from_obs(obs, min_slit, slit_gap, adj_len=False, auto_sel=True):
    for idx, ob in enumerate(obs):

        ob['index'] = idx 
        ob['slitIndex'] = idx 
        if ob['pcode'] == -2:  
            ob['slitpa'] == -9999
            ob['slitLPA'] = ob['pa0_fld']
            ob['relpa'] = None
        else:
            ob["slitLPA"] = ob['slitpa']

    obs = dsimselector.from_list(obs, min_slit, slit_gap, sel=True)
    if adj_len:
        obs = gslit.len_slits(obs, slit_gap)
    return obs


def sky_coords(slit):
    out = []
    for ob in slit:
        ra0 = ob['ra_telR']
        dec0 = ob['dec_telR']
        pa0 = ob['pa0_fld']

        xarc = 0.5 * (ob['X1'] + ob['X2'])
        yarc = 0.5 * (ob['Y1'] + ob['Y2'])

        r = np.sqrt(xarc*xarc + yarc*yarc)
        r = np.arctan(r/206264.8)

        phi = pa0 - np.arctan2(yarc, xarc)        # WORK

        sind = np.sin(dec0) * np.cos(r) + np.cos(dec0) * \
            np.sin(r) * np.cos(phi)

        sina = np.sin(r) * np.sin(phi) / np.sqrt(1. - sind*sind)
        dec = np.arcsin(sind)
        ra = ra0 + np.arcsin(sina)

        # PA = already assigned    <------ check if true with new list
        # calc the centers and lengths of the slits
        # XXX NB: by convention, slit length will be defined as TOTAL length

        x = ob['X2'] - ob['X1']
        y = ob['Y2'] - ob['Y1']
        len1 = 0.5 * np.sqrt(x*x + y*y)

        # Slit length on either side of target

        xl2 = ob['X2'] - ob['xarcs']
        yl2 = ob['Y2'] - ob['yarcs']
        xl1 = ob['xarcs'] - ob['X1']
        yl1 = ob['yarcs'] - ob['Y1']
        rlen1 = np.sqrt(xl1*xl1 + yl1*yl1)
        rlen2 = np.sqrt(xl2*xl2 + yl2*yl2)

        add = {'xarcsS': xarc, 'yarcsS': yarc,
            'length1S': len1, 'length2S': len1, # length1S and length2S are the same
            'rlength1': rlen1, 'rlength2': rlen2,
            'raRadS': ra, 'decRadS': dec}

        out.append({**ob, **add})

    return out 

# UNREFR_COORDS
def unrefr_coords(slit, site):

    outSlit = []
    for ob in slit:
        raRad = ob['raRadS']
        decRad = ob['decRadS']
        ha_fld = ob['ha0_fld']
        lst = ob['ra0_fld'] + ha_fld     # XXX Verify correct/see above

        # Apply to field center
        # XXX Clean up (see above) This is refracted ha. already saved
        ha = lst - ob['ra_fldR']
        az, el = sl.slde2h(ha, ob['dec_fldR'], site['lat'])
        zd = np.pi/2. - el
        tanz = np.tan(zd)
        zd = zd + ob['orig_ref1'] * tanz + ob['orig_ref3'] * tanz**3
        el = np.pi/2. - zd
        ha0, dec0_fld = sl.sldh2e(az, el, site['lat'])
        ra0_fld = lst - ha0

        ob['ra0_fldU'] = ra0_fld
        ob['dec0_fldU'] = dec0_fld

        ob['newcenterRADeg'] = np.degrees(ra0_fld)
        ob['newcenterDECDeg'] = np.degrees(dec0_fld)

        ha = lst - raRad
        az, el = sl.slde2h(ha, decRad, site['lat'])

        zd = np.pi/2. - el
        tanz = np.tan(zd)
        zd = zd + ob['orig_ref1'] * tanz + ob['orig_ref3'] * tanz**3
        el = np.pi/2. - zd

        ha0, _dec0 = sl.sldh2e(az, el, site['lat'])
        _ra0 = lst - ha0
        ob['raRadU'] = _ra0
        ob['decRadU'] = _dec0
        outSlit.append(ob)

    return outSlit 


def mask_coords_bak(obs):
    asec_rad = 206264.80
    FLIP = -1.
    RELPA = obs['relpa']
    XARCS = obs['xarcsS']
    YARCS = obs['yarcsS']
    # Correct?  -- correct for xarcsS since both are centered on the slit
    LEN1 = obs['length1S']
    LEN2 = obs['length2S']  # Correct?
    FL_TEL = 150327.0

    X1 = obs['X1']
    Y1 = obs['Y1']
    X2 = obs['X2']
    Y2 = obs['Y2']


# offset from telescope axis to slitmask origin, IN SLITMASK COORDS
#        yoff = ZPT_YM * (1. - np.cos (np.radians(M_ANGLE)))
    yoff = 0.       # XXX check!  Am not sure where the above comes from
    xoff = 0.

    SLWID = []
    XMM1, YMM1, XMM2, YMM2, XMM3, YMM3, XMM4, YMM4 = [], [], [], [], [], [], [], []
    xfp1, yfp1, xfp2, yfp2, xfp3, yfp3, xfp4, yfp4 = [], [], [], [], [], [], [], []
    for i in range(len(RELPA)):

        SLWID.append(obs['slitWidth'][i])
#        if obs['pcode'][i]==-2:           ########## <--- alignment box                       <<<----should be done earlier?
#            SLWID.append(4)
#        else:
#            SLWID.append(obs['slitWidth'][i])

# XXX For now, carry through the RELPA thing; in end, must be specified!
        if (RELPA[i] != None):
            cosa = np.cos(RELPA[i])
            sina = np.sin(RELPA[i])
        else:
            cosa = 1.
            sina = 0.

# This is a recalculation ... prob not needed
        X1[i] = XARCS[i] - LEN1[i] * cosa * FLIP
        Y1[i] = YARCS[i] - LEN1[i] * sina
        X2[i] = XARCS[i] + LEN2[i] * cosa * FLIP
        Y2[i] = YARCS[i] + LEN2[i] * sina


# X1,Y1 are now tan projections already!

        xfp = FL_TEL * X1[i] / asec_rad
        yfp = FL_TEL * (Y1[i] - 0.5*SLWID[i]) / asec_rad
        pa = 0.

        xfp1.append(X1[i])
        yfp1.append(Y1[i] - 0.5*SLWID[i])

        xfp, yfp = gnom_to_dproj(xfp, yfp)         # (allowed)
        xsm, ysm, pa = proj_to_mask(xfp, yfp, pa)

        XMM1.append(xsm + xoff)
        YMM1.append(ysm + yoff)

        xfp = FL_TEL * X2[i] / asec_rad
        yfp = FL_TEL * (Y2[i] - 0.5*SLWID[i]) / asec_rad
        pa = 0.

        xfp2.append(X2[i])
        yfp2.append(Y2[i] - 0.5*SLWID[i])

        xfp, yfp = gnom_to_dproj(xfp, yfp)         # (allowed)
        xsm, ysm, pa = proj_to_mask(xfp, yfp, pa)

        XMM2.append(xsm + xoff)
        YMM2.append(ysm + yoff)

        xfp = FL_TEL * X2[i] / asec_rad
        yfp = FL_TEL * (Y2[i] + 0.5*SLWID[i]) / asec_rad
        pa = 0.

        xfp3.append(X2[i])
        yfp3.append(Y2[i] + 0.5*SLWID[i])

        xfp, yfp = gnom_to_dproj(xfp, yfp)         # (allowed)
        xsm, ysm, pa = proj_to_mask(xfp, yfp, pa)

        XMM3.append(xsm + xoff)
        YMM3.append(ysm + yoff)

        xfp = FL_TEL * X1[i] / asec_rad
        yfp = FL_TEL * (Y1[i] + 0.5*SLWID[i]) / asec_rad
        pa = 0.

        xfp4.append(X1[i])
        yfp4.append(Y1[i] + 0.5*SLWID[i])

        xfp, yfp = gnom_to_dproj(xfp, yfp)         # (allowed)
        xsm, ysm, pa = proj_to_mask(xfp, yfp, pa)

        XMM4.append(xsm + xoff)
        YMM4.append(ysm + yoff)

    obs['slitX1'], obs['slitX2'], obs['slitX3'], obs['slitX4'] = XMM1, XMM2, XMM3, XMM4
    obs['slitY1'], obs['slitY2'], obs['slitY3'], obs['slitY4'] = YMM1, YMM2, YMM3, YMM4
    obs['arcslitX1'], obs['arcslitX2'], obs['arcslitX3'], obs['arcslitX4'] = xfp1, xfp2, xfp3, xfp4
    obs['arcslitY1'], obs['arcslitY2'], obs['arcslitY3'], obs['arcslitY4'] = yfp1, yfp2, yfp3, yfp4
    return obs

def mask_coords(obs):
    asec_rad = 206264.80
    FLIP = -1.
    FL_TEL = 150327.0
    outObs=[]

    for ob in obs:
        RELPA = ob['relpa']
        XARCS = ob['xarcsS']
        YARCS = ob['yarcsS']
        # Correct?  -- correct for xarcsS since both are centered on the slit
        LEN1 = ob['length1S']
        LEN2 = ob['length2S']  # Correct?
        SLWID = ob['slitWidth']

        X1 = ob['X1']
        Y1 = ob['Y1']
        X2 = ob['X2']
        Y2 = ob['Y2']

        # offset from telescope axis to slitmask origin, IN SLITMASK COORDS
        #        yoff = ZPT_YM * (1. - np.cos (np.radians(M_ANGLE)))
        yoff = 0.       # XXX check!  Am not sure where the above comes from
        xoff = 0.

        # SLWID = []
        # XMM1, YMM1, XMM2, YMM2, XMM3, YMM3, XMM4, YMM4 = [], [], [], [], [], [], [], []
        # xfp1, yfp1, xfp2, yfp2, xfp3, yfp3, xfp4, yfp4 = [], [], [], [], [], [], [], []

        # SLWID.append(ob['slitWidth'])
#        if obs['pcode'][i]==-2:           ########## <--- alignment box                       <<<----should be done earlier?
#            SLWID.append(4)
#        else:
#            SLWID.append(obs['slitWidth'][i])

# XXX For now, carry through the RELPA thing; in end, must be specified!
        if (RELPA != None):
            cosa = np.cos(RELPA)
            sina = np.sin(RELPA)
        else:
            cosa = 1.
            sina = 0.

# This is a recalculation ... prob not needed
        X1 = XARCS - LEN1 * cosa * FLIP
        Y1 = YARCS - LEN1 * sina
        X2 = XARCS + LEN2 * cosa * FLIP
        Y2 = YARCS + LEN2 * sina


# X1,Y1 are now tan projections already!

        xfp = FL_TEL * X1 / asec_rad
        yfp = FL_TEL * (Y1 - 0.5*SLWID) / asec_rad
        pa = 0.

        xfp1 = X1
        yfp1 = Y1 - 0.5*SLWID

        xfp, yfp = gnom_to_dproj(xfp, yfp)         # (allowed)
        xsm, ysm, pa = proj_to_mask(xfp, yfp, pa)

        XMM1 = xsm + xoff
        YMM1 = ysm + yoff

        xfp = FL_TEL * X2 / asec_rad
        yfp = FL_TEL * (Y2 - 0.5*SLWID) / asec_rad
        pa = 0.

        xfp2 = X2
        yfp2 = Y2 - 0.5*SLWID

        xfp, yfp = gnom_to_dproj(xfp, yfp)         # (allowed)
        xsm, ysm, pa = proj_to_mask(xfp, yfp, pa)

        XMM2 = xsm + xoff
        YMM2 = ysm + yoff

        xfp = FL_TEL * X2 / asec_rad
        yfp = FL_TEL * (Y2 + 0.5*SLWID) / asec_rad
        pa = 0.

        xfp3 = X2
        yfp3 = Y2 + 0.5*SLWID

        xfp, yfp = gnom_to_dproj(xfp, yfp)         # (allowed)
        xsm, ysm, pa = proj_to_mask(xfp, yfp, pa)

        XMM3 = xsm + xoff
        YMM3 = ysm + yoff

        xfp = FL_TEL * X1 / asec_rad
        yfp = FL_TEL * (Y1 + 0.5*SLWID) / asec_rad
        pa = 0.

        xfp4 = X1
        yfp4 = Y1 + 0.5*SLWID

        xfp, yfp = gnom_to_dproj(xfp, yfp)         # (allowed)
        xsm, ysm, pa = proj_to_mask(xfp, yfp, pa)

        XMM4 = xsm + xoff
        YMM4 = ysm + yoff
        ob['slitX1'] = XMM1
        ob['slitX2'] = XMM2
        ob['slitX3'] = XMM3
        ob['slitX4'] = XMM4

        ob['slitY1'] = YMM1
        ob['slitY2'] = YMM2
        ob['slitY3'] = YMM3
        ob['slitY4'] = YMM4

        ob['arcslitX1'] = xfp1
        ob['arcslitX2'] = xfp2
        ob['arcslitX3'] = xfp3
        ob['arcslitX4'] = xfp4

        ob['arcslitY1'] = yfp1
        ob['arcslitY2'] = yfp2
        ob['arcslitY3'] = yfp3
        ob['arcslitY4'] = yfp4
        outObs.append(ob)

    return outObs 

#
# GNOM_TO_DPROJ: adjust gnomonic coords to curved surface, take projection
# onto plane, and apply distortion correction, resulting in distortion-
# adjusted projected coords ready for a vertical projection to slitmask.
# Double inputs, outputs;  outputs may be the same arguments as inputs.
#


def gnom_to_dproj(xg, yg):
    DIST_C0, DIST_C2 = 0.0e-4, -1.111311e-8
    rho = np.sqrt(xg * xg + yg * yg)
    cosa = yg / rho
    sina = xg / rho

# Apply map gnomonic projection --> real telescope
    rho = rho * (1. + DIST_C0 + DIST_C2 * rho * rho)
    xd = rho * sina
    yd = rho * cosa
    return xd, yd

#
# PROJ_TO_MASK: project planar onto curved slitmask coordinates
# Double inputs, outputs
# Note that this is pure geometry -- any empirically determined corrections
# should go elsewhere...
#


def proj_to_mask(xp, yp, ap):

    M_RCURV = 2120.9  # Manually set
    M_ANGLE = 6.00  # Manually set
    ZPT_YM = 128.803
    R_IMSURF = 2133.6
    MASK_HT0 = 2.717
    PPLDIST = 20018.4

    mu = np.arcsin(xp / M_RCURV)
    cosm = np.cos(mu)
    cost = np.cos(np.radians(M_ANGLE))
    tant = np.tan(np.radians(M_ANGLE))
    xx = M_RCURV * mu
    yy = (yp - ZPT_YM) / cost + M_RCURV * tant * (1. - cosm)

    tanpa = np.tan(np.radians(ap)) * cosm / cost + tant * xp / M_RCURV
    ac = np.degrees(np.arctan(tanpa))


# What follows is a small correction for the fact that the mask does
# not lie exactly in the spherical image surface (where the distortion
# values and gnomonic projection are calculated) and the rays are arriving
# from the pupil image; thus, the exact locations are moved _slightly_
# wrt the telescope optical axis.  Note also that these corrections are
# only calculated to first order.

# Spherical image surface height:
    rho = np.sqrt(xp * xp + yp * yp)
    hs = R_IMSURF * (1. - np.sqrt(1. - (rho / R_IMSURF) ** 2))
# Mask surface height:
    hm = MASK_HT0 + yy * np.sin(np.radians(M_ANGLE)) + M_RCURV * (1. - cosm)
# Correction:
    yc = yy + (hs - hm) * yp / PPLDIST / cost
    xc = xx + (hs - hm) * xp / PPLDIST / cosm

    return xc, yc, ac


def gen_obs(fileparams, targetList):
    obs, site = init_dicts(targetList, fileparams)
    obs = refr_coords(obs, site)
    obs = fld2telax(obs, 'ra_fldR', 'dec_fldR', 'ra_telR', 'dec_telR')
    obs = tel_coords(obs, 'raRadR', 'decRadR', 'ra_telR', 'dec_telR')
    min_slit = float(fileparams['MinSlitLength'])
    slit_gap = float(fileparams['MinSlitSeparation'])
    slit = gen_slits_from_obs(obs, min_slit, slit_gap, False, False)
    slit = sky_coords(slit)
    targetListOut = []
    for idx, target in enumerate(targetList):
        target['xarcsS'] = slit[idx]['xarcsS']
        target['yarcsS'] = slit[idx]['yarcsS']
        target['xarcs'] = obs[idx]['xarcs']
        target['yarcs'] = obs[idx]['yarcs']
        targetListOut.append(target)
    return targetListOut

def genSlits(targetList, fileparams, auto_sel=True, returnSlitSite=False):
    logger.debug('genSlits')

    if fileparams['NoOverlap'] == 'yes':
        adj_len = True
    else:
        adj_len = False
    if fileparams['ProjSlitLength'] == 'yes':
        proj_len = True
    else:
        proj_len = False
    obs, site = init_dicts(targetList, fileparams)
    logger.debug('init_dicts')
    obs = refr_coords(obs, site)
    obs = fld2telax(obs, 'ra_fldR', 'dec_fldR', 'ra_telR', 'dec_telR')
    obs = tel_coords(obs, 'raRadR', 'decRadR', 'ra_telR', 'dec_telR', proj_len)
    min_slit = float(fileparams['MinSlitLength'])
    slit_gap = float(fileparams['MinSlitSeparation'])
    slit = gen_slits_from_obs(obs, min_slit, slit_gap, adj_len, auto_sel)
    slit = sky_coords(slit)
    slit = unrefr_coords(slit, site)
    slit = fld2telax(slit, 'ra0_fldU', 'dec0_fldU', 'ra_telU', 'dec_telU')
    slit = tel_coords(slit, 'raRadU', 'decRadU', 'ra_telU', 'dec_telU', proj_len)
    slit = mask_coords(slit)

    outTargetList = []
    slitKeys = [ 'slitWidth', 'selected',
                'xarcsS', 'yarcsS',
                'xarcs', 'yarcs', 
                'length1S', 'length2S',
                'rlength1', 'rlength2', 
                'slitX1', 'slitX2', 'slitX3', 'slitX4',
                'slitY1', 'slitY2', 'slitY3', 'slitY4',
                'arcslitX1', 'arcslitX2', 'arcslitX3', 'arcslitX4',
                'newcenterRADeg', 'newcenterDECDeg',
                'arcslitY1', 'arcslitY2', 'arcslitY3', 'arcslitY4']
    obsKeys = ['xarcs', 'yarcs', 'objectId', 'length1',
               'length2', 'ra_fldR', 'dec_fldR', 'lst']
    outTargetList = combine_target_with_slit_and_obs(targetList, slit, obs, slitKeys, obsKeys)

    out = [outTargetList , slit, site] if returnSlitSite else outTargetList 

    return out 

def combine_target_with_slit_and_obs(targetList, slit, obs, slitKeys, obsKeys):
    outTargetList = []
    for idx, target in enumerate(targetList):
        tgt = target.copy()
        tgt = {**tgt, **{ k: slit[idx][k] for k in slitKeys }}
        tgt = {**tgt, **{ k: obs[idx][k] for k in obsKeys}}
        outTargetList.append(tgt)
    return outTargetList

def gen_mask_out(targetList, fileparams):

    targetList, slits, site = genSlits(targetList, fileparams, auto_sel=False, returnSlitSite=True)
    df = pd.DataFrame(targetList)


    tel = df[['newcenterRADeg', 'newcenterDECDeg', 'lst' ]] 
    tel.loc[:, 'dateobs'] = fileparams['ObsDate']
    #tel = {k: ([v] if type(v) != list else v) for (k, v) in tel.items()}

    params = {
        'objfile': '',  # Pass separately?
        'output': fileparams['OutputFits']+'.out',
        'mdf': fileparams['OutputFits'],
        'plotfile': '',
        'ra0': (15*utils.sexg2Float(fileparams['InputRA'])),
        'dec0': (utils.sexg2Float(fileparams['InputDEC'])),
        'pa0': float(fileparams['MaskPA']),
        'equinox': 2000.0,
        'ha0': float(fileparams['HourAngle']),
        'min_slit': float(fileparams['MinSlitLength']),
        'sep_slit': float(fileparams['MinSlitSeparation']),
        'slit_width': float(fileparams['SlitWidth']),
        'box_sz': float(fileparams['AlignBoxSize']),
        'blue': float(fileparams['BlueWaveLength']),
        'red': float(fileparams['RedWaveLength']),
        'proj_len': False,
        'no_overlap': False,
        #    'std_format':True,     #Remove this option
        'lambda_cen': float(fileparams['CenterWaveLength']),
        'temp': float(fileparams['Temperature']),
        'pressure': float(fileparams['Pressure']),
        'maskid': fileparams['MaskId'],
        'guiname': fileparams['MaskName'],
        'dateobs': fileparams['ObsDate'],
        'author': fileparams['Author'],
        'observer': fileparams['Observer'],
        'project': fileparams['ProjectName'],
        'instrument': 'DEIMOS',
        'telescope': 'Keck II'
    }

    params['descreate'] = '2022-12-01T01:00:00'

    site = {k: ([v] if type(v) != list else v) for (k, v) in site.items()}
    params = {k: ([v] if type(v) != list else v)
              for (k, v) in params.items()}  # <-----fix this for correct outputs

    slitsdf = pd.DataFrame(slits)
    slitsdf = slitsdf[(slitsdf['selected'] == 1) & (slitsdf['inMask'] == 1)]
    slitsdf.reset_index(drop=True, inplace=True)
    assert slitsdf.shape[0] > 0, 'No slits selected for mask'

    paramdf = pd.DataFrame(params)
    sitedf = pd.DataFrame(site)
    teldf = pd.DataFrame(tel)

    mdf = MaskDesignOutputFitsFile(slitsdf, sitedf, paramdf, teldf)

    return mdf, df.to_dict(orient='records')
