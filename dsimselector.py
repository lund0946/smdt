import pandas as pd
import numpy as np
import math



def selector(df,xmin,xmax,min_slit,slit_gap):
    print(df)

    #need to check for preselected
    npre=len(df[df["sel"]==1])

    #need to select options

    ###sel_sort() low-to high sort of x1 and xarcs
    df=df.sort_values(by=["xarcs"])  

    tg=df[df['pcode']!=-1]

    sel=tg[tg['sel']==1]
    opt=tg[(tg['sel']!=1) & (tg['inMask']==1) & (df['pcode']>0)]
    nopt=len(tg[(tg['sel']!=1) & (tg['inMask']==1) & (df['pcode']>0)])


    minsep=2*(0.5*min_slit+slit_gap) ########       Should this be L1+L2 instead of min_slit?  Or maybe optional ones we all assume min_slit.
    print('xarc sorted opt')
    print(opt)

# Already selected
# The number of "gaps" to search is npre+1
    ndx = 0
    xlow = xmin
    xskip = 0.
    nselect = 0                     # triggers init in sel_rank
    print('sel conditions',len(sel.xarcs),npre,nopt,minsep,slit_gap)
    if (len(opt) > 0):            #was sel originally, but didnt make sense
        for i in range(npre):
            ndx=sel.index[i]
            if (i < npre):
                xupp = sel.X1[ndx]
                xskip = sel.X2[ndx] - sel.X1[ndx]
            else:
                xupp = xmax
                
            if (xupp > xlow):
                print('running sel rank over range ',xlow, xupp,len(opt))
                opt=sel_rank (opt, xlow, xupp, minsep, slit_gap)
            xlow = xupp + xskip


    print(opt)
    cols=list(df.columns)
    df=df.sort_values(by=["index"])
    df.loc[df.index.isin(opt.index), cols]=opt[cols]
    dfout=df.to_dict('list')
    print(dfout)
    return dfout




def sel_rank(opt, xlow, xupp, minsep, slit_gap):
    print('Starting sel_rank')
        
# Can we fit a minimum slit in here?
    if (xupp - xlow < minsep):               # probably too restrictive, can't fit anything in this gap, exit
        print('too restrictive,returning')
        return opt

# Start at half a slit length; stop inside half slit length  
    x = opt.iloc[-1].xarcs                            # grab xarc for last target option
    xstop = np.min ([x, xupp-0.5*minsep])        # stop at last target or upper limit to stop (whichever is closer)
    xnext = xlow + 0.5 * minsep                  # defines start of search range (xarc should be greater than this to fit slit)
    xlast = xlow

# Loop through to end
    i=0
    while i<len(opt.xarcs):
        ndx = opt.index[i]                      
        x = opt.xarcs[ndx]
        if (x < xnext):                          # xarc is too close for a slit, continue
            i=i+1
            print('too close, continue')
            continue
        if (opt.X1[ndx] < xlast):                  # X1 (slit edge) is less than xlast, continue
            i=i+1
            print('edge overlap, continue')
            continue
        if (x > xstop):                          #xarc > last target or upper limit to stop; break  
            print('exceeded xstop, break')
            break
                
        isel = i                                 #selected index (best)
        slitlen = opt.X2[ndx] - opt.X1[ndx]
        prisel = opt.pcode[ndx] / (x - xlast) / slitlen         ##priority selection
        
# Now look for higher priority to win out, over range (xlast,xlook) (another 0.5*minsep)
        xlook = np.min ([x+minsep, xstop])
        if (isel < len(opt.xarcs)):              # should always be the case??
            for j in range(i+1,len(opt),1):      #starting at next option after selected, to look for a better one
                jdx = opt.index[j]               # not needed?



                if (opt.X1[jdx] >  opt.X2[ndx]+slit_gap):
                    continue                     # There is no conflict, far enough away that it can be skipped.
                                                 # XXX but prisel gets higher?
                if (opt.X2[jdx] > xupp):
                    continue                     # XXX Can't use as slit extends too far.  (inconsistent use of X2 vs x in sel_rank, should be xupp-0.5*minsep?).

                if (opt.X1[jdx] < xlast):
                    continue                     # MJL added (can't have it overlapp with xlast either)
                


                xj = opt.xarcs[jdx]
                if (xj >= xlook):                # we've looked out to our limit, break
                    break

                slitlen = opt.X2[jdx] - opt.X1[jdx]
                prinorm = opt.pcode[jdx] / (xj - xlast) / slitlen
                if (prinorm > prisel):
                     x = xj                      # not needed, isel/prisel only?
                     isel = j
                     prisel = prinorm

#        nsel = nsel + 1
#        ndx = tndex[isel]
#        sel[nsel] = ndx
        ndx=opt.index[isel]
        xlast = opt.X2[ndx]
        xnext = xlast + 0.5 * minsep
        i = isel                        # Reset search start point
        i=i+1
        #set selection if 
        print('Saving selection ',ndx,isel)
        opt.sel[ndx]=1           # New column to differentiate between originally selected and sel_rank selected ones for re-running at different angles?

    return opt



def from_dict(dict):
    import maskLayouts as ml
    import targs
    mask=ml.MaskLayouts["deimos"]
    minX, maxX = np.min(mask, axis=0)[0], np.max(mask, axis=0)[0]
    df=pd.DataFrame.from_dict(dict)
    df=targs.markInside(df)
    min_slit,slit_gap=10,0.35  ## set from inputs
    dfout=selector(df,minX,maxX,min_slit,slit_gap)
    #dfout=df.to_dict('list')
    print(dfout)

    dfout['ra0_fld']=dfout['ra0_fld'][0]
    dfout['dec0_fld']=dfout['dec0_fld'][0]
    dfout['ha0_fld']=dfout['ha0_fld'][0]
    dfout['lst']=dfout['lst'][0]
    dfout['pa0_fld']=dfout['pa0_fld'][0]
    dfout['orig_ref1']=dfout['orig_ref1'][0]
    dfout['orig_ref3']=dfout['orig_ref3'][0]
    dfout['ra_fldR']=dfout['ra_fldR'][0]
    dfout['dec_fldR']=dfout['dec_fldR'][0]
    dfout['ra_telR']= dfout['ra_telR'][0]
    dfout['dec_telR']=dfout['dec_telR'][0]
    return dfout

