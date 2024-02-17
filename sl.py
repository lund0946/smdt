import numpy as np
import math






def slrfco(hm,tdk,pmb,rh,wl,phi,tlr,eps):
    atn1=0.7853981633974483
    atn4=1.325817663668033

    r1=slrfro(atn1,hm,tdk,pmb,rh,wl,phi,tlr,eps)
    r2=slrfro(atn4,hm,tdk,pmb,rh,wl,phi,tlr,eps)

    refa=(64.*r1-r2)/60.
    refb=(r2-4.*r1)/60.
    return refa,refb

def refi(dn,rdndr):
    return rdndr/(dn+rdndr)

def slrfro(zobs,hm,tdk,pmb,rh,wl,phi,tlr,eps):
    d93=1.623156204
    gcr=8314.32
    dmd=28.9644
    dmw=18.0152
    s=6378120.
    delta=18.36
    ht=11000.
    hs=80000.
    ismax=16384.

    #transform zobs into normal range
    zobs1=slda1p(zobs)
    zobs2=min(abs(zobs1),d93)

    hmok=min(max(hm,-1e3),hs)
    tdkok=min(max(tdk,100.),500.)
    pmbok=min(max(pmb,0.),10000.)
    rhok=min(max(rh,0.),1.)
    wlok=max(wl,0.1)
    alpha=min(max(abs(tlr),0.001),0.01)
  
    tol=min(max(abs(eps),1e-12),0.1)/2.

    optic=wlok<=100.


    #  set up model atmosphere parameters defined at the observer.
    wlsq = wlok*wlok
    gb = 9.784*(1.-0.0026*math.cos(phi+phi)-0.00000028*hmok)
    if (optic):
        a = (287.604+(1.6288+0.0136/wlsq)/wlsq)*273.15e-6/1013.25
    else:
        a = 77.624e-6
    gamal = (gb*dmd)/gcr
    gamma = gamal/alpha
    gamm2 = gamma-2.
    delm2 = delta-2.
    tdc = tdkok-273.15
    psat = 10.**((0.7859+0.03477*tdc)/(1+0.00412*tdc))*(1+pmbok*(4.5e-6+6e-10*tdc*tdc))
    if (pmbok>0.):
        pwo = rhok*psat/(1.-(1.-rhok)*psat/pmbok)
    else:
        pwo = 0.
      
    w = pwo*(1.-dmw/dmd)*gamma/(delta-gamma)
    c1 = a*(pmbok+w)/tdkok
    if (optic):
        c2 = (a*w+11.2684e-6*pwo)/tdkok
    else:
        c2 = (a*w+12.92e-6*pwo)/tdkok
      
    c3 = (gamma-1)*alpha*c1/tdkok
    c4 = (delta-1)*alpha*c2/tdkok
    if (optic):
        c5 = 0.
        c6 = 0.
    else:
        c5 = 371897.e-6*pwo/tdkok
        c6 = c5*delm2*alpha/(tdkok*tdkok)
      

   #*  conditions at the observer.
    r0 = s+hmok
    temp,dn0,rdndr0=slatmt(r0,tdkok,alpha,gamm2,delm2,c1,c2,c3,c4,c5,c6,r0)  #############
    sk0 = dn0*r0*math.sin(zobs2)                  #
    f0 = refi(dn0,rdndr0)                 #

   #*  conditions in the troposphere at the tropopause.
    rt = s+ht
    tt,dnt,rdndrt=slatmt(r0,tdkok,alpha,gamm2,delm2,c1,c2,c3,c4,c5,c6,rt)   #############
    sine = sk0/(rt*dnt)
    zt = math.atan2(sine,np.sqrt(max(1-sine*sine,0)))
    ft = refi(dnt,rdndrt)

   #*  conditions in the stratosphere at the tropopause.
    dnts,rdndrp=slatms(rt,tt,dnt,gamal,rt) #########
    sine = sk0/(rt*dnts)
    zts = math.atan2(sine,np.sqrt(max(1.-sine*sine,0)))
    fts = refi(dnts,rdndrp)

   #*  conditions at the stratosphere limit.
    rs = s+hs
    dns,rdndrs=slatms(rt,tt,dnt,gamal,rs) #########
    sine = sk0/(rs*dns)
    zs = math.atan2(sine,np.sqrt(max(1.-sine*sine,0)))
    fs = refi(dns,rdndrs)



#*
#*  integrate the refraction integral in two parts;  first in the
#*  troposphere (k=1), then in the stratosphere (k=2).
#*

#*  initialize previous refraction to ensure at least two iterations.
    refold = 1.

#*  start off with 8 strips for the troposphere integration, and then
#*  use the final troposphere value for the stratosphere integration,
#*  which tends to need more strips.
    iss = 8

#*  troposphere then stratosphere.
    for k in range(1,2+1):
        refold=1. 
        iss=8
#*     start z, z range, and start and end values.
        if (k==1):
            z0 = zobs2
            zrange = zt-z0
            fb = f0
            ff = ft
        else:
            z0 = zts
            zrange = zs-z0
            fb = fts
            ff = fs

#*     sums of odd and even values.
        fo = 0
        fe = 0

#*     first time through the loop we have to do every point.
        n = 1

#*     start of iteration loop (terminates at specified precision).
        loop = True
        while (loop):

#*        strip width.
            h = zrange/float(iss)

#*        initialize distance from earth centre for quadrature pass.
            if (k==1):
                r = r0
            else:
                r = rt

#*        one pass (no need to compute evens after first time).
            for i in range(1,iss-1+1,n):

#*           sine of observed zenith distance.
                sz = math.sin(z0+h*float(i))

#*           find r (to the nearest metre, maximum four iterations).
                if (sz > 1e-20):
                    w = sk0/sz
                    rg = r
                    dr = 1e6
                    j = 0
                    while (abs(dr)>1 and j<4):
                        j=j+1
                        if (k==1):
                            tg,dn,rdndr=slatmt(r0,tdkok,alpha,gamm2,delm2,c1,c2,c3,c4,c5,c6,rg) ############
                        else:
                            dn,rdndr=slatms(rt,tt,dnt,gamal,rg)        ############
                     
                        dr = (rg*dn-w)/(dn+rdndr)
                        rg = rg-dr
                  
                    r = rg

#*           find the refractive index and integrand at r.
                if (k==1):
                    t,dn,rdndr=slatmt(r0,tdkok,alpha,gamm2,delm2,c1,c2,c3,c4,c5,c6,r)    ########
                else:
                    dn,rdndr=slatms(rt,tt,dnt,gamal,r)  ##########
               
                f = refi(dn,rdndr)

#*           accumulate odd and (first time only) even values.
                if (n==1 and i%2==0):
                    fe = fe+f
                else:
                    fo = fo+f
              

#*        evaluate the integrand using simpson's rule.
            refp = h*(fb+4.*fo+2.*fe+ff)/3.

#*        has the required precision been achieved?
            if (abs(refp-refold)>tol):

#*           no: prepare for next iteration.

#*           save current value for convergence test.
                refold = refp

#*           double the number of strips.
                iss = iss+iss

#*           sum of all current values = sum of next pass's even values.
                fe = fe+fo

#*           prepare for new odd values.
                fo = 0.

#*           skip even values next time.
                n = 2
            else:

#*           yes: save troposphere component and terminate the loop.
                if (k==1): reft = refp
                loop = False

#*  result.
    ref = reft+refp
    if (zobs1<0): 
        ref = -ref

    return ref




def slatms(rt,tt,dnt,gamal,r):

    b = gamal/tt
    w = (dnt-1e0)*math.exp(-b*(r-rt))
    dn = 1e0+w
    rdndr = -r*b*w
    return dn,rdndr


def slatmt(r0,t0,alpha,gamm2,delm2,c1,c2,c3,c4,c5,c6,r):

    t = max(min(t0-alpha*(r-r0),320),100)
    tt0 = t/t0
    tt0gm2 = tt0**gamm2
    tt0dm2 = tt0**delm2
    dn = 1.+(c1*tt0gm2-(c2-c5/t)*tt0dm2)*tt0
    rdndr = r*(-c3*tt0gm2+(c4-c6/tt0)*tt0dm2)
    return t,dn,rdndr

def slda1p(angle):
    DPI=3.141592653589793238462643
    D2PI=6.283185307179586476925287

    slDA1P=angle%D2PI
    if (abs(slDA1P)>DPI):
        slDA1P=slDA1P-math.copysign(D2PI,angle)

    return slDA1P

def slrefz(zu,refa,refb):


    r2d=57.29577951308232

    d93=93.

    #*  coefficients for high zd model (used beyond zd 83 deg)
    c1=+0.55445
    c2=-0.01133
    c3=+0.00202
    c4=+0.28385
    c5=+0.02390

    #*  zd at which one model hands over to the other (radians)
    z83=83./r2d

    #*  high-zd-model prediction (deg) for that point
    ref83=(c1+c2*7.+c3*49.)/(1.+c4*7.+c5*49.)

    #*  perform calculations for zu or 83 deg, whichever is smaller
    zu1 = min(zu,z83)

    #*  functions of zd
    zl = zu1
    s = math.sin(zl)
    c = math.cos(zl)
    t = s/c
    tsq = t*t
    tcu = t*tsq

    #*  refracted zd (mathematically to better than 1 mas at 70 deg)
    zl = zl-(refa*t+refb*tcu)/(1.+(refa+3.*refb*tsq)/(c*c))

   #*  further iteration
    s = math.sin(zl)
    c = math.cos(zl)
    t = s/c
    tsq = t*t
    tcu = t*tsq
    ref = zu1-zl+(zl-zu1+refa*t+refb*tcu)/(1.+(refa+3.*refb*tsq)/(c*c))

   #*  special handling for large zu
    if (zu>zu1):
        e = 90.-min(d93,zu*r2d)
        e2 = e*e
        ref = (ref/ref83)*(c1+c2*e+c3*e2)/(1.+c4*e+c5*e2)

   #*  return refracted zd
    zr = zu-ref

    return zr





def slpa(ha,dec,phi):

#     HA     d     hour angle in radians (geocentric apparent)
#     DEC    d     declination in radians (geocentric apparent)
#     PHI    d     observatory latitude in radians (geodetic)

    cp=math.cos(phi)
    sqsz=cp*math.sin(ha)
    cqsz=math.sin(phi)*math.cos(dec)-cp*math.sin(dec)*math.cos(ha)
    if (sqsz==0. and cqsz ==0.): cqsz=1.
    pa=math.atan2(sqsz,cqsz)
    return pa


def slarms(zd):
    seczm1 = 1./(math.cos(min(1.52,np.abs(zd))))-1.
    airmass = 1. + seczm1*(0.9981833 - seczm1*(0.002875 + 0.0008083*seczm1))
    return airmass


def slde2h(ha,dec,phi):

    # All units in radians

#*  useful trig functions
    sh=math.sin(ha)
    ch=math.cos(ha)
    sd=math.sin(dec)
    cd=math.cos(dec)
    sp=math.sin(phi)
    cp=math.cos(phi)

#*  az,el as x,y,z
    x=-ch*cd*sp+sd*cp
    y=-sh*cd
    z=ch*cd*cp+sd*sp

#*  to spherical
    r=math.sqrt(x*x+y*y)
    if (r==0.0):
        a=0.0
    else:
       a=math.atan2(y,x)
    if (a<0.0): a=a+2*np.pi
    az=a
    el=math.atan2(z,r)
    return az,el


def sldh2e(az,el,phi):

#*  useful trig functions
    sa=math.sin(az)
    ca=math.cos(az)
    se=math.sin(el)
    ce=math.cos(el)
    sp=math.sin(phi)
    cp=math.cos(phi)

#*  ha,dec as x,y,z
    x=-ca*ce*sp+se*cp
    y=-sa*ce
    z=ca*ce*cp+se*sp

#*  to ha,dec
    r=math.sqrt(x*x+y*y)
    if (r==0.0):
        ha=0.0
    else:
        ha=math.atan2(y,x)
    dec=math.atan2(z,r)

    return ha,dec




def slatmd(TDK, PMB, RH, WL1, A1, B1, WL2):


#*  Check for radio wavelengths
    if (WL1>100. or WL2 >100.):
#*     Radio: no dispersion
        A2 = A1
        B2 = B1
    else:

#*     Optical: keep arguments within safe bounds
        TDKOK = np.min([np.max([TDK,100.]),500.])
        PMBOK = np.min([np.max([PMB,0.]),10000.])
        RHOK = np.min([np.max([RH,0.0]),1.0])

#*     Atmosphere parameters at the observer
        PSAT = 10.0**(-8.71150+0.034770*TDKOK)
        PWO = RHOK*PSAT
        W1 = 11.2684e-6*PWO

#*     Refractivity at the observer for first wavelength
        WLOK = np.max([WL1,0.10])
        WLSQ = WLOK*WLOK
        W2 = 77.5317e-6+(0.43909e-6+0.00367e-6/WLSQ)/WLSQ
        DN1 = (W2*PMBOK-W1)/TDKOK

#*     Refractivity at the observer for second wavelength
        WLOK = np.max([WL2,0.10])
        WLSQ = WLOK*WLOK
        W2 = 77.5317e-6+(0.43909e-6+0.00367e-6/WLSQ)/WLSQ
        DN2 = (W2*PMBOK-W1)/TDKOK

#*     Scale the refraction coefficients (see Green 4.31, p93)
        if (DN1 != 0.0):
            F = DN2/DN1
            A2 = A1*F
            B2 = B1*F
            if (DN1 != A1): 
                B2=B2*(1.0+DN1*(DN1-DN2)/(2.0*(DN1-A1)))
        else:
            A2 = A1
            B2 = B1
    return A2,B2

#elevation=45.


#hm=4150.
#tdk=273.15
#pmb=480.
#rh=0.4
#wl=0.4
#phi=0.3455752
#tlr=0.0065
#eps=1e-10
#zu=np.radians(elevation)




#refa,refb=slrfco(hm,tdk,pmb,rh,wl,phi,tlr,eps)
#zd=slrefz(zu,refa,refb)

