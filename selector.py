# SELECTOR: Does an auto selection of slits
# Should include an option for weighting to keep things toward the center.
# Note that y's sent to sel_rank are relative to starting y
# have it run from bottom to top
# -- need to work in segments to accomodate currently selected objects
# -- there was something else ...

procedure       selector (indat, tdat, ntarg, nlist, minsep, psum)

pointer indat
pointer tdat
int     ntarg
int     nlist           # list to work on
real    minsep          # XXX min. separation -- probably should be in DEFDAT
int     psum            # sum of selected priorities (returned)

int     nopt, npre              # number of options, prev. selected objects
int     i, ndx
int     ix                      # starting index for search (saves time)
int     nselect                         # Number of selected slits
real    xlow, xupp, xskip
pointer bufx1, bufx2                    # TMP? buffers for pre-sel. objs
pointer bufn, bufx, bufp, bufsel        # TMP, for now

begin
        nopt = 0
        npre = 0
        do i = 0, ntarg-1 {
                if (SEL(tdat,i) == YES) {
                        npre = npre + 1
                } else if (SAMPL(tdat,i) == nlist && STAT(tdat,i) == YES) {
                        nopt = nopt + 1
                }
        }
        call malloc (bufx1, npre, TY_INT)
        call malloc (bufx2, npre, TY_REAL)
        call malloc (bufn, nopt, TY_INT)
        call malloc (bufx, nopt, TY_REAL)
        call malloc (bufp, nopt, TY_INT)
        call malloc (bufsel, nopt, TY_INT)

# Grep on previously selected objects and suitable options; fill vectors
        nopt = 0
        npre = 0
        do i = 0, ntarg-1 {
                if (PCODE(tdat,i) == CODE_GS)           # GS's don't take space
                        next
                if (SEL(tdat,i) == YES) {
#                       Memr[bufx1+npre] = XARCS(tdat,i) - LEN1(tdat,i)
#                       Memr[bufx2+npre] = XARCS(tdat,i) + LEN2(tdat,i)
                        Memr[bufx1+npre] = X1(tdat,i)
                        Memr[bufx2+npre] = X2(tdat,i)
                        npre = npre + 1
                } else if (SAMPL(tdat,i) == nlist && STAT(tdat,i) == YES && PCODE(tdat,i) > 0) {
                        Memi[bufn+nopt] = i     # INDEX(tdat,i) XXX
                        Memr[bufx+nopt] = XARCS(tdat,i)
                        Memi[bufp+nopt] = PCODE(tdat,i)
                        nopt = nopt + 1
                }
        }

# Sort the two lists
        call sel_sort (Memr[bufx1], Memr[bufx2], npre,
                                Memi[bufn], Memr[bufx], Memi[bufp], nopt)

# The number of "gaps" to search is npre+1
        ndx = 0
        xlow = XLOW_LIM
        xskip = 0.
        nselect = 0                     # triggers init in sel_rank
        if (nopt > 0) {
            do i = 0, npre {
                if (i < npre) {
                        xupp = Memr[bufx1+i]
                        xskip = Memr[bufx2+i] - Memr[bufx1+i]
                } else {
                        xupp = XUPP_LIM
                }


## old ...
#               if (xupp <= xlow)
#                       next
#               call sel_rank (Memr[bufx], Memi[bufp], Memi[bufn],
#               Memi[bufsel], nopt, ix, xlow, xupp, minsep, nselect)
#               xlow = xupp + xskip

                if (xupp > xlow) {
                        call sel_rank (tdat, indat, Memi[bufn],
                        Memi[bufsel], nopt, ix, xlow, xupp, minsep, nselect)
                }

                xlow = xupp + xskip
            }
        }


#...select the mask slits
        if (nselect > 0) {
                do i = 0, nselect-1 {
                        SEL(tdat,Memi[bufsel+i]) = YES
                }
        }

        psum = 0
        do i = 0, ntarg-1 {
                if (SEL(tdat,i) == YES)
                        psum = psum + max (PCODE(tdat,i), 0)    # NO GS, AS
        }

        call mfree (bufsel, TY_INT)
        call mfree (bufp, TY_INT)
        call mfree (bufx, TY_REAL)
        call mfree (bufn, TY_INT)
        call mfree (bufx2, TY_REAL)
        call mfree (bufx1, TY_INT)
end

