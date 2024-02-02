import pandas as pd
import numpy as np
import logging
import maskLayouts as ml
import targs
logger = logging.getLogger('smdt')


def selector(df, xmin, xmax, min_slit, slit_gap):
    logger.debug('Running Selector')
    # need to check for preselected
    npre = len(df[(df["sel"] == 1) & (df["pcode"] != -1)])

    # need to select options

    # sel_sort() low-to high sort of x1 and xarcs
    df = df.sort_values(by=["xarcs"])
    tg = df[df['pcode'] != -1]

    sel = tg[tg['sel'] == 1]
    opt = tg[(tg['sel'] != 1) & (tg['inMask'] == 1) & (df['pcode'] > 0)]
    nopt = len(tg[(tg['sel'] != 1) & (tg['inMask'] == 1) & (df['pcode'] > 0)])

    # Should this be L1+L2 instead of min_slit?  Or maybe optional ones we all assume min_slit.
    minsep = 2*(0.5*min_slit+slit_gap)

    # Already selected
    # The number of "gaps" to search is npre+1
    ndx = 0
    xlow = xmin
    xskip = 0.
    logger.debug(
        f'sel conditions {sel.xarcs}, {npre}, {nopt}, {minsep}, {slit_gap}')
    if (len(opt) > 0):  # was sel originally, but didnt make sense
        for i in range(npre+1):
            logger.debug(f'{i},{npre},{range(npre)}')
            if (i < npre):
                ndx = sel.index[i]
                xupp = sel.X1[ndx]
                xskip = sel.X2[ndx] - sel.X1[ndx]
            else:
                xupp = xmax

            if (xupp > xlow):
                logger.debug(
                    f'running sel rank over range {xlow, xupp, len(opt)}')
                opt = sel_rank(opt, xlow, xupp, minsep, slit_gap)
            xlow = xupp + xskip

    cols = list(df.columns)
    df = df.sort_values(by=["index"])
    df.loc[df.index.isin(opt.index), cols] = opt[cols]
    return df.to_dict(orient='records')


def sel_rank(opt, xlow, xupp, minsep, slit_gap):
    logger.debug(f'Starting sel_rank xlow: {xlow}, xupp: {xupp})')

    # Can we fit a minimum slit in here?
    if (xupp - xlow < minsep):               # probably too restrictive, can't fit anything in this gap, exit
        logger.debug('too restrictive. returning')
        return opt

    # Start at half a slit length; stop inside half slit length
    # grab xarc for last target option
    x = opt.iloc[-1].xarcs
    # stop at last target or upper limit to stop (whichever is closer)
    xstop = np.min([x, xupp-0.5*minsep])
    # defines start of search range (xarc should be greater than this to fit slit)
    xnext = xlow + 0.5 * minsep
    xlast = xlow

    # Loop through to end
    i = 0
    while i < len(opt.xarcs):
        ndx = opt.index[i]
        x = opt.xarcs[ndx]
        if (x < xnext):                          # xarc is too close for a slit, continue
            i = i+1
            logger.debug('too close. continue')
            continue
        if (opt.X1[ndx] < xlast):                  # X1 (slit edge) is less than xlast, continue
            i = i+1
            logger.debug('edge overlap. continue')
            continue
        if (x > xstop):  # xarc > last target or upper limit to stop; break
            logger.debug('exceeded xstop. break')
            break

        isel = i  # selected index (best)
        slitlen = opt.X2[ndx] - opt.X1[ndx]
        prisel = opt.pcode[ndx] / (x - xlast) / slitlen  # priority selection

        # Now look for higher priority to win out, over range (xlast,xlook) (another 0.5*minsep)
        xlook = np.min([x+minsep, xstop])
        if (isel < len(opt.xarcs)):              # should always be the case??
            # starting at next option after selected, to look for a better one
            for j in range(i+1, len(opt), 1):
                jdx = opt.index[j]               # not needed?

                if (opt.X1[jdx] > opt.X2[ndx]+slit_gap):
                    # There is no conflict, far enough away that it can be skipped.
                    continue
                    # XXX but prisel gets higher?
                if (opt.X2[jdx] > xupp):
                    # XXX Can't use as slit extends too far.  (inconsistent use of X2 vs x in sel_rank, should be xupp-0.5*minsep?).
                    continue

                if (opt.X1[jdx] < xlast):
                    # MJL added (can't have it overlapp with xlast either)
                    continue

                xj = opt.xarcs[jdx]
                if (xj >= xlook):                # we've looked out to our limit, break
                    break

                slitlen = opt.X2[jdx] - opt.X1[jdx]
                prinorm = opt.pcode[jdx] / (xj - xlast) / slitlen
                if (prinorm > prisel):
                    x = xj                      # not needed, isel/prisel only?
                    isel = j
                    prisel = prinorm

        ndx = opt.index[isel]
        xlast = opt.X2[ndx]
        xnext = xlast + 0.5 * minsep
        i = isel                        # Reset search start point
        i = i+1
        # set selection if
        logger.debug(f'Saving selection {ndx}, {isel}')
        # New column to differentiate between originally selected and sel_rank selected ones for re-running at different angles?
        opt.sel[ndx] = 1

    return opt


def from_list(obs, sel=True):
    mask = ml.MaskLayouts["deimos"]
    minX, maxX = np.min(mask, axis=0)[0], np.max(mask, axis=0)[0]
    # Convert dict of lists to list of dicts
    obs = targs.mark_inside(obs)
    min_slit, slit_gap = 10, 0.35  # set from inputs
    out = selector(pd.DataFrame(obs), minX, maxX,
                   min_slit, slit_gap) if sel else obs
    keys = ['ra0_fld', 'dec0_fld', 'ha0_fld', 'lst', 'pa0_fld',
            'orig_ref1', 'orig_ref3', 'ra_fldR', 'dec_fldR', 'ra_telR', 'dec_telR']
    out = [{**el, **{key: out[0][key] for key in keys}} for el in out]
    return out
