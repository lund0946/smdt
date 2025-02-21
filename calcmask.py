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
import datetime

from astropy import units as u
from astropy.coordinates import Angle

import pickle

import sl
import maskLayouts
import utils
import dsimselector

import pdb






def init_dicts(data,params):
    #params {'ProjectNamefd': ['New Mask'], 'OutputFitsfd': ['mask.fits'], 'Telescopefd': ['Keck II'], 'Instrumentfd': ['DEIMOS'], 'ObsDatefd': ['2022-08-31 00:00:00'], 'Authorfd': ['Keck Observatory'], 'Observerfd': ['Observer Name'], 'MaskIdfd': ['123456789'], 'MaskNamefd': ['Mask Name'], 'MinSlitLengthfd': ['5.0'], 'MinSlitSeparationfd': ['0.35'], 'SlitWidthfd': ['1.00'], 'AlignBoxSizefd': ['4.0'], 'BlueWaveLengthfd': ['3200'], 'RedWaveLengthfd': ['3200'], 'ReferenceWaveLengthfd': ['3200'], 'CenterWaveLengthfd': ['3200'], 'ProjSlitLengthfd': ['yes'], 'NoOverlapfd': ['yes'], 'Temperaturefd': ['0.0'], 'Pressurefd': ['615.0'], 'MaskPAfd': ['0.0'], 'SlitPAfd': ['0.0'], 'InputRAfd': ['00:00:00'], 'InputDECfd': ['00:00:00'], 'MaskMarginfd': ['4'], 'HourAnglefd': ['0.001'], 'Extrafd': ['Extra'], 'mouseAction': ['on'], 'showSel': ['on']}



    ra=data.loc[:,'raHour'].tolist()
    dec=data.loc[:,'decDeg'].tolist()
    mag=data.loc[:,'mag'].tolist()
    magband=data.loc[:,'pBand'].tolist()
    pcode=data.loc[:,'pcode'].tolist()
    sel=data.loc[:,'selected'].tolist()
    slit_pa=data.loc[:,'slitLPA'].tolist()
    objectId=data.loc[:,'objectId'].tolist()


    ####      <---------  Needs an if since it's an optional parameter?
    dlength1=data.loc[:,'length1'].tolist()
    dlength2=data.loc[:,'length2'].tolist()

    ####

    try:
        slit_pa=data.loc[:,'slitLPA'].tolist()
        tilt=True
    except:
        tilt=False
    raDeg,decDeg=[],[]
    slitpa=[]
    _pcode=[]
    _mag,_magband=[],[]
    ra=Angle(ra,unit=u.hour)
    dec=Angle(dec,unit=u.deg)
    for i in range(len(ra)):
        if tilt==True:
            slitpa.append(slit_pa[i])
        else:
            slitpa.append(-9999)
        raDeg.append(ra[i].degree)
        decDeg.append(dec[i].degree)


    centerRADeg=utils.sexg2Float(params['InputRAfd'][0])*15   ####### Check sexagesimal conversion
    centerDECDeg=utils.sexg2Float(params['InputDECfd'][0])



    haDeg=float(params['HourAnglefd'][0])
    positionAngle=float(params['MaskPAfd'][0])
    len1=float(params['MinSlitLengthfd'][0])/2
    len2=float(params['MinSlitLengthfd'][0])/2


    ra0_fld=np.radians(centerRADeg)
    dec0_fld=np.radians(centerDECDeg)
    ha0_fld=np.radians(15*haDeg)
    slitpa=np.radians(slitpa)
    raRad=np.radians(raDeg)
    decRad=np.radians(decDeg)
    lst = ra0_fld + ha0_fld
    pa0_fld=np.radians(positionAngle)

    length1,length2=[],[]
    rlength1,rlength2=[],[]

    slitLPA=[]
    slitWidth=[]
    for i in range(len(raRad)): ### Manual Hacks
        slitLPA.append(slitpa[i])
        if pcode[i]!=-2:
            slitWidth.append(float(params['SlitWidthfd'][0]))    #### Set manually later???  #### <<<<------------
##            length1.append(len1)  ### slitlength manual
##            length2.append(len2)
            length1.append(dlength1[i])
            length2.append(dlength2[i])
            rlength1.append(dlength1[i])
            rlength2.append(dlength2[i])
            slitLPA.append(slitpa[i])
        else:
            slitWidth.append(float(params['AlignBoxSizefd'][0]))
            length1.append(float(params['AlignBoxSizefd'][0])*0.5)  ### slitlength manual
            length2.append(float(params['AlignBoxSizefd'][0])*0.5)
            rlength1.append(float(params['AlignBoxSizefd'][0])*0.5)  ### slitlength manual
            rlength2.append(float(params['AlignBoxSizefd'][0])*0.5)
            slitLPA.append(0)

    obs_lat= 19.8
    obs_alt = 4150.
    mm_arcs = 0.7253
    waver=float(params['CenterWaveLengthfd'][0])
    wavemn=float(params['BlueWaveLengthfd'][0])
    wavemx=float(params['RedWaveLengthfd'][0])
    pres=float(params['Pressurefd'][0])
    temp=float(params['Temperaturefd'][0])
    obs_rh=0.4                                               ######### <--------- Add to webpage params!


    lat = np.radians(obs_lat)        # radians
    htm = obs_alt                   # meters
    tdk = temp + 273.15      # temp in K
    pmb = pres               # millibars
    rel_h20 = obs_rh                # relative humidity
    w = waver/10000. ##reference wavelength conv. to micron

    obs={'objectId':objectId,'ra0_fld':ra0_fld,'dec0_fld':dec0_fld,'ha0_fld':ha0_fld,'raRad':raRad,'decRad':decRad,'lst':lst,'pa0_fld':pa0_fld,'length1':length1,'length2':length2,'rlength1':rlength1,'rlength2':rlength2,'slitLPA':slitLPA,'pcode':pcode,'slitWidth':slitWidth,'slitpa':slitpa,'mag':mag,'magband':magband,'sel':sel}
    site={'lat':lat,'htm':htm,'tdk':tdk,'pmb':pmb,'rel_h20':rel_h20,'w':w,'wavemn':wavemn,'wavemx':wavemx}

    return obs,site


def refr_coords(obs,site):

    # Get the refraction coeffs (2 hardcodes suggested in SLALIB):
    r1,r3=sl.slrfco (site['htm'], site['tdk'], site['pmb'], site['rel_h20'], site['w'], site['lat'], 0.0065, 1.e-10)

    # Save the refraction coeffs for later use:
    obs['orig_ref1'] = r1
    obs['orig_ref3'] = r3


# Apply to field center
    az,el=sl.slde2h (obs['ha0_fld'], obs['dec0_fld'], site['lat'])
    zd0 = np.pi/2. - el
    zd=sl.slrefz (zd0, r1, r3)
    elr = np.pi/2. - zd
    har,dec_fld=sl.sldh2e (az, elr, site['lat'])
    ra_fld = obs['lst'] - har

# Now work out atmospheric dispersion:
    zd=sl.slrefz (zd0, r1, r3)
    w1 = site['wavemn']/10000. #conv to micron
    w2 = site['wavemx']/10000. #conv to micron
    a,b=sl.slatmd (site['tdk'], site['pmb'], site['rel_h20'], site['w'], r1, r3, w1)
    zd1=sl.slrefz (zd0, a, b)
    a,b=sl.slatmd (site['tdk'], site['pmb'], site['rel_h20'], site['w'], r1, r3, w2)
    zd2=sl.slrefz (zd0, a, b)
    AD1 = (zd1 - zd) * 206205.
    AD2 = (zd2 - zd) * 206205.
# ... and paralactic angle and airmass
    par_ang = sl.slpa (har, dec_fld, site['lat'])
    amass = sl.slarms (zd)

# Loop and apply to targets:
    raRadR,decRadR=[],[]
    for i in range(len(obs['raRad'])):
        ha = obs['lst'] - obs['raRad'][i]
        az,el=sl.slde2h (ha, obs['decRad'][i], site['lat'])
        zd0 = np.pi/2. - el
        zd=sl.slrefz (zd0, r1, r3)
        elr = np.pi/2. - zd

        har,_dec=sl.sldh2e (az, elr, site['lat'])
        _ra = obs['lst'] - har
        raRadR.append(_ra)
        decRadR.append(_dec)

    obs['raRadR']=raRadR
    obs['decRadR']=decRadR
    obs['ra_fldR']=ra_fld
    obs['dec_fldR']=dec_fld

    return obs


def fld2telax(obs,ra_fld,dec_fld,ratel,dectel):
# FLD2TELAX:  from field center and rotator PA, calc coords of telescope axis

    ra_fld=obs[ra_fld]
    dec_fld=obs[dec_fld]

    FLDCEN_X=0.
    FLDCEN_Y=270.
    PA_ROT=obs['pa0_fld']

# convert field center offset (arcsec) to radians
    r = np.radians(np.sqrt (FLDCEN_X*FLDCEN_X + FLDCEN_Y*FLDCEN_Y) / 3600.)

# get PA of field center
    pa_fld = np.arctan2 (FLDCEN_Y, FLDCEN_X)

    cosr = np.cos (r)
    sinr = np.sin (r)
    cosd = np.cos (dec_fld)
    sind = np.sin (dec_fld)

    cost = np.cos (PA_ROT - pa_fld)
    sint = np.sin (PA_ROT - pa_fld)

    sina = sinr * sint / cosd               # ASSUME not at dec=90
    cosa = np.sqrt (1. - sina*sina)

    ra_tel = ra_fld - np.arcsin (sina)
    dec_tel = np.arcsin ((sind*cosd*cosa - cosr*sinr*cost) /
                            (cosr*cosd*cosa - sinr*sind*cost))
    obs[ratel]=ra_tel
    obs[dectel]=dec_tel
    return obs



def tel_coords(obs,ra_ref,dec_ref,ra_telref,dec_telref,proj_len=False):
    xarcs,yarcs=[],[]
    X1,Y1,X2,Y2=[],[],[],[]
    relpa=[]
    flip=-1


    ra0=obs[ra_telref]
    dec0=obs[dec_telref]
    pa0=obs['pa0_fld']               ##PA_ROT better be in radians <-- should be pa_rot??  I think this needs to clearly be PA_ROT
    ra=obs[ra_ref]
    dec=obs[dec_ref]
    length1=obs['length1']
    length2=obs['length2']

    for i in range(len(ra)):

        dec_obj = dec[i]
        del_ra = ra[i] - ra0

        cosr = np.sin (dec_obj) * np.sin (dec0) + np.cos (dec_obj) * np.cos (dec0) * np.cos (del_ra)
        r = np.arccos (cosr)
        sinp = np.cos (dec_obj) * np.sin (del_ra) / np.sqrt (1. - cosr*cosr)
        cosp = np.sqrt (np.max ([(1. - sinp*sinp), 0.]))
        if (dec_obj < dec0):
            cosp = -cosp
        p = np.arctan2 (sinp, cosp)

#convert radii to arcsec
#convert r to tan(r) to get tan projection

        r = np.tan(r) * 206264.8
        _xarcs = r * np.cos (pa0 - p)
        _yarcs = r * np.sin (pa0 - p)
        xarcs.append(_xarcs)
        yarcs.append(_yarcs)

        if obs['pcode'][i]==-2:
            obs['slitpa'][i]=-9999


        if obs['slitpa'][i]==-9999:   ##No individual slit angles
            relpa.append(None)
            rangle = 0.                #90 not zero??
        else:
            _relpa= obs['slitpa'][i] - pa0  ###check that slitLPA is available
            relpa.append(_relpa)
            rangle = _relpa

# For simplicity, we calculate the endpoints in X here; note use of FLIP

        xgeom = (flip) * np.cos (rangle)
        ygeom = np.sin (rangle)
        if (proj_len == True):
            xgeom = xgeom / np.abs (np.cos (rangle))
            ygeom = ygeom / np.abs (np.cos (rangle))

# We always want X1 < X2, so:
        if (xgeom > 0):
            _X1 = xarcs[i] - length1[i] * xgeom
            _Y1 = yarcs[i] - length1[i] * ygeom
            _X2 = xarcs[i] + length2[i] * xgeom
            _Y2 = yarcs[i] + length2[i] * ygeom

        else:
            _X2 = xarcs[i] - length1[i] * xgeom
            _Y2 = yarcs[i] - length1[i] * ygeom
            _X1 = xarcs[i] + length2[i] * xgeom
            _Y1 = yarcs[i] + length2[i] * ygeom

        X1.append(_X1)
        X2.append(_X2)
        Y1.append(_Y1)
        Y2.append(_Y2)

    obs['X1'],obs['X2'],obs['Y1'],obs['Y2']=X1,X2,Y1,Y2

    obs['xarcs'],obs['yarcs']=xarcs,yarcs
    obs['relpa']=relpa


    return obs


def gen_slits(obs,adj_len=False,auto_sel=True,min_slit=10,slit_gap=0.35):



    CODE_GS=-1 #code for guidestars
    n_targs=len(obs['raRadR'])
    ndx = 0
    _PA,_RELPA,_PCODE,_X1,_Y1,_X2,_Y2,_XARCS,_YARCS,_SLWID,_SLNDX=[],[],[],[],[],[],[],[],[],[],[]
    _sel=[]
    _ndx=[]
    for i in range(n_targs):
        if True:#(obs[SEL[i] !=0):     # or != 0
#            _sel.append(obs['sel'][i])            #until selection is implemented #########
            x = obs['xarcs'][i]       # unclear TY of XYARCS
            y = obs['yarcs'][i]

            if obs['pcode'][i]==-2:   #If PCODE=-2, set slitpa to -9999
                obs['slitpa'][i] == -9999

            _ndx.append(ndx)
            if (obs['slitpa'][i] == -9999):   ### Never none?
                _PA.append(obs['pa0_fld'])
                _RELPA.append(None)
            else:
                _PA.append(obs['slitpa'][i])
                _RELPA.append(obs['relpa'][i])
            _PCODE.append(obs['pcode'][i])

            _X1.append(obs['X1'][i])
            _Y1.append(obs['Y1'][i])
            _X2.append(obs['X2'][i])
            _Y2.append(obs['Y2'][i])

# XXX NB: until the final sky_coords are calc'd, want X/YARCS to repr. objects

            _XARCS.append(obs['xarcs'][i])
            _YARCS.append(obs['yarcs'][i])

# XXX cuidado!  I am not sure that the tan-projection of the rel PA is the
# same as the rel PA -- MUST CHECK!

#            _SLWID.append(obs['slitWidth'][0]) #Not needed?

# This is where we also assign slit index to object
            _SLNDX.append(ndx)
            ndx = ndx + 1
    nslit = ndx
    obs["index"]=_ndx
    obs["slitLPA"]=_PA
    obs["relpa"]=_RELPA
    obs["pcode"]=_PCODE
    obs["X1"]=_X1
    obs["Y1"]=_Y1
    obs["X2"]=_X2
    obs["Y2"]=_Y2
    obs["xarcs"]=_XARCS
    obs["yarcs"]=_YARCS
#    obs["slitWidth"]=_SLWID      # not needed?
    obs["slitIndex"]=_SLNDX
 #   obs["sel"]=_sel


#    print('\n\n\n\n\n\n\n\ =================')
#    if auto_sel:
    obs=dsimselector.from_dict(obs,auto_sel,min_slit,slit_gap)

    if adj_len:
        import gslit
        obs=gslit.len_slits(obs,min_slit,slit_gap)
    return obs
def sky_coords(obs):

    ra,dec=[],[]
    xarcs,yarcs=[],[]
    len1,len2=[],[]
    rlen1,rlen2=[],[]

    x1=obs['X1']
    x2=obs['X2']
    y1=obs['Y1']
    y2=obs['Y2']


    ra0=obs['ra_telR']
    dec0=obs['dec_telR']
    pa0=obs['pa0_fld']

    for i in range(len(x1)):

        x = 0.5 * (x1[i] + x2[i])
        y = 0.5 * (y1[i] + y2[i])

        r = np.sqrt (x*x + y*y)
        r = np.arctan (r/206264.8)

        phi = pa0 - np.arctan2 (y, x)        # WORK

        sind = np.sin(dec0) * np.cos(r) + np.cos(dec0) * np.sin(r) * np.cos(phi)

        sina = np.sin(r) * np.sin(phi) / np.sqrt(1. - sind*sind)

        _dec = np.arcsin(sind)
        _ra = ra0 + np.arcsin(sina)

        dec.append(_dec)
        ra.append(_ra)

# PA = already assigned    <------ check if true with new list
# calc the centers and lengths of the slits

        _xarcs = 0.5 * (x1[i] + x2[i])
        _yarcs = 0.5 * (y1[i] + y2[i])
        xarcs.append(_xarcs)
        yarcs.append(_yarcs)

# XXX NB: by convention, slit length will be defined as TOTAL length

        x = x2[i] - x1[i]
        y = y2[i] - y1[i]

        _len1 = 0.5 * np.sqrt (x*x + y*y)
        len1.append(_len1)
        len2.append(_len1)

# Slit length on either side of target

        xl2 = x2[i] - obs['xarcs'][i]
        yl2 = y2[i] - obs['yarcs'][i]
        xl1 = obs['xarcs'][i] - x1[i]
        yl1 = obs['yarcs'][i] - y1[i]
        _rlen1 = np.sqrt (xl1*xl1 + yl1*yl1)
        _rlen2 = np.sqrt (xl2*xl2 + yl2*yl2)

        rlen1.append(_rlen1)
        rlen2.append(_rlen2)

    obs['xarcsS']=xarcs
    obs['yarcsS']=yarcs

    obs['length1S']=len1
    obs['length2S']=len2

    obs['rlength1']=rlen1
    obs['rlength2']=rlen2


    obs['raRadS']=ra
    obs['decRadS']=dec

    return obs


##UNREFR_COORDS
def unrefr_coords(obs,site):

    ra0,dec0=[],[]

    raRad=obs['raRadS']
    decRad=obs['decRadS']
    ha_fld=obs['ha0_fld']
    lst = obs['ra0_fld'] + ha_fld     # XXX Verify correct/see above
    lat = site['lat']                 # radians

# Apply to field center
    ha = lst - obs['ra_fldR']        ## XXX Clean up (see above) This is refracted ha. already saved
    az,el=sl.slde2h (ha, obs['dec_fldR'], lat)
    zd = np.pi/2. - el
    tanz = np.tan (zd)
    zd = zd + obs['orig_ref1'] * tanz + obs['orig_ref3'] * tanz**3
    el = np.pi/2. - zd
    ha0, dec0_fld= sl.sldh2e (az, el, lat)
    ra0_fld = lst - ha0

    obs['ra0_fldU']=ra0_fld
    obs['dec0_fldU']=dec0_fld



    obs['newcenterRADeg']=np.degrees(ra0_fld)
    obs['newcenterDECDeg']=np.degrees(dec0_fld)

# Loop and apply to targets:
    for i in range(len(raRad)):
        ha = lst - raRad[i]
        az,el=sl.slde2h (ha, decRad[i], lat)

        zd = np.pi/2. - el
        tanz = np.tan (zd)
        zd = zd + obs['orig_ref1'] * tanz + obs['orig_ref3'] * tanz**3
        el = np.pi/2. - zd

        ha0,_dec0=sl.sldh2e (az, el, lat)
        _ra0 = lst - ha0
        ra0.append(_ra0)
        dec0.append(_dec0)


    obs['raRadU']=ra0
    obs['decRadU']=dec0

    return obs


def mask_coords(obs):
    asec_rad = 206264.80
    FLIP=-1.
    RELPA=obs['relpa']
    XARCS=obs['xarcsS']
    YARCS=obs['yarcsS']
    LEN1=obs['length1S']  ##Correct?  -- correct for xarcsS since both are centered on the slit
    LEN2=obs['length2S']  ##Correct?
    FL_TEL=150327.0

    X1=obs['X1']
    Y1=obs['Y1']
    X2=obs['X2']
    Y2=obs['Y2']



# offset from telescope axis to slitmask origin, IN SLITMASK COORDS
#        yoff = ZPT_YM * (1. - np.cos (np.radians(M_ANGLE)))
    yoff = 0.       # XXX check!  Am not sure where the above comes from
    xoff = 0.

    SLWID=[]
    XMM1,YMM1,XMM2,YMM2,XMM3,YMM3,XMM4,YMM4=[],[],[],[],[],[],[],[]
    xfp1,yfp1,xfp2,yfp2,xfp3,yfp3,xfp4,yfp4=[],[],[],[],[],[],[],[]
    for i in range(len(RELPA)):

        SLWID.append(obs['slitWidth'][i])
#        if obs['pcode'][i]==-2:           ########## <--- alignment box                       <<<----should be done earlier?
#            SLWID.append(4)
#        else:
#            SLWID.append(obs['slitWidth'][i])

# XXX For now, carry through the RELPA thing; in end, must be specified!
        if (RELPA[i] != None):
            cosa = np.cos (RELPA[i])
            sina = np.sin (RELPA[i])
        else:
            cosa = 1.
            sina = 0.

# This is a recalculation ... prob not needed
        X1[i] = XARCS[i] - LEN1[i] * cosa * FLIP
        Y1[i] = YARCS[i] - LEN1[i] * sina
        X2[i] = XARCS[i] + LEN2[i] * cosa * FLIP
        Y2[i] = YARCS[i] + LEN2[i] * sina


# X1,Y1 are now tan projections already!

        xfp = FL_TEL *  X1[i] / asec_rad
        yfp = FL_TEL * (Y1[i] - 0.5*SLWID[i]) / asec_rad
        pa = 0.

        xfp1.append(X1[i])
        yfp1.append(Y1[i] - 0.5*SLWID[i])

        xfp,yfp=gnom_to_dproj (xfp, yfp)         # (allowed)
        xsm,ysm,pa=proj_to_mask (xfp, yfp, pa)

        XMM1.append(xsm + xoff)
        YMM1.append(ysm + yoff)

        xfp = FL_TEL *  X2[i] / asec_rad
        yfp = FL_TEL * (Y2[i] - 0.5*SLWID[i]) / asec_rad
        pa = 0.

        xfp2.append(X2[i])
        yfp2.append(Y2[i] - 0.5*SLWID[i])

        xfp,yfp=gnom_to_dproj (xfp, yfp)         # (allowed)
        xsm,ysm,pa=proj_to_mask (xfp, yfp, pa)

        XMM2.append(xsm + xoff)
        YMM2.append(ysm + yoff)

        xfp = FL_TEL *  X2[i] / asec_rad
        yfp = FL_TEL * (Y2[i] + 0.5*SLWID[i]) / asec_rad
        pa = 0.

        xfp3.append(X2[i])
        yfp3.append(Y2[i] + 0.5*SLWID[i])

        xfp,yfp=gnom_to_dproj (xfp, yfp)         # (allowed)
        xsm,ysm,pa=proj_to_mask (xfp, yfp, pa)

        XMM3.append(xsm + xoff)
        YMM3.append(ysm + yoff)

        xfp = FL_TEL *  X1[i] / asec_rad
        yfp = FL_TEL * (Y1[i] + 0.5*SLWID[i]) / asec_rad
        pa = 0.

        xfp4.append(X1[i])
        yfp4.append(Y1[i] + 0.5*SLWID[i])

        xfp,yfp=gnom_to_dproj (xfp, yfp)         # (allowed)
        xsm,ysm,pa=proj_to_mask (xfp, yfp, pa)

        XMM4.append(xsm + xoff)
        YMM4.append(ysm + yoff)

    obs['slitX1'],obs['slitX2'],obs['slitX3'],obs['slitX4']=XMM1,XMM2,XMM3,XMM4
    obs['slitY1'],obs['slitY2'],obs['slitY3'],obs['slitY4']=YMM1,YMM2,YMM3,YMM4
    obs['arcslitX1'],obs['arcslitX2'],obs['arcslitX3'],obs['arcslitX4']=xfp1,xfp2,xfp3,xfp4
    obs['arcslitY1'],obs['arcslitY2'],obs['arcslitY3'],obs['arcslitY4']=yfp1,yfp2,yfp3,yfp4
    return obs

#
# GNOM_TO_DPROJ: adjust gnomonic coords to curved surface, take projection
# onto plane, and apply distortion correction, resulting in distortion-
# adjusted projected coords ready for a vertical projection to slitmask.
# Double inputs, outputs;  outputs may be the same arguments as inputs.
#


def gnom_to_dproj(xg,yg):
    DIST_C0,DIST_C2=0.0e-4,-1.111311e-8
    rho= np.sqrt (xg * xg + yg * yg)
    cosa = yg / rho
    sina = xg / rho

# Apply map gnomonic projection --> real telescope
    rho = rho * (1. + DIST_C0 + DIST_C2 * rho * rho)
    xd = rho * sina
    yd = rho * cosa
    return xd,yd

#
# PROJ_TO_MASK: project planar onto curved slitmask coordinates
# Double inputs, outputs
# Note that this is pure geometry -- any empirically determined corrections
# should go elsewhere...
#

def proj_to_mask(xp,yp,ap):


    M_RCURV=2120.9    ##################### Manually set
    M_ANGLE=6.00  ######################## Manually set
    ZPT_YM=128.803
    R_IMSURF=2133.6
    MASK_HT0=2.717   ########
    PPLDIST=20018.4

    mu = np.arcsin (xp / M_RCURV)
    cosm = np.cos (mu)
    cost = np.cos (np.radians(M_ANGLE))
    tant = np.tan (np.radians(M_ANGLE))
    xx =  M_RCURV * mu
    yy =  (yp - ZPT_YM) / cost + M_RCURV * tant * (1. - cosm)

    tanpa = np.tan (np.radians(ap)) * cosm / cost + tant * xp / M_RCURV
    ac = np.degrees(np.arctan (tanpa))




# What follows is a small correction for the fact that the mask does
# not lie exactly in the spherical image surface (where the distortion
# values and gnomonic projection are calculated) and the rays are arriving
# from the pupil image; thus, the exact locations are moved _slightly_
# wrt the telescope optical axis.  Note also that these corrections are
# only calculated to first order.

# Spherical image surface height:
    rho = np.sqrt (xp * xp + yp * yp)
    hs = R_IMSURF * (1. - np.sqrt (1. - (rho / R_IMSURF) ** 2))
# Mask surface height:
    hm = MASK_HT0 + yy * np.sin (np.radians(M_ANGLE)) + M_RCURV * (1. - cosm)
# Correction:
    yc = yy + (hs - hm) * yp / PPLDIST / cost
    xc = xx + (hs - hm) * xp / PPLDIST / cosm


    return xc,yc,ac


















def genObs(df,fileparams):
    min_slit,slit_gap=float(fileparams['MinSlitLengthfd'][0]),float(fileparams['MinSlitSeparationfd'][0])
    obs,site=init_dicts(df,fileparams)
    obs=refr_coords(obs,site)
    obs=fld2telax(obs,'ra_fldR','dec_fldR','ra_telR','dec_telR')
    obs=tel_coords(obs,'raRadR','decRadR','ra_telR','dec_telR')
    slit=gen_slits(obs,False,False,min_slit,slit_gap)
    slit=sky_coords(slit)
    df['xarcsS']=slit['xarcsS']
    df['yarcsS']=slit['yarcsS']
    df['xarcs']=obs['xarcs']
    df['yarcs']=obs['yarcs']
    df['objectId']=obs['objectId']
    f=open('gen_obs.pkl','wb')
    pickle.dump([obs,site,slit,df],f)
    f.close()
    return df

def genSlits(df,fileparams,auto_sel=True):
#    print('genSlits\n\n\n\n\n\n\n\n\n')

    global slit
    global site
    min_slit,slit_gap=float(fileparams['MinSlitLengthfd'][0]),float(fileparams['MinSlitSeparationfd'][0])

    if fileparams['NoOverlapfd'][0]=='yes':
        adj_len=True
    else:
        adj_len=False
    if fileparams['ProjSlitLengthfd'][0]=='yes':
        proj_len=True
    else:
        proj_len=False
    obs,site=init_dicts(df,fileparams)
#    print('init_dicts')
    obs=refr_coords(obs,site)
    obs=fld2telax(obs,'ra_fldR','dec_fldR','ra_telR','dec_telR')
    obs=tel_coords(obs,'raRadR','decRadR','ra_telR','dec_telR',proj_len)
    slit=gen_slits(obs,adj_len,auto_sel,min_slit,slit_gap)
    slit=sky_coords(slit)
    slit=unrefr_coords(slit,site)
    slit=fld2telax(slit,'ra0_fldU','dec0_fldU','ra_telU','dec_telU')
    slit=tel_coords(slit,'raRadU','decRadU','ra_telU','dec_telU',proj_len)
    slit=mask_coords(slit)

    df['slitWidth']=slit['slitWidth']

    df['xarcsS']=slit['xarcsS']
    df['yarcsS']=slit['yarcsS']
    df['xarcs']=obs['xarcs']
    df['yarcs']=obs['yarcs']
    df['selected']=slit['sel']
    df['length1']=obs['length1']
    df['length2']=obs['length2']
    df['length1S']=slit['length1S']
    df['length2S']=slit['length2S']
    df['rlength1']=slit['rlength1']
    df['rlength2']=slit['rlength2']

    df['slitX1'],df['slitX2'],df['slitX3'],df['slitX4']=slit['slitX1'],slit['slitX2'],slit['slitX3'],slit['slitX4']
    df['slitY1'],df['slitY2'],df['slitY3'],df['slitY4']=slit['slitY1'],slit['slitY2'],slit['slitY3'],slit['slitY4']
    df['arcslitX1'],df['arcslitX2'],df['arcslitX3'],df['arcslitX4']=slit['arcslitX1'],slit['arcslitX2'],slit['arcslitX3'],slit['arcslitX4']
    df['arcslitY1'],df['arcslitY2'],df['arcslitY3'],df['arcslitY4']=slit['arcslitY1'],slit['arcslitY2'],slit['arcslitY3'],slit['arcslitY4']
#    df['slitX1'],df['slitX2'],df['slitX3'],df['slitX4']=slit['X1'],slit['X1'],slit['X2'],slit['X2']
#    df['slitY1'],df['slitY2'],df['slitY3'],df['slitY4']=slit['Y1'],slit['Y2'],slit['Y2'],slit['Y1']
    df['objectId']=obs['objectId']
    return df

def genMaskOut(df,fileparams):

    global slit
    global site
    min_slit,slit_gap=float(fileparams['MinSlitLengthfd'][0]),float(fileparams['MinSlitSeparationfd'][0])

    if 'slitX1' not in df.columns:    #rethink this?!
        if fileparams['NoOverlapfd'][0]=='yes':
            adj_len=True
        else:
            adj_len=False
        if fileparams['ProjSlitLengthfd'][0]=='yes':
            proj_len=True
        else:
            proj_len=False
        df=df.loc[df['selected']==1]
        obs,site=init_dicts(df,fileparams)
        obs=refr_coords(obs,site)
        obs=fld2telax(obs,'ra_fldR','dec_fldR','ra_telR','dec_telR')
        obs=tel_coords(obs,'raRadR','decRadR','ra_telR','dec_telR',proj_len)
        slit=gen_slits(obs,adj_len,True,min_slit,slit_gap)
        slit=sky_coords(slit)
        slit=unrefr_coords(slit,site)
        slit=fld2telax(slit,'ra0_fldU','dec0_fldU','ra_telU','dec_telU')
        slit=tel_coords(slit,'raRadU','decRadU','ra_telU','dec_telU',proj_len)
        slit=mask_coords(slit)

        df['slitX1'],df['slitX2'],df['slitX3'],df['slitX4']=slit['slitX1'],slit['slitX2'],slit['slitX3'],slit['slitX4']
        df['slitY1'],df['slitY2'],df['slitY3'],df['slitY4']=slit['slitY1'],slit['slitY2'],slit['slitY3'],slit['slitY4']
        df['arcslitX1'],df['arcslitX2'],df['arcslitX3'],df['arcslitX4']=slit['arcslitX1'],slit['arcslitX2'],slit['arcslitX3'],slit['arcslitX4']
        df['arcslitY1'],df['arcslitY2'],df['arcslitY3'],df['arcslitY4']=slit['arcslitY1'],slit['arcslitY2'],slit['arcslitY3'],slit['arcslitY4']

        df['slitWidth']=slit['slitWidth'] ##????? This too?

        df['xarcsS']=slit['xarcsS']
        df['yarcsS']=slit['yarcsS']
        df['xarcs']=obs['xarcs']
        df['yarcs']=obs['yarcs']
#        df['xarcs']=slit['xarcs']
#        df['yarcs']=slit['yarcs']
        df['ra_fldR']=obs['ra_fldR']
        df['dec_fldR']=obs['dec_fldR']
        df['selected']=slit['sel']
#        df['length2']=slit['length2S']
        df['length1']=obs['length1']
        df['length2']=obs['length2']
        df['length1S']=slit['length1S']
        df['length2S']=slit['length2S']
        df['rlength1']=slit['rlength1'] #not needed?
        df['rlength2']=slit['rlength2'] #not needed?
        df['objectId']=obs['objectId']

    tel={}
    tel['newcenterRADeg']=slit['newcenterRADeg']
    tel['newcenterDECDeg']=slit['newcenterDECDeg']
    tel['dateobs']=fileparams['ObsDatefd']
    tel['lst']=slit['lst']
    tel['ra_telR']=slit['ra_telR']
    tel['dec_telR']=slit['dec_telR']

    params={
        'objfile':'',      #Pass separately?
        'output':fileparams['OutputFitsfd'][0]+'.out',
        'mdf':fileparams['OutputFitsfd'][0],
        'plotfile':'',
        'ra0':(15*utils.sexg2Float(fileparams['InputRAfd'][0])),
        'dec0':(utils.sexg2Float(fileparams['InputDECfd'][0])),
        'pa0':float(fileparams['MaskPAfd'][0]),
        'equinox':2000.0,
        'ha0':float(fileparams['HourAnglefd'][0]),
        'min_slit':float(fileparams['MinSlitLengthfd'][0]),
        'sep_slit':float(fileparams['MinSlitSeparationfd'][0]),
        'slit_width':float(fileparams['SlitWidthfd'][0]),
        'box_sz':float(fileparams['AlignBoxSizefd'][0]),
        'blue':float(fileparams['BlueWaveLengthfd'][0]),
        'red':float(fileparams['RedWaveLengthfd'][0]),
        'proj_len':False,
        'no_overlap':False,
#    'std_format':True,     #Remove this option
        'lambda_cen':float(fileparams['CenterWaveLengthfd'][0]),
        'temp':float(fileparams['Temperaturefd'][0]),
        'pressure':float(fileparams['Pressurefd'][0]),
        'maskid':fileparams['MaskIdfd'][0],
        'guiname':fileparams['MaskNamefd'][0],
        'dateobs':fileparams['ObsDatefd'][0],
        'author':fileparams['Authorfd'][0],
        'observer':fileparams['Observerfd'][0],
        'project':fileparams['ProjectNamefd'][0],
        'instrument':'DEIMOS',
        'telescope':'Keck II'
 }

    params['descreate']=datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    site={k:([v] if type(v)!=list else v) for (k,v) in site.items()}
    params={k:([v] if type(v)!=list else v) for (k,v) in params.items()}     ####   <-----fix this for correct outputs
    tel={k:([v] if type(v)!=list else v) for (k,v) in tel.items()}

    slitsdf=pd.DataFrame(slit)
#    slitsdf=slitsdf[(slitsdf['sel']==1) & (slitsdf['inMask']==1)]
#    slitsdf.reset_index(drop=True,inplace=True)

    paramdf=pd.DataFrame(params)
    sitedf=pd.DataFrame(site)
    teldf=pd.DataFrame(tel)

    from writeMask import MaskDesignOutputFitsFile
    mdf=MaskDesignOutputFitsFile(slitsdf,sitedf,paramdf,teldf)
    mdf.writeTo(params['mdf'][0])
    if params['mdf'][0].endswith('.fits'):
        mdf.writeOut(params['mdf'][0][:-5]+'.out')
    else:
        mdf.writeOut(params['mdf'][0]+'.out')

    return df
