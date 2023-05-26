from flask import Flask, render_template, request, make_response, session, redirect, url_for, jsonify
from werkzeug.datastructures import CombinedMultiDict, ImmutableMultiDict
import webbrowser
from threading import  Timer
import maskLayouts as ml
import configFile as cf
import json
import re
import numpy as np
import dss2Header
import targs
import pdb
import calcmask
import utils
import plot
from targetSelector import TargetSelector

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
        elif p=='MinSlitLengthfd' or p=='MinSlitSeparationfd' or p=='SlitWidthfd' or p=='AlignBoxSizefd' or p=='BlueWaveLengthfd' or p=='RedWaveLengthfd' or p=='ReferenceWaveLengthfd' or p=='CenterWaveLengthfd' or p=='Temperaturefd' or p=='Pressurefd' or p=='MaskPAfd' or p=='SlitPAfd' or p=='MaskMarginfd' or p=='HourAnglefd':
            params[p]=[float(params[p][0])]
        else:
            continue
    
    return params



SESSION_TYPE='redis'
app = Flask(__name__)
app.secret_key='dsf2315ewd'

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
            except:
                print('Failed to load parameters')
    return dict


@app.route('/setColumnValue',methods=["GET","POST"])
def setColumnValue():
    print('setting column')
    global df
    targets=df
    print(targets)
#    pdb.set_trace()
    values=json.loads(request.data.decode().split('=')[2].split('&')[0])
    column=request.data.decode().split('=')[1].split('&')[0]
    print(column,values)
    df=targs.updateColumn(targets,column,values)
    print(df)
    outp=targs.toJsonWithInfo(session['params'],df)
    return outp



@app.route('/updateTarget',methods=["GET","POST"])
def updateTarget():
    global df
    print('update target')
    targets=df
    print(targets)
    values=json.loads(request.data.decode().split('=')[1].split('}&')[0]+'}')
    print(values)
    print(values['targetName'])
    df,idx=targs.updateTarget(targets,values)
    return json.dumps({'idx':idx})


@app.route('/deleteTarget',methods=["GET","POST"])
def deleteTarget():
    global df
    print('deleteTarget')
    print('data->',request.data.decode())
    targets=df
    idx=int(request.args.get('idx',None))
    df=targs.deleteTarget(targets,idx)
    outp=targs.toJsonWithInfo(session['params'],df)
    print(outp)
    return outp




@app.route('/getTargetsAndInfo')
def getTargetsAndInfo():
    print('targs and info')
    print(session['params'])
    params=session['params']
    global df
    if True:
#    try:
        print(df)
        print('TYPE-------------',type(df))
        newdf=calcmask.genObs(df,session['params'])
        print('pre sel')
        print(newdf)
        newdf=targs.markInside(newdf)
        mask = ml.MaskLayouts["deimos"]
        minX, maxX = np.min(mask, axis=0)[0], np.max(mask, axis=0)[0]
        selector = TargetSelector(newdf, minX, maxX, float(params['MinSlitLengthfd'][0]), float(params['MinSlitSeparationfd'][0]))
        newdf = selector.performSelection(extendSlits=False)
        print('post sel')
        print(newdf)
        outp=targs.toJsonWithInfo(session['params'],newdf)
#    except:
#        outp=''
    print(outp)
    return outp
    
@app.route('/recalculateMask',methods=["GET","POST"])
def recalculateMask():
    print('recalculate mask')
    global df
    print(df)
    print('TYPE-------------',type(df))
    params=session['params']
    newdf=calcmask.genSlits(df,session['params'])
    print(newdf)
    newdf=targs.markInside(newdf)
    mask = ml.MaskLayouts["deimos"]
    minX, maxX = np.min(mask, axis=0)[0], np.max(mask, axis=0)[0]
    selector = TargetSelector(newdf, minX, maxX, float(params['MinSlitLengthfd'][0]), float(params['MinSlitSeparationfd'][0]))
    newdf = selector.performSelection(extendSlits=False)

    print(newdf)
    outp=targs.toJsonWithInfo(session['params'],newdf)
    print(outp)
    return outp

@app.route('/saveMaskDesignFile',methods=["GET","POST"])
def saveMaskDesignFile():
    print('Save Mask Design')
    global df
    print(df)
    params=session['params']
    print('TYPE-------------',type(df))
    df=targs.markInside(df)
    mask = ml.MaskLayouts["deimos"]
    minX, maxX = np.min(mask, axis=0)[0], np.max(mask, axis=0)[0]
    selector = TargetSelector(df, minX, maxX, float(params['MinSlitLengthfd'][0]), float(params['MinSlitSeparationfd'][0]))
    df = selector.performSelection(extendSlits=False)

    newdf=calcmask.genMaskOut(df,session['params'])
    plot.makeplot(params['OutputFitsfd'][0])

    outp=targs.toJsonWithInfo(session['params'],newdf)
    print(outp)
    return outp


##Update Params Button, Load Targets Button
@app.route('/sendTargets2Server',methods=["GET","POST"])
def sendTargets2Server():
    params=request.form.to_dict(flat=False)
    print('Here Are PARAMS! \n\n\n\n\n\n\n')
    print(params['InputRAfd'],params['InputDECfd'])
    centerRADeg,centerDEC,positionAngle=15*utils.sexg2Float(params['InputRAfd'][0]),utils.sexg2Float(params['InputDECfd'][0]),float(params['MaskPAfd'][0])
    print(params)
    fh=[]
    session['params']=params
    uploaded_file = request.files['targetList']
    print('send2server')
    if uploaded_file.filename != '':
        input=uploaded_file.stream
        for line in input:
            print(line.strip().decode('UTF-8'))
            fh.append(line.strip().decode('UTF-8'))

        session['file']=fh
        global df
        df=targs.readRaw(session['file'],session['params'])

    return ''    


#Loads original params
@app.route('/getConfigParams')
def getConfigParams():
    paramData=readparams()
    session['params']=paramData
    return json.dumps({"params": paramData})


@app.route('/getMaskLayout')
def getMaskLayout():
    """
    Gets the mask layout, which is defined in maskLayout.py as a python data structure for convenience.
    MaskLayoput, GuiderFOV and Badcolumns are defined in maskLayouts.py

    Returns a JSON with mask, guiderFOC and badColumns
    """
    try:
        instrument = "deimos"
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
    t=Timer(1,launchBrowser,['localhost',9302,'/'])
    t.start()
    app.run(host='localhost',port=9302,debug=True,use_reloader=False)

