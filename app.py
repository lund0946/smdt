from datetime import timedelta
from flask import Flask, render_template, request, session
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
from logging import FileHandler

logger = logging.getLogger('smdt')
logger.setLevel(logging.DEBUG)
logger.addHandler(default_handler)
fh = FileHandler('smdt.log')
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

    for p in params:
        if p == 'MaskIdfd':
            params[p] = [int(params[p][0])]
        elif p == 'MinSlitLengthfd' or p == 'MinSlitSeparationfd' or p == 'SlitWidthfd' or p == 'AlignBoxSizefd' or p == 'BlueWaveLengthfd' or p == 'RedWaveLengthfd' or p == 'CenterWaveLengthfd' or p == 'Temperaturefd' or p == 'Pressurefd' or p == 'MaskPAfd' or p == 'SlitPAfd' or p == 'MaskMarginfd' or p == 'HourAnglefd':
            params[p] = [float(params[p][0])]
        else:
            continue

    return params


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


@app.route('/setColumnValue', methods=["GET", "POST"])
def setColumnValue():
    global df
    global prms
    targets = df
    params = prms
    values = json.loads(request.data.decode().split('=')[2].split('&')[0])
    column = request.data.decode().split('=')[1].split('&')[0]
    df = targs.updateColumn(targets, column, values)
    outp = targs.toJsonWithInfo(params, df)
    return outp


@app.route('/updateTarget', methods=["GET", "POST"])
def updateTarget():
    global df
    global prms
    targets = df
    values = json.loads(request.data.decode().split('=')[1].split('}&')[0]+'}')
    df, idx = targs.updateTarget(targets, values)
    outp = targs.toJsonWithInfo(prms, df)
    tgs = json.loads(outp)

    outp = {**tgs, **{'idx': idx}}
    return outp


@app.route('/deleteTarget', methods=["GET", "POST"])
def deleteTarget():
    global df
    global prms
    targets = df
    idx = int(request.args.get('idx', None))
    df = targs.deleteTarget(targets, idx)
    outp = targs.toJsonWithInfo(prms, df)
    return outp


@app.route('/resetSelection', methods=["GET", "POST"])
def resetSelection():
    global df
    global prms
    df.selected = df.loadselected
    outp = targs.toJsonWithInfo(prms, df)
    return outp


@app.route('/getTargetsAndInfo')
def getTargetsAndInfo():
    global prms
    params = prms
    global df
    try:
        logger.debug('newdf/getTargetsAndInfo')
        newdf = calcmask.genObs(df, params)
        newdf = targs.markInside(newdf)
        outp = targs.toJsonWithInfo(params, newdf)
    except Exception as err:
        logger.error(f'Exception {err}')
        outp = ''
    return outp


@app.route('/generateSlits', methods=["GET", "POST"])
def generateSlits():
    global df
    global prms
    params = prms
    df = targs.markInside(df)
    newdf = calcmask.genSlits(df, params, auto_sel=True)
    df = newdf
    outp = targs.toJsonWithInfo(params, newdf)
    return outp


## Performs auto-selection of slits##
@app.route('/recalculateMask', methods=["GET", "POST"])
def recalculateMask():
    global df
    global prms
    params = prms
    df = targs.markInside(df)
    newdf = calcmask.genSlits(df, params, auto_sel=True)
    df = newdf
    outp = targs.toJsonWithInfo(params, newdf)
    return outp


@app.route('/saveMaskDesignFile', methods=["GET", "POST"])
def saveMaskDesignFile():  # should only save current rather than re-running everything!
    global df
    global prms
    params = prms
    df = targs.markInside(df)

    newdf = calcmask.genMaskOut(df, params)
    plot.makeplot(params['OutputFitsfd'][0])
    df = newdf

    outp = targs.toJsonWithInfo(params, newdf)
    return outp


# Update Params Button, Load Targets Button
@app.route('/sendTargets2Server', methods=["GET", "POST"])
def sendTargets2Server():
    global prms
    prms = request.form.to_dict(flat=False)
    params = prms
    fh = []
    session['params'] = params
    prms = params
    uploaded_file = request.files['targetList']
    if uploaded_file.filename != '':
        input = uploaded_file.stream
        for line in input:
            fh.append(line.strip().decode('UTF-8'))

        session['file'] = fh
        global df
        df = targs.readRaw(session['file'], prms)
        # Only backup selected targets on file load.
        df['loadselected'] = df.selected
    return ''

# Update Params Button
@app.route('/updateParams4Server', methods=["GET", "POST"])
def updateParams4Server():
    global prms
    prms = request.form.to_dict(flat=False)
    session['params'] = prms
    return ''


# Loads original params
@app.route('/getConfigParams')
def getConfigParams():
    global prms
    paramData = readparams()
    prms = paramData
    logger.debug(f'params: {paramData}')
    session['params'] = paramData
    prms = paramData
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
    t = Timer(1, launchBrowser, ['localhost', 9302, '/'])
    t.start()
    app.run(host='localhost', port=9302, debug=True, use_reloader=False)
