#
# GEN_SLITS: initialize data structure for slits; fill (generate slits)
#

procedure       gen_slits (tdat, ntarg, sdat, nslit, indat)

pointer tdat
int     ntarg
pointer sdat
int     nslit
pointer indat

int     ndx, i
real    x, y

int     chk_stat()
begin

# Count the selected targets
        nslit = 0
        do i = 0, ntarg-1 {
                if (SEL(tdat,i) == YES)
                        nslit = nslit + 1
        }

# Allocate the vectors:
        call slit_alloc (sdat, nslit)           # nslit includes GS, etc

# Set up slits for selected targets:
        ndx = 0
        do i = 0, ntarg-1 {
                if (PCODE(tdat,i) == CODE_GS)   # Ignore guide stars
                        next
                if (SEL(tdat,i) == YES) {       # or != 0
                        x = XARCS(tdat,i)       # unclear TY of XYARCS
                        y = YARCS(tdat,i)
                        if (chk_stat (x, y, NO) == NO)
                                next            # Not on metal

                        INDEX(sdat,ndx) = ndx
                        if (PA(tdat,i) == INDEF) {
                                PA(sdat,ndx) = PA_ROT(indat)
                        } else {
                                PA(sdat,ndx) = PA(tdat,i)
                        }
                        RELPA(sdat,ndx) = RELPA(tdat,i)
                        PCODE(sdat,ndx) = PCODE(tdat,i)

                        X1(sdat,ndx) = X1(tdat,i)
                        Y1(sdat,ndx) = Y1(tdat,i)
                        X2(sdat,ndx) = X2(tdat,i)
                        Y2(sdat,ndx) = Y2(tdat,i)

# XXX NB: until the final sky_coords are calc'd, want X/YARCS to repr. objects
                        XARCS(sdat,ndx) = XARCS(tdat,i)
                        YARCS(sdat,ndx) = YARCS(tdat,i)
# XXX cuidado!  I am not sure that the tan-projection of the rel PA is the
# same as the rel PA -- MUST CHECK!

                        SLWID(sdat,ndx) = SLWID(tdat,i)

# This is where we also assign slit index to object
                        SLNDX(tdat,i) = ndx

                        ndx = ndx + 1
                }
        }
        nslit = ndx

        if (ADJ_LEN(indat) == YES)
                call len_slits (tdat, ntarg, sdat, nslit, indat)

end

#
# SLIT_ALLOC: allocate arrays for targets (broken out for MD ingestor)
# SLIT_FREE: free memory
#

