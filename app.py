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


def check_session(params=('targetList', 'params')):
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
    targetList = session['targetList']
    values = json.loads(request.data.decode().split('=')[2].split('&')[0])
    column = request.data.decode().split('=')[1].split('&')[0]
    session['targetList'] = targs.update_column(targetList, column, values)
    outp = targs.to_json_with_info(session['params'], session['targetList'])
    return outp


@check_session
@app.route('/updateTarget', methods=["GET", "POST"])
def updateTarget():
    targetList = session['targetList']
    values = json.loads(request.data.decode().split('=')[1].split('}&')[0]+'}')
    session['targetList'], idx = targs.update_target(targetList, values)
    outp = targs.to_json_with_info(session['params'], session['targetList'])
    outp = {**outp, **{'idx': idx}}
    return outp


@check_session
@app.route('/deleteTarget', methods=["GET", "POST"])
def deleteTarget():
    idx = int(request.args.get('idx', None))
    targetList = session['targetList']
    targetList.pop(idx)
    session['targetList'] = targetList
    outp = targs.to_json_with_info(session['params'], session['targetList'])
    return outp


@check_session
@app.route('/resetSelection', methods=["GET", "POST"])
def resetSelection():
    targetList = session['targetList']
    prms = session['params']
    targetList = [ {**target, 'selected': target['localselected']} for target in targetList]
    outp = targs.to_json_with_info(prms, targetList)
    return outp


@check_session
@app.route('/getTargetsAndInfo')
def getTargetsAndInfo():
    try:
        logger.debug('targetList/getTargetsAndInfo')
        targetList = calcmask.gen_obs(session['targetList'], session['params'])
        targetList = targs.mark_inside(targetList)
        outp = targs.to_json_with_info(session['params'], targetList)
    except Exception as err:
        logger.error(f'Exception {err}')
        outp = ''
    return outp


@check_session
@app.route('/generateSlits', methods=["GET", "POST"])
def generateSlits():
    targetList = targs.mark_inside(session['targetList'])
    targetList = calcmask.genSlits(targetList, session['params'], auto_sel=True)
    session['targetList'] = targetList 
    outp = targs.to_json_with_info(session['params'], targetList)
    return outp


## Performs auto-selection of slits##
@check_session
@app.route('/recalculateMask', methods=["GET", "POST"])
def recalculateMask():
    targetList = targs.mark_inside(session['targetList'])
    targetList = calcmask.genSlits(targetList, session['params'], auto_sel=True)
    session['targetList'] = targetList 
    outp = targs.to_json_with_info(session['params'], targetList)
    return outp


@check_session
@app.route('/saveMaskDesignFile', methods=["GET", "POST"])
def saveMaskDesignFile():  # should only save current rather than re-running everything!
    targetList = targs.mark_inside(session['targetList'])
    params = session['params']

    targetList = calcmask.genMaskOut(targetList , params)
    plot.makeplot(params['OutputFits'][0])
    session['targetList'] = targetList 
    outp = targs.to_json_with_info(params, targetList)
    return outp


# Update Params Button, Load Targets Button
# @check_session(params=['params', 'file'])
@app.route('/sendTargets2Server', methods=["GET", "POST"])
def sendTargets2Server():
    prms = request.form.to_dict()
    prms = {k.rstrip('fd'): v for k, v in prms.items()}
    fh = []
    session['params'] = prms
    uploaded_file = request.files['targetList']
    if uploaded_file.filename != '':
        for line in uploaded_file.stream:
            fh.append(line.strip().decode('UTF-8'))

        session['file'] = fh
        targetList = targs.readRaw(session['file'], prms)
        # Only backup selected targets on file load.
        targetList = [ {**target, 'localselected': target['selected']} for target in targetList]
        session['targetList'] = targetList 

        # generate slits
        targetList = calcmask.gen_obs(session['targetList'], session['params'])
        targetList = targs.mark_inside(targetList)
        targetList = calcmask.genSlits(targetList , session['params'], auto_sel=True)
        session['targetList '] = targetList 
        outp = targs.to_json_with_info(session['params'], targetList)
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
