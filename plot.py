

from astropy.io import fits
import maskLayouts
import drawUtils
import utils
import matplotlib
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
matplotlib.use('agg')
import os

def makeplot(plotname):
    sx1,sx2,sx3,sx4=[],[],[],[]
    sy1,sy2,sy3,sy4=[],[],[],[]
    col=[]

    f=fits.open(plotname)
    slitdata=f[7].data
    typedata=f[4].data
    for i in range(len(slitdata)):
        print(slitdata[i])
        sx1.append(slitdata[i][3])
        sy1.append(slitdata[i][4])
        sx2.append(slitdata[i][5])
        sy2.append(slitdata[i][6])
        sx3.append(slitdata[i][7])
        sy3.append(slitdata[i][8])
        sx4.append(slitdata[i][9])
        sy4.append(slitdata[i][10])
        if typedata[i][5]=='P':      #color blue for slits
            col.append('royalblue')
        elif typedata[i][5]=='G':    #color gold for guidestars
            col.append('gold')
        elif typedata[i][5]=='A':    #color purple for alignment boxes
            col.append('violet')
        else:
            #can't identify slit type?
            col.append('crimson')    #color red if something else
    


    import matplotlib.pyplot as plt

    fig, sps = plt.subplots(1, figsize=(16, 5))
    plt.subplot(111)
    plt.title (os.path.splitext(os.path.basename(plotname))[0])

    ax=plt.gca()
    ZPT_YM=128.803
    layout = maskLayouts.MaskLayouts["deimos"]
    layoutMM = maskLayouts.scaleLayout(layout, utils.AS2MM, 0, -ZPT_YM) ###

    drawUtils.drawPatch(ax, layoutMM, fc="None", ec="g")
  
    for i in range(len(sx1)):
        if col[i]=='gold':
            plt.scatter((sx1[i]+sx2[i]+sx3[i]+sx4[i])/4,(sy1[i]+sy2[i]+sy3[i]+sy4[i])/4,s=30,facecolors='none',edgecolors=col[i],alpha=0.9,label='Guide Star')
            pass
        elif col[i]=='violet':
            plt.plot([sx1[i],sx2[i],sx3[i],sx4[i],sx1[i]],[sy1[i],sy2[i],sy3[i],sy4[i],sy1[i]],color=col[i],alpha=0.8,label='Alignment Box')
        elif col[i]=='royalblue':
            plt.plot([sx1[i],sx2[i],sx3[i],sx4[i],sx1[i]],[sy1[i],sy2[i],sy3[i],sy4[i],sy1[i]],color=col[i],alpha=0.8,label='Target slit')
        else:
            plt.plot([sx1[i],sx2[i],sx3[i],sx4[i],sx1[i]],[sy1[i],sy2[i],sy3[i],sy4[i],sy1[i]],color=col[i],alpha=0.8,label='Unknown')

    plt.gca().invert_xaxis()
    plt.grid()
    plt.legend([Line2D([], [], color='gold'),Line2D([], [], color='violet'),Line2D([], [], color='royalblue'),Line2D([], [], color='crimson')],['Guide Star','Alignment Box','Target slit','Unknown'],loc="upper left")
    plt.savefig(plotname+'.png')
