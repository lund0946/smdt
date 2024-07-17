import sys
import pandas as pd
import math
from astropy.io import fits
from astropy import units as u
import maskLayouts
import matplotlib.pyplot as plt
import matplotlib.path as path
import matplotlib.patches as patches
import pdb


def drawPatch(ax, vertCodes, offx=0, offy=0, **kwargs):
    """
    For example:
    VertCodes = ( (x, y, c), (x, y, c), .. )
    kwargs: facecolor='none', lw=1, edgecolor='r'
    """
    # cTable = path.Path.MOVETO, path.Path.LINETO, path.Path.CLOSEPOLY

    if len(vertCodes) == 0: return None
    vertices = [(offx + x, offy + y) for x, y, m in vertCodes]
    codes = [(path.Path.MOVETO if m == 0 else path.Path.LINETO) for x, y, m in vertCodes]

    codes[0] = path.Path.MOVETO
    layout = path.Path(vertices, codes)
    patch = patches.PathPatch(layout, **kwargs)
    ax.add_patch(patch)
    return patch

def load_df(fname):
    
    sx1,sx2,sx3,sx4=[],[],[],[]
    sy1,sy2,sy3,sy4=[],[],[],[]

    f=fits.open(fname)            
    slitdata=f[7].data


    oname=[]
    oid=[]
    p=[]
    ra,dec=[],[]

    for i in range(len(f[1].data)):
        oid.append(f[1].data[i][0])
        oname.append(f[1].data[i][1])
        ra.append(f[1].data[i][2])
        dec.append(f[1].data[i][3])
        p.append(f[1].data[i][16])
    smo=[]
    smd=[]
    for i in range(len(f[5].data)):
        smo.append(f[5].data[i][1])
        smd.append(f[5].data[i][2])

    dslitid=[]
    for i in range(len(slitdata)):
        sx1.append(slitdata[i][3])
        sy1.append(slitdata[i][4])
        sx2.append(slitdata[i][5])
        sy2.append(slitdata[i][6])
        sx3.append(slitdata[i][7])
        sy3.append(slitdata[i][8])
        sx4.append(slitdata[i][9])
        sy4.append(slitdata[i][10])
        dslitid.append(slitdata[i][2])

    bluslits=pd.DataFrame({'dslitid':dslitid,'sx1':sx1,'sx2':sx2,'sx3':sx3,'sx4':sx4,'sy1':sy1,'sy2':sy2,'sy3':sy3,'sy4':sy4})
    slitobjmap=pd.DataFrame({'objectid':smo,'dslitid':smd})
    objectcat=pd.DataFrame({'objectid':oid,'objectname':oname,'objectclass':p,'ra':ra,'dec':dec})
    d1=bluslits.merge(slitobjmap,on='dslitid',how='inner')
    d2=d1.merge(objectcat,on='objectid',how='inner')
    mask=d2.loc[d2['objectclass']!='Guide_Star']
    return mask 


# total arguments
n = len(sys.argv)

if n!=3:
    print('Need 2 files to compare. Exiting.')
    sys.exit()

f1=sys.argv[1]
f2=sys.argv[2]

mask1 = load_df(f1)
mask2 = load_df(f2)

## print(mask2) ##
masks=mask2.merge(mask1,on=('objectname', 'ra', 'dec'),how='inner')

## print(masks) ##
dx1,dx2,dx3,dx4=[],[],[],[]
dy1,dy2,dy3,dy4=[],[],[],[]
dx,dy=[],[]
for i, row in masks.iterrows():
    dx1.append(row['sx1_x']-row['sx1_y'])
    dx2.append(row['sx2_x']-row['sx2_y'])
    dx3.append(row['sx3_x']-row['sx3_y'])
    dx4.append(row['sx4_x']-row['sx4_y'])
    dy1.append(row['sy1_x']-row['sy1_y'])
    dy2.append(row['sy2_x']-row['sy2_y'])
    dy3.append(row['sy3_x']-row['sy3_y'])
    dy4.append(row['sy4_x']-row['sy4_y'])
    dx.append(((row['sx1_x']-row['sx1_y'])+(row['sx2_x']-row['sx2_y'])+(row['sx3_x']-row['sx3_y'])+(row['sx4_x']-row['sx4_y']))/4.)
    dy.append(((row['sy1_x']-row['sy1_y'])+(row['sy2_x']-row['sy2_y'])+(row['sy3_x']-row['sy3_y'])+(row['sy4_x']-row['sy4_y']))/4.)



########
fig, sps = plt.subplots(3, figsize=(10, 8))
plt.subplot(311)
plt.title ("SMDT Mask Design Comparison")

ax=plt.gca()
ZPT_YM=128.803
MM2AS = math.degrees(3600 / 150280)  #
AS2MM = 1.0 / MM2AS  #
layout = maskLayouts.MaskLayouts["deimos"]
layoutMM = maskLayouts.scaleLayout(layout, AS2MM, 0, -ZPT_YM) ###

drawPatch(ax, layoutMM, fc="None", ec="g")
for i, row in mask1.iterrows():
    plt.plot([row['sx1'],row['sx2'],row['sx3'],row['sx4'],row['sx1']],[row['sy1'],row['sy2'],row['sy3'],row['sy4'],row['sy1']],color='b',alpha=0.8)
for i, row in mask2.iterrows():
    plt.plot([row['sx1'],row['sx2'],row['sx3'],row['sx4'],row['sx1']],[row['sy1'],row['sy2'],row['sy3'],row['sy4'],row['sy1']],color='r',alpha=0.8)

plt.gca().invert_xaxis()
plt.grid()

plt.subplot(312)
plt.plot(masks.sx1_x, dx1, "v", label="dX1")
plt.plot(masks.sx2_x, dx2, "^", label="dX2")
plt.plot(masks.sx3_x, dx3, ".", label="dX3")
plt.plot(masks.sx4_x, dx4, ".", label="dX4")
plt.xlabel("Slit X position [mm]")
plt.ylabel("X position Error [mm]")
plt.legend()
plt.grid()
plt.tight_layout()

plt.subplot(313)
plt.plot(masks.sy1_x, dy1, "v", label="dy1")
plt.plot(masks.sy2_x, dy2, "^", label="dy2")
plt.plot(masks.sy3_x, dy3, ".", label="dy3")
plt.plot(masks.sy4_x, dy4, ".", label="dy4")

plt.xlabel("Slit Y position [mm]")
plt.ylabel("Y Error [mm]")

plt.grid()
plt.tight_layout()

plt.show()
