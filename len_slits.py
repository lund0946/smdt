

pandas dataframe





def slit_len():

#        call slit_sort (Memr[bufx], Memi[bufi], nslit)

    fdx=open(XPROJ_MAP)      # distortion map
    gs_ingest(fdx,asfx,asfy) # distortion map -> polynomial function


    for i in range(len(ra)-1):
        pc1=df['pcode'][i]
        pc2=df['pcode'][i+1]

        if pc1<0 and pc2<0:
            continue          # both alignment/guide stars no problem
  
        xlow=X2+param['slit_gap']
        xupp=X1-param['slit_gap']
  
        xcen=0.5*(xlow+xupp)
  
        yas=Y2
        dxlow=gseval(asfx,xcen,yas) #<-evaluate polynomial distortion at x,y
        yas=Y1
        dxupp=gseval(asfx,xcen,yas) 
        dxavg = 0.5 * (dxupp + dxlow)
        dxlow = dxlow - dxavg
        dxupp = dxupp - dxavg

        if pc1<0:
            del1=0
            del2=X1-xlow-(dxupp-dxlow)
        elif pc2<0:
            del1 =  xupp - X2(sdat,ndx1) + (dxlow - dxupp)
            del2 = 0.
        else:
            del1 = xcen - 0.5*param['slit_gap'] - X2 + dxlow
            del2 = X1 - (xcen + 0.5*param['slit_gap']) - dxupp
  
        X2 = X2 + del1
        if (del1 != 0. && RELPA != INDEF) 
            tana = np.tan (RELPA)
            Y2 = Y2 + del1 * FLIP * tana  #FLIP=-1
                

        X1 = X1 - del2
        if (del2 != 0. && RELPA != INDEF) 
            tana = np.tan (RELPA)
            Y1 = Y1 - del2 * FLIP * tana #FLIP=-1


         
