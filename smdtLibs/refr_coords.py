
import numpy as np



def refCoords(ra_fld,dec_fld,ha_fld,obs_lat,obs_alt,tempc,pressmb,obs_rh,waver,wmin,wmax,ra,dec)
    lst = ra_fld + ha_fld
    lat = np.radians(obs_lat)        # radians
    htm = obs_alt                   # meters
    tdk = TEMP(indat) + 273.15      # temp in K
    pmb = PRES(indat)               # millibars
    rel_h20 = obs_rh                # relative humidity
    w = waver

# Get the refraction coeffs (2 hardcodes suggested in SLALIB):

    r1,r3=slrfco (htm, tdk, pmb, rel_h20, w, lat, 0.0065D0, 1D-10)

# Save the refraction coeffs for later use:
    REF1 = r1
    REF3 = r3

    halfpi=np.pi/2.

# Apply to field center
    ha = lst - ra_fld
    az,el=sl.slde2h (ha, dec_fld, lat)
    zd0 = halfpi - el
    zd=sl.slrefz (zd0, r1, r3)
    el = halfpi - zd
    ha,dec_fld=sl.sldh2e (az, el, lat)
    ra_fld = lst - ha

# Loop and apply to targets:
    for i in range(len(ra)):
        ha = lst - ra[i]
        az,el=slde2h (ha, dec[i], lat)

        zd = halfpi - el
        zd = sl.slrefz (zd, r1, r3, zd)
        el = HALFPI - zd

        ha,dec[i]=sldh2e (az, el, lat)
#        ra[i] = lst - ha  ##may want to do an ra0,dec0 and ra,dec table
        

# Now work out atmospheric dispersion:
    zd=slrefz (zd0, r1, r3)

    w1 = wmin
    w2 = wmax
    a,b=sl.slatmd (tdk, pmb, rel_h20, w, r1, r3, w1)
    zd1=sl.slrefz (zd0, a, b, zd1)
    a,b=sl.slatmd (tdk, pmb, rel_h20, w, r1, r3, w2, a, b)
    zd2=sl.slrefz (zd0, a, b, zd2)

# ... amount
    ad1 = (zd1 - zd) * 206205.
    ad2 = (zd2 - zd) * 206205.

# ... and paralactic angle
    par_ang=sl.slpa(ha_fld, dec_fld, lat)

# Finally, airmass:
    amass=sl.slarms(zd)


