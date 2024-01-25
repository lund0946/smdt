

from astropy.io import fits
import maskLayouts
import drawUtils
import utils
import matplotlib
import matplotlib.pyplot as plt
import logging
logger = logging.getLogger('smdt')
matplotlib.use('agg')

def makeplot(plotname):
    sx1,sx2,sx3,sx4=[],[],[],[]
    sy1,sy2,sy3,sy4=[],[],[],[]
    col=[]

    f=fits.open(plotname)
    slitdata=f[7].data
    typedata=f[4].data
    for i in range(len(slitdata)):
        logger.debug(slitdata[i])
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
    plt.title ("dsim comparison")

    ax=plt.gca()
    ZPT_YM=128.803
    layout = maskLayouts.MaskLayouts["deimos"]
    layoutMM = maskLayouts.scaleLayout(layout, utils.AS2MM, 0, -ZPT_YM) ###

    drawUtils.drawPatch(ax, layoutMM, fc="None", ec="g")
  
    for i in range(len(sx1)):
        plt.plot([sx1[i],sx2[i],sx3[i],sx4[i],sx1[i]],[sy1[i],sy2[i],sy3[i],sy4[i],sy1[i]],color=col[i],alpha=0.8)

    plt.gca().invert_xaxis()
    plt.grid()
    plt.savefig(plotname+'.png')
