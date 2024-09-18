from datetime import timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response
from flask.logging import default_handler
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
import tarfile
import tempfile


from utils import schema, validate_params, toSexagecimal

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


app = Flask(__name__)
app.config.from_pyfile('config.ini')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
    hours=app.config['PERMANENT_SESSION_LIFETIME'])


@app.route('/setColumnValue', methods=["GET", "POST"])
def setColumnValue():
    targetList = request.json['targets']
    values = request.json['value']
    column = request.json['column']
    targetList = targs.update_column(targetList, column, values)
    return {'status': 'OK', 'targets': targetList}


@app.route('/updateTarget', methods=["GET", "POST"])
def updateTarget():
    values = request.json['values']
    targetList = request.json['targets']
    params = request.json['params']
    targetList, idx = targs.update_target(targetList, values)
    outp = targs.to_json_with_info(params, targetList)
    outp = {**outp, 'idx': idx, "info": targs.getROIInfo(params)}
    return outp


@app.route('/updateSelection', methods=["GET", "POST"])
def updateSelection():
    targetList = request.json['targets']
    values = request.json['values']
    params = request.json['params']
    targetList, idx = targs.update_target(targetList, values)
    outp = targs.to_json_with_info(params, targetList)
    outp = {**outp, 'idx': idx, "info": targs.getROIInfo(params)}
    return outp


@app.route('/deleteTarget', methods=["GET", "POST"])
def deleteTarget():
    idx = request.json['idx']
    targetList = request.json['targets']
    params = request.json['params']
    targetList.pop(idx)
    outp = targs.to_json_with_info(params, targetList)
    outp = {**outp, 'idx': idx, "info": targs.getROIInfo(params)}
    return outp


@app.route('/resetSelection', methods=["GET", "POST"])
def resetSelection():
    targetList = request.json['targets']
    params = request.json['params']
    targetList = [{**target, 'selected': target['localselected']}
                  for target in targetList]
    outp = targs.to_json_with_info(params, targetList)
    outp = {**outp, "info": targs.getROIInfo(params)}
    return outp


@app.route('/generateSlits', methods=["GET", "POST"])
def generateSlits():
    targetList = request.json['targets']
    params = request.json['params']
    targetList = targs.mark_inside(targetList)
    targetList, slit, site= calcmask.genSlits(targetList, params, auto_sel=True, returnSlitSite=True)
    outp = targs.to_json_with_info(params, targetList)
    return outp


## Performs auto-selection of slits##

@app.route('/recalculateMask', methods=["GET", "POST"])
def recalculateMask():
    targetList = targs.mark_inside(request.json['targets'])
    targetList = calcmask.genSlits(
        targetList, request.json['params'], auto_sel=True)
    outp = targs.to_json_with_info(request.json['params'], targetList)
    outp = { **outp, "info": targs.getROIInfo(request.json['params'])}
    return outp


@app.route('/saveMaskDesignFile', methods=["GET", "POST"])
def saveMaskDesignFile():  # should only save current rather than re-running everything!
    try:
        targetList = targs.mark_inside(request.json['targets'])
        params = request.json['params']
        outp = {'status': 'OK', **targs.to_json_with_info(params, targetList)}
        # with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdirname = tempfile.mkdtemp()
        mdfName = os.path.join(tmpdirname, params['OutputFits']).replace('.fits', '')
        gzName = os.path.join(tmpdirname, mdfName + '.tar.gz')
        names = [f'{mdfName}.fits', f'{mdfName}.out',
                 f'{mdfName}.png', f'{mdfName}.json']
        mdf, targetList = calcmask.gen_mask_out(targetList, params)
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
    prms = request.json['formData']
    # prms = {k.replace('fd', ''): v for k, v in prms.items()}
    fh = [line for line in request.json['file'].split('\n') if line]
    targetList = targs.readRaw(fh, prms)
    # Only backup selected targets on file load.
    targetList = [{**target, 'localselected': target['selected']}
                  for target in targetList]

    # generate slits
    targetList = calcmask.gen_obs(prms, targetList)
    targetList = targs.mark_inside(targetList)
    targetList = calcmask.genSlits(targetList, prms, auto_sel=True)
    # raMedian = np.median([target['raHour'] for target in targetList])
    # decMedian = np.median([target['decDeg'] for target in targetList])
    # prms = {**prms,
    #         'InputRA': toSexagecimal(raMedian),
    #         'InputDEC': toSexagecimal(decMedian),
    #         }

    outp = targs.to_json_with_info(prms, targetList)
    return outp


@app.route('/updateParams4Server', methods=["GET", "POST"])
def updateParams4Server():
    prms = request.json['params']
    targetList = request.json['targets']
    ok, prms = validate_params(prms)
    if not ok:
        return [str(x) for x in prms]
    outp = targs.to_json_with_info(prms, targetList)
    outp = {**outp, 'status': 'OK'}
    return outp


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
