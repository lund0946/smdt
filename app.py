from flask import Flask, render_template, request, jsonify, send_from_directory, make_response, session
from flask.logging import default_handler
from flask_session import Session
from flask_cors import CORS
import webbrowser
import numpy as np
import maskLayouts as ml
import os
import json
import numpy as np
import targs
import calcmask
import json
import plot
import logging
from logging import FileHandler, StreamHandler
from threading import Timer
import tarfile
import tempfile
import logging
from functools import wraps
from utils import schema, validate_params
import pdb



logger = logging.getLogger('smdt')
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger.setLevel(logging.INFO)
logger.addHandler(default_handler)
st = StreamHandler()
st.setLevel(logging.INFO)
st.setFormatter(formatter)
fh = FileHandler('smdt.log')
fh.setFormatter(formatter)
logger.addHandler(fh)


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_function_call(func):
    """Decorator to log function calls"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logging.info(f"Function '{func.__name__}' called with args: {args} kwargs: {kwargs}")
        result = func(*args, **kwargs)
        logging.info(f"Function '{func.__name__}' returned: {result}")
        return result
    return wrapper


def launchBrowser(host, portnr, path):
    webbrowser.open(f"http://{host}:{portnr}/{path}", new=1)


app = Flask(__name__)
app.config.from_pyfile('config.py')
Session(app)
CORS(app, supports_credentials=True)


@app.before_request
def log_request():
    logging.info(f"Request made to: {request.path} with method {request.method}")


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
    values = request.json['value']
    column = request.json['column']
    logger.info(f"Setting column {column} to value {values}")
    logger.info(f"session keys: {session.keys()}")
    logger.info(f"session targetList: {session.get('targetList')}")
    session['targetList'] = targs.update_column(session['targetList'], column, values)
    session.modified=True
    return {'status': 'OK', 'targets': session['targetList']}


@app.route('/updateTarget', methods=["GET", "POST"])
def updateTarget():
    values = request.json['values']
    session['targetList'], idx = targs.update_target(session['targetList'], values)
    session.modified=True
    outp = targs.to_json_with_info(session['params'], session['targetList'])
    return {**outp, 'idx': idx, "info": targs.getROIInfo(session['params'])}


@app.route('/updateSelection', methods=["GET", "POST"])
def updateSelection():
    values = request.json['values']
    session['targetList'], idx = targs.update_target(session['targetList'], values)
    session.modified=True
    outp = targs.to_json_with_info(session['params'], session['targetList'])
    return {**outp, 'idx': idx, "info": targs.getROIInfo(session['params'])}


@app.route('/deleteTarget', methods=["GET", "POST"])
def deleteTarget():
    idx = request.json['idx']
    if idx < len(session['targetList']):
        session['targetList'].pop(idx)
        session.modified=True
    else:
        logger.debug('Invalid idx. Not deleting')
    outp = targs.to_json_with_info(session['params'], session['targetList'])
    outp = {**outp, 'idx': idx, "info": targs.getROIInfo(session['params'])}
    return outp


@app.route('/resetSelection', methods=["GET", "POST"])
def resetSelection():
    session['targetList'] = [{**target, 'selected': target['localselected']}
                  for target in session['targetList']]
    session.modified=True
    outp = targs.to_json_with_info(session['params'], session['targetList'])
    return {**outp, "info": targs.getROIInfo(session['params'])}


@app.route('/generateSlits', methods=["GET", "POST"])
def generateSlits():
    session['targetList'] = targs.mark_inside(session['targetList'])
    session['targetList'], slit, site= calcmask.gen_slits(session['targetList'], session['params'], auto_sel=False, returnSlitSite=True)  #auto_sel=False, since everything is already selected by this point?
    session.modified=True
    outp = targs.to_json_with_info(session['params'], session['targetList'])
    return outp


## Performs auto-selection of slits##

@app.route('/recalculateMask', methods=["GET", "POST"])
def recalculateMask():
    session['targetList'] = targs.mark_inside(session['targetList'])
    session['targetList'] = calcmask.gen_slits(
        session['targetList'], session['params'], auto_sel=True)
    session.modified=True
    outp = targs.to_json_with_info(session['params'], session['targetList'])
    return { **outp, "info": targs.getROIInfo(session['params'])}
    


@app.route('/saveMaskDesignFile', methods=["GET", "POST"])
def saveMaskDesignFile():  # should only save current rather than re-running everything!
    try:
        session['targetList'] = targs.mark_inside(session['targetList'])
        session.modified=True
        outp = {'status': 'OK', **targs.to_json_with_info(session['params'], session['targetList'])}
        # with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdirname = tempfile.mkdtemp()
        mdfName = os.path.join(tmpdirname, session['params']['OutputFits']).replace('.fits', '')
        gzName = os.path.join(tmpdirname, mdfName + '.tar.gz')
        names = [f'{mdfName}.fits', f'{mdfName}.out',
                 f'{mdfName}.png', f'{mdfName}.json']
        mdf, session['targetList'] = calcmask.gen_mask_out(session['targetList'], session['params'])
        mdf.writeTo(names[0])
        mdf.writeOut(names[1])
        plt = plot.makeplot(names[0])
        plt.savefig(names[2])
        with open(names[3], 'w') as f:
            json.dump(outp, f, ensure_ascii=False, indent=4)
        with tarfile.open(gzName, "w") as tar:
            for name in names:
                tar.add(name, arcname=os.path.basename(name))
            tar.close()
        fname = os.path.basename(gzName)
        return send_from_directory(directory=tmpdirname,
                                   path=fname,
                                   as_attachment=True)
    except Exception as err:
        logger.error(f'Exception {err}')
        response = make_response(
            jsonify({'status': 'ERR', 'msg': str(err)}), 500)
        response.headers["X-Exception"] = str(err)
        return response

# Update Params Button, Load Targets Button
@app.route('/sendTargets2Server', methods=["GET", "POST"])
def sendTargets2Server():
    filename = request.json.get('filename')
    if not filename:
        return
    session['params'] = request.json['formData']
    # need to set number params to floats
    for key, val in session['params'].items():
        try:
            if 'number' in schema['properties'].get(key,{}).get('type', []):
                session['params'][key] = float(val)
        except Exception as err:
            pdb.set_trace()
            logger.warning(f'Failed to convert {key} to float: {err}')
            pass
    fh = [line for line in request.json['file'].split('\n') if line]
    session['targetList'] = targs.readRaw(fh, session['params'])
    # Only backup selected targets on file load.
    session['targetList'] = [{**target, 'localselected': target['selected']}
                  for target in session['targetList']]

    # generate slits
#    session['targetList'] = calcmask.gen_obs(session['targetList'], session['params'])
    session['targetList'] = targs.mark_inside(session['targetList'])
    session['targetList'] = calcmask.gen_slits(session['targetList'], session['params'], auto_sel=False)
    session['test'] = 'ok, i\'m set'
    session.modified=True

    outp = targs.to_json_with_info(session['params'], session['targetList'])
    outp = {**outp, 'status': 'OK'}
    return outp

@app.route('/updateParams4Server', methods=["GET", "POST"])
def updateParams4Server():
    session['params'] = request.json['formData']
    print(session['params'])
    #ok, session['params'] = validate_params(session['params'])
    ok=True
    session.modified=True
    if not ok:
        return [str(x) for x in session['params']]

    if 'targetList' not in session:
        session['targetList']=[]
    session['targetList'] = targs.mark_inside(session['targetList'])
    session['targetList'] = calcmask.gen_slits(session['targetList'], session['params'], auto_sel=False)
    outp = targs.to_json_with_info(session['params'], session['targetList'])
    outp = {**outp, 'status': 'OK'}
    return outp


# Loads original params
@app.route('/getSchema')
def getConfigParams():
    logger.debug(f'Param Schema: {schema}')
    session['got schema'] = True
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
