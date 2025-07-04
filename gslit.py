import math
import pdb
import pandas as pd
import logging
logger = logging.getLogger('smdt')


def gs_ingest():

    gsx1 = {'Polynomial': 3,
            'XX order': 2,
            'XY order': 2,
            'No cross terms': 0,
            'Min XX': -520,
            'Max XX': 520,
            'Min XY': 60,
            'Max XY': 500,
            'a11gsx1': 1.016705240037079,
            'a21gsx1': 6.687464442317909E-4,
            'a12gsx1': -0.003768592018465056}

    gsy1 = {'Polynomial': 3,
            'YX order': 2,
            'YY order': 2,
            'No cross terms': 0,
            'Min YX': -520,
            'Max YX': 520,
            'Min YY': 60,
            'Max YY': 500,
            'a11gsy1': -1.017054527544823,
            'a21gsy1': 0.9993337278388555,
            'a12gsy1': 0.003767549438866996}

    gsx2 = {'Polynomial': 3,
            'XX order': 4,
            'XY order': 3,
            'No cross terms': 1,
            'Min XX': -520,
            'Max XX': 520,
            'Min XY': 60,
            'Max XY': 500,
            'a11gsx2': 0.02096737234073239,
            'a21gsx2': -0.002856818950658679,
            'a31gsx2': 7.352264719120571E-8,
            'a41gsx2': -1.815660472554430E-11,
            'a12gsx2': -1.283628450621775E-4,
            'a22gsx2': 3.130290963876479E-7,
            'a32gsx2': -2.711217805831556E-10,
            'a42gsx2': -3.405048301772552E-13,
            'a13gsx2': 2.023744389073399E-7,
            'a23gsx2': 2.884798947183307E-8,
            'a33gsx2': 8.846686870636339E-14,
            'a43gsx2': 1.058362375914123E-15}

    gsy2 = {'Polynomial': 3,
            'YX order': 3,
            'YY order': 3,
            'No cross terms': 1,
            'Min YX': -520,
            'Max YX': 520,
            'Min YY': 60,
            'Max YY': 500,
            'a11gsy2': -0.02212851955870276,
            'a21gsy2': 0.002868421252923779,
            'a31gsy2': -6.937588005053427E-8,
            'a41gsy2': 1.372236409235230E-4,
            'a12gsy2': -3.212954741091695E-7,
            'a22gsy2': 2.371209886903566E-10,
            'a32gsy2': -2.156093090589542E-7,
            'a42gsy2': -2.890777864877165E-8,
            'a13gsy2': -5.544386481049514E-14,
            'a23gsy2': 0.0,
            'a33gsy2': 0.0,
            'a43gsy2': 0.0}

    return gsx1, gsx2


def gseval(x1, x2, cen, yas):
    dx = (x1['a11gsx1'] + x2['a11gsx2'])+(x1['a21gsx1']+x2['a21gsx2'])*cen + x2['a31gsx2']*(cen**2) + x2['a41gsx2']*(cen**3) + (x1['a12gsx1']+x2['a12gsx2'])*yas + x2['a22gsx2']*cen * \
        yas + x2['a32gsx2']*(cen**2)*yas + x2['a42gsx2']*(cen**3)*yas + x2['a13gsx2']*(yas**2) + \
        x2['a23gsx2']*cen*(yas**2) + x2['a33gsx2']*(cen**2) * \
        (yas**2) + x2['a43gsx2']*(cen**3)*(yas**2)

    return dx


# Adjust slit lengths to fit
def len_slits(dict, slit_gap=0.35):
    logger.debug('len_slits')
    #df=pd.DataFrame.from_dict(dict)
    df=pd.DataFrame(dict)
    tg = df[(df['pcode']!=-1) & (df['selected']==1) & (df['inMask']==1)] # remove pcode=-1 from list  ## was just tg=df[(df['pcode']!=-1) prev
    tg = tg.sort_values(by=['xarcs'], ascending=True)  ### Correct value to sort on?
    gsx1, gsx2=gs_ingest() ## only x used
        
    for i,row in enumerate(tg.iterrows()):
        if i==len(tg)-1:
            continue
        ndx1 = tg.index[i]
        ndx2 = tg.index[i+1]
        pc1 = tg.pcode[ndx1]
        pc2 = tg.pcode[ndx2]

        if pc1 == -2 and pc2 == -2:
            continue

        xlow = tg.X2[ndx1] + slit_gap 
        xupp = tg.X1[ndx2] - slit_gap 
        xcen = 0.5 * (xlow + xupp)

        yas = tg.Y2[ndx1]
        dxlow = gseval(gsx1, gsx2, xcen, yas)
        yas = tg.Y1[ndx2]
        dxupp = gseval(gsx1, gsx2, xcen, yas)
        dxavg = 0.5 * (dxupp + dxlow)
        dxlow = dxlow - dxavg
        dxupp = dxupp - dxavg

        if (pc1 == -2):
            del1 = 0.
            del2 = tg.X1[ndx2] - xlow - (dxupp - dxlow)
        elif (pc2 == -2):
            del1 = xupp - tg.X2[ndx1] + (dxlow - dxupp)
            del2 = 0.
        else:
            del1 = xcen - 0.5*slit_gap - tg.X2[ndx1] + dxlow
            del2 = tg.X1[ndx2] - (xcen + 0.5*slit_gap) - dxupp

        tg.loc[ndx1, 'X2'] = tg.X2[ndx1] + del1
        if (del1 != 0. and tg.relpa[ndx1] != None):
            tana = math.tan(tg.relpa[ndx1])
            tg.loc[ndx1, 'Y2'] = tg.Y2[ndx1] - del1 * tana

        tg.loc[ndx2, 'X1'] = tg.X1[ndx2] - del2
        if (del2 != 0. and tg.relpa[ndx2] != None):
            tana = math.tan(tg.relpa[ndx2])
            tg.loc[ndx2, 'Y1'] = tg.Y1[ndx2] + del2 * tana

    cols = list(df.columns)
    tg = tg.sort_values(by=["index"])
    df.loc[df.index.isin(tg.index), cols] = tg[cols]
    keys = ['ra0_fld', 'dec0_fld', 'ha0_fld', 'lst', 'pa0_fld', 'orig_ref1',
            'orig_ref3', 'ra_fldR', 'dec_fldR', 'ra_telR', 'dec_telR']
    for key in keys:
        df[key] = df.iloc[0][key]
    return df.to_dict(orient='records')
