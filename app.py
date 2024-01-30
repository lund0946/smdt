from datetime import timedelta
from flask import Flask, render_template, request, session, g
from flask.logging import default_handler
from flask_session import Session
from werkzeug.datastructures import CombinedMultiDict, ImmutableMultiDict
import webbrowser
from threading import Timer
import maskLayouts as ml
import json
import re
import targs
import calcmask
import plot
import logging
from logging import FileHandler, StreamHandler
import pdb

VALID_PARAMS = ['MaskIdfd',
                'MinSlitLengthfd',
                'MinSlitSeparationfd',
                'SlitWidthfd',
                'AlignBoxSizefd',
                'BlueWaveLengthfd', 
                'RedWaveLengthfd', 
                'CenterWaveLengthfd', 
                'Temperaturefd', 
                'Pressurefd', 
                'MaskPAfd', 
                'SlitPAfd', 
                'MaskMarginfd', 
                'HourAnglefd']
logger = logging.getLogger('smdt')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger.setLevel(logging.DEBUG)
logger.addHandler(default_handler)
st = StreamHandler()
st.setLevel(logging.DEBUG)
st.setFormatter(formatter)
fh = FileHandler('smdt.log')
fh.setFormatter(formatter)
logger.addHandler(fh)

def launchBrowser(host, portnr, path):
    webbrowser.open(f"http://{host}:{portnr}/{path}", new=1)


def stripquote(string):
    if string.count('"') == 2:
        string = re.findall(r'"([^"]*)"', string)
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

    for prm in params:
        if prm == 'MaskIdfd':
            params[prm] = [int(params[prm][0])]
        elif prm in VALID_PARAMS:
            params[prm] = [float(params[prm][0])]
        else:
            continue

    return params

def check_session(params=('df', 'params')):
    def decorator(fun):
        def wrapper(*args, **kwargs):
            for prm in params:
                if session.get(prm) is None:
                    raise Exception(f'No {prm} in session')
            return fun(*args, **kwargs)
        return wrapper
    return decorator


app = Flask(__name__)
app.config.from_pyfile('config.live.ini')
Session(app)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=app.config['PERMANENT_SESSION_LIFETIME'])

def readparams():
    dict = {}
    with open('params.cfg') as f:
        for line in f:
            try:
                if len(line.split(',')) == 4:
                    sep = line.strip().split(',')
                    (k, v) = sep[0].split(' = ')
                    dict[k] = (stripquote(v), stripquote(sep[1]),
                               stripquote(sep[2]), stripquote(sep[3]))
                else:
                    continue
            except Exception as err:
                logger.error('Failed to load parameters: {err}')
    return dict


@check_session
@app.route('/setColumnValue', methods=["GET", "POST"])
def setColumnValue():
    targets = session['df']
    values = json.loads(request.data.decode().split('=')[2].split('&')[0])
    column = request.data.decode().split('=')[1].split('&')[0]
    session['df'] = targs.updateColumn(targets, column, values)
    outp = targs.toJsonWithInfo(session['params'], session['df'])
    return outp


@check_session
@app.route('/updateTarget', methods=["GET", "POST"])
def updateTarget():
    targets = session['df']
    values = json.loads(request.data.decode().split('=')[1].split('}&')[0]+'}')
    session['df'], idx = targs.updateTarget(targets, values)
    outp = targs.toJsonWithInfo(session['params'], session['df'])
    tgs = json.loads(outp)

    outp = {**tgs, **{'idx': idx}}
    return outp


@check_session
@app.route('/deleteTarget', methods=["GET", "POST"])
def deleteTarget():
    idx = int(request.args.get('idx', None))
    session['df'] = targs.deleteTarget(session['df'], idx)
    outp = targs.toJsonWithInfo(session['params'], session['df'])
    return outp


@check_session
@app.route('/resetSelection', methods=["GET", "POST"])
def resetSelection():
    df = session['df']
    prms = session['params']
    df.selected = df.loadselected
    outp = targs.toJsonWithInfo(prms, df)
    return outp


@check_session
@app.route('/getTargetsAndInfo')
def getTargetsAndInfo():
    try:
        logger.debug('newdf/getTargetsAndInfo')
        newdf = calcmask.genObs(session['df'], session['params'])
        newdf = targs.markInside(newdf)
        outp = targs.toJsonWithInfo(session['params'], newdf)
    except Exception as err:
        logger.error(f'Exception {err}')
        outp = ''
    return outp


@check_session
@app.route('/generateSlits', methods=["GET", "POST"])
def generateSlits():
    df = targs.markInside(session['df'])
    newdf = calcmask.genSlits(df, session['params'], auto_sel=True)
    session['df'] = newdf
    outp = targs.toJsonWithInfo(session['params'], newdf)
    return outp


## Performs auto-selection of slits##
@check_session
@app.route('/recalculateMask', methods=["GET", "POST"])
def recalculateMask():
    df = targs.markInside(session['df'])
    newdf = calcmask.genSlits(df, session['params'], auto_sel=True)
    session['df'] = newdf
    outp = targs.toJsonWithInfo(session['params'], newdf)
    return outp


@check_session
@app.route('/saveMaskDesignFile', methods=["GET", "POST"])
def saveMaskDesignFile():  # should only save current rather than re-running everything!
    df = targs.markInside(session['df'])
    params = session['params'] 

    pdb.set_trace()
    newdf = calcmask.genMaskOut(df, params)
    plot.makeplot(params['OutputFitsfd'][0])
    session['df'] = newdf
    outp = targs.toJsonWithInfo(params, newdf)
    return outp


# Update Params Button, Load Targets Button
# @check_session(params=['params', 'file'])
@app.route('/sendTargets2Server', methods=["GET", "POST"])
def sendTargets2Server():
    prms = request.form.to_dict(flat=False)
    fh = []
    session['params'] = prms 
    uploaded_file = request.files['targetList']
    if uploaded_file.filename != '':
        for line in uploaded_file.stream:
            fh.append(line.strip().decode('UTF-8'))

        session['file'] = fh
        df = targs.readRaw(session['file'], prms)
        # Only backup selected targets on file load.
        df['loadselected'] = df.selected
        session['df'] = df

        #generate slits
        newdf = calcmask.genObs(session['df'], session['params'])
        df = targs.markInside(newdf)
        newdf = calcmask.genSlits(df, session['params'], auto_sel=True)
        session['df'] = newdf
        outp = targs.toJsonWithInfo(session['params'], newdf)
    return outp

# Update Params Button
@app.route('/updateParams4Server', methods=["GET", "POST"])
def updateParams4Server():
    prms = request.form.to_dict(flat=False)
    session['params'] = prms
    return ''


# Loads original params
@app.route('/getConfigParams')
def getConfigParams():
    paramData = readparams()
    logger.debug(f'params: {paramData}')
    session['params'] = paramData
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
        # a list of (x,y,flag), polygon vertices
        mask = ml.MaskLayouts[instrument]
        # list of (x, y, w, h, ang), boxes
        guiderFOV = ml.GuiderFOVs[instrument]
        badColumns = ml.BadColumns[instrument]  # list of lines, as polygons
        # might need to be jsonified
        return {"mask": mask, "guiderFOV": guiderFOV, "badColumns": badColumns}
    except Exception as err:
        logger.error(err)
        return ((0, 0, 0),)


@app.route('/')
def home():
    return render_template('dt.html')


@app.route("/targets", methods=["GET", "POST"])
def LoadTargets():
    return


if __name__ == '__main__':
    # t = Timer(1, launchBrowser, ['localhost', 9302, '/'])
    # t.start()
    app.run(host='localhost', port=9302, debug=True, use_reloader=False)
