from flask import Flask, render_template, request, make_response, session, redirect, url_for, jsonify
from flask_session import Session
from werkzeug.datastructures import CombinedMultiDict, ImmutableMultiDict
import webbrowser
from threading import  Timer
from datetime import timedelta
import maskLayouts as ml
import configFile as cf
import json
import re
import numpy as np
#import dss2Header
import targs
import pdb
import calcmask
import utils
import plot
from targetSelector import TargetSelector
import dsimselector


def launchBrowser(host, portnr, path):
    webbrowser.open(f"http://{host}:{portnr}/{path}", new=1)

def stripquote(string):
    if string.count('"')==2:
        string=re.findall(r'"([^"]*)"',string)
    return string

def form_or_json():
    if request.method == 'POST':
        if request.files:
            return CombinedMultiDict((request.files, request.form))
        elif request.form:
            return request.form
        elif request.get_json():
            return ImmutableMultiDict(request.get_json())

def fixType(params):

    for p in params:
        if  p=='MaskIdfd':
            params[p]=[int(params[p][0])]
        elif p=='MinSlitLengthfd' or p=='MinSlitSeparationfd' or p=='SlitWidthfd' or p=='AlignBoxSizefd' or p=='BlueWaveLengthfd' or p=='RedWaveLengthfd' or p=='CenterWaveLengthfd' or p=='Temperaturefd' or p=='Pressurefd' or p=='MaskPAfd' or p=='SlitPAfd' or p=='MaskMarginfd' or p=='HourAnglefd':
            params[p]=[float(params[p][0])]
        else:
            continue
    
    return params


def dbprint(st):
    print("\033[95m {}\033[00m" .format(st))
    pass



app = Flask(__name__)
app.secret_key='dsf2315ewd'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=0.001)

# The maximum number of items the session stores 
# before it starts deleting some, default 500
app.config['SESSION_FILE_THRESHOLD'] = 10000  
Session(app)


#@app.route('/readparams')
def readparams():
    dict={}
    with open('params.cfg') as f:
        for line in f:
            try:
                if len(line.split(','))==4:
                    sep=line.strip().split(',')
                    (k,v) = sep[0].split(' = ')
                    dict[k]=(stripquote(v),stripquote(sep[1]),stripquote(sep[2]),stripquote(sep[3]))
                else:
                    continue
            except Exception as e:
                pass
                print('Failed to load parameters',e)
    return dict


@app.route('/setColumnValue',methods=["GET","POST"])
def setColumnValue():
    global df
    global prms
    targets=df
    params=prms
#    pdb.set_trace()
    values=json.loads(request.data.decode().split('=')[2].split('&')[0])
    column=request.data.decode().split('=')[1].split('&')[0]
    df=targs.updateColumn(targets,column,values)
    outp=targs.toJsonWithInfo(params,df)
    return outp



@app.route('/updateTarget',methods=["GET","POST"])
def updateTarget():
    global df
    global prms
    targets=df
    values=json.loads(request.data.decode().split('=')[1].split('}&')[0]+'}')
    df,idx=targs.updateTarget(targets,values)
    outp=targs.toJsonWithInfo(prms,df)
    tgs = json.loads(outp)

    outp=merged_dict = {**tgs, **{'idx':idx}}
    return outp
#    return json.dumps({'idx':idx})


@app.route('/updateSelection',methods=["GET","POST"])
def updateSelection():
    global df
    global prms
    targets=df
    values=json.loads(request.data.decode().split('=')[1].split('}&')[0]+'}')
    df,idx=targs.updateTarget(targets,values)
    outp=targs.toJsonWithInfo(prms,df)
    tgs = json.loads(outp)

    outp=merged_dict = {**tgs, **{'idx':idx}}
    return outp

@app.route('/deleteTarget',methods=["GET","POST"])
def deleteTarget():
    global df
    global prms
    targets=df
    idx=int(request.args.get('idx',None))
    df=targs.deleteTarget(targets,idx)
    outp=targs.toJsonWithInfo(prms,df)
    return outp

@app.route('/resetSelection',methods=["GET","POST"])
def resetSelection():
    global df
    global prms
    df.selected=df.loadselected
    outp=targs.toJsonWithInfo(prms,df)
    return outp


@app.route('/getTargetsAndInfo')
def getTargetsAndInfo():
    global prms
    params=prms
    global df
    try:
        print('newdf/getTargetsAndInfo')
        newdf=calcmask.genObs(df,params)
        newdf=targs.markInside(newdf)
        mask = ml.MaskLayouts["lris"]
        minX, maxX = np.min(mask, axis=0)[0], np.max(mask, axis=0)[0]
        #selector = TargetSelector(newdf, minX, maxX, float(params['MinSlitLengthfd'][0]), float(params['MinSlitSeparationfd'][0]))
        #newdf = selector.performSelection(extendSlits=False)
        outp=targs.toJsonWithInfo(params,newdf)
    except Exception as e:
        print('Exception',e)
        outp=''
    return outp
    

@app.route('/generateSlits',methods=["GET","POST"])
def generateSlits():
    global df
    global prms
    params=prms
    df=targs.markInside(df)
    newdf=calcmask.genSlits(df,params,auto_sel=False)
    mask = ml.MaskLayouts["lris"]
    minX, maxX = np.min(mask, axis=0)[0], np.max(mask, axis=0)[0]
    df=newdf
    outp=targs.toJsonWithInfo(params,newdf)
    return outp


##Performs auto-selection of slits##
@app.route('/recalculateMask',methods=["GET","POST"])
def recalculateMask():
    global df
    global prms
    params=prms
    df=targs.markInside(df)
    newdf=calcmask.genSlits(df,params,auto_sel=True)
    mask = ml.MaskLayouts["lris"]
    minX, maxX = np.min(mask, axis=0)[0], np.max(mask, axis=0)[0]
 #   selector = TargetSelector(newdf, minX, maxX, float(params['MinSlitLengthfd'][0]), float(params['MinSlitSeparationfd'][0]))
#    newdf = selector.performSelection(extendSlits=False)
    df=newdf
    outp=targs.toJsonWithInfo(params,newdf)
    return outp

@app.route('/saveMaskDesignFile',methods=["GET","POST"])
def saveMaskDesignFile():  # should only save current rather than re-running everything!
    global df
    global prms
    params=prms
    df=targs.markInside(df)
    mask = ml.MaskLayouts["lris"]
    minX, maxX = np.min(mask, axis=0)[0], np.max(mask, axis=0)[0]
 #   selector = TargetSelector(df, minX, maxX, float(params['MinSlitLengthfd'][0]), float(params['MinSlitSeparationfd'][0]))
#    df = selector.performSelection(extendSlits=False)

    newdf=calcmask.genMaskOut(df,params)
    plot.makeplot(params['OutputFitsfd'][0])
    df=newdf

    outp=targs.toJsonWithInfo(params,newdf)
    return outp


##Update Params Button, Load Targets Button
@app.route('/sendTargets2Server',methods=["GET","POST"])
def sendTargets2Server():
    print('sendTargets2Server()')
    global prms
    prms=request.form.to_dict(flat=False)
    params=prms
    print(prms)
    centerRADeg,centerDEC,positionAngle=15*utils.sexg2Float(params['InputRAfd'][0]),utils.sexg2Float(params['InputDECfd'][0]),float(params['MaskPAfd'][0])
    fh=[]
    session['params']=params
    prms=params
    print(request.files['targetList'])
    uploaded_file = request.files['targetList']
    if uploaded_file.filename != '':
        input=uploaded_file.stream
        for line in input:
            fh.append(line.strip().decode('UTF-8'))

        session['file']=fh
        global df
        df=targs.readRaw(session['file'],prms)
        df['loadselected']=df.selected                   #Only backup selected targets on file load.
    outp=targs.toJsonWithInfo(params,df)
    return outp
#    return ''    

##Update Params Button
@app.route('/updateParams4Server',methods=["GET","POST"])
def updateParams4Server():
    global prms
    prms=request.form.to_dict(flat=False)
    centerRADeg,centerDEC,positionAngle=15*utils.sexg2Float(prms['InputRAfd'][0]),utils.sexg2Float(prms['InputDECfd'][0]),float(prms['MaskPAfd'][0])
    session['params']=prms
    return ''


#Loads original params
@app.route('/getConfigParams')
def getConfigParams():
    global prms
    paramData=readparams()
    prms=paramData
    print('params:',paramData)
    session['params']=paramData
    prms=paramData
    return json.dumps({"params": paramData})


@app.route('/getMaskLayout')
def getMaskLayout():
    """
    Gets the mask layout, which is defined in maskLayout.py as a python data structure for convenience.
    MaskLayoput, GuiderFOV and Badcolumns are defined in maskLayouts.py

    Returns a JSON with mask, guiderFOC and badColumns
    """
    try:
        instrument = "lris"
        mask = ml.MaskLayouts[instrument]  # a list of (x,y,flag), polygon vertices
        guiderFOV = ml.GuiderFOVs[instrument]  # list of (x, y, w, h, ang), boxes
        badColumns = ml.BadColumns[instrument]  # list of lines, as polygons
        return {"mask": mask, "guiderFOV": guiderFOV, "badColumns": badColumns} ####might need to be jsonified
    except Exception as e:
        print(e)
        return ((0, 0, 0),)

#deletes target
@app.route('/deleteTarget')
#def deleteTarget():
#    return json.dumps({"params": paramData})



@app.route('/')
def home():
    return render_template('dt.html')


@app.route("/targets", methods=["GET","POST"])
def LoadTargets():
    return



if __name__ == '__main__':
    t=Timer(1,launchBrowser,['localhost',9305,'/'])
    t.start()
    app.run(host='localhost',port=9305,debug=True,use_reloader=False)

