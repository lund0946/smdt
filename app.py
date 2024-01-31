from datetime import timedelta
from flask import Flask, render_template, request, session, jsonify
from threading import Timer
from flask.logging import default_handler
from flask_session import Session
import webbrowser
import maskLayouts as ml
import json
import re
import targs
import calcmask
import plot
import logging
from logging import FileHandler, StreamHandler
import pdb

from utils import schema, validate_params

logger = logging.getLogger('smdt')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
app.config.from_pyfile('config.ini')
Session(app)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
    hours=app.config['PERMANENT_SESSION_LIFETIME'])




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

    newdf = calcmask.genMaskOut(df, params)
    plot.makeplot(params['OutputFitsfd'][0])
    session['df'] = newdf
    outp = targs.toJsonWithInfo(params, newdf)
    return outp


# Update Params Button, Load Targets Button
# @check_session(params=['params', 'file'])
@app.route('/sendTargets2Server', methods=["GET", "POST"])
def sendTargets2Server():
    prms = request.form.to_dict()
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

        # generate slits
        newdf = calcmask.genObs(session['df'], session['params'])
        df = targs.markInside(newdf)
        newdf = calcmask.genSlits(df, session['params'], auto_sel=True)
        session['df'] = newdf
        outp = targs.toJsonWithInfo(session['params'], newdf)
    return outp


@app.route('/updateParams4Server', methods=["GET", "POST"])
def updateParams4Server():
    prms = request.json
    ok, prms = validate_params(prms)
    if not ok:
        return [str(x) for x in prms ]
    session['params'] = prms
    return 'OK'


# Loads original params
@app.route('/getSchema')
def getConfigParams():
    logger.debug(f'Param Schema: {schema}')
    return jsonify(schema)


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
