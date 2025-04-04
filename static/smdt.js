/*
Main entry point for the Slitmask Design Tool.
Invoked by body.onload.
This module interfaces with the server,
while the canvasShow object renders the targets and the mask.
*/

function SlitmaskDesignTool() {
	var self = this;

	self.xAsPerPixel = 1;
	self.yAsPerPixel = 1;


	function E(n) {
		return document.getElementById(n);
	}

	self.buildParamTable = function (schema) {
		// params
		let buf = Array();
		let txt;
		buf.push('<table id="paramTable">');
		let sortedProps = {}
		for (let key of schema.required) {
			sortedProps[key] = schema.properties[key]
		}
		const params = undefined;
		for (let [key, props] of Object.entries(sortedProps)) {
			const type = props.type.includes('number') ? 'number' : 'text';
			const value = params ? params[key] : props.default;
			txt = `<tr><td> ${props.label} :<td><input ftype=${type} id="${key}fd" name="${key}" value="${value}"><td>${props.description}`;
			buf.push(txt);
		}
		buf.push('</table>');
		E('paramTableDiv').innerHTML = buf.join('');
	};


	self.loadConfigParams = function () {
		function schema_callback(schema) {
			const filename = E('targetList');
			const msg = !filename.value ? 'Please select target list file to load' : 'Ready to load targets';
			self.setStatus(msg);
			self.buildParamTable(schema);

			//init
			self.canvasShow = new CanvasShow('canvasDiv', 'zoomCanvasDiv');
			self.canvasShow.setShowPriorities(E('minPriority').value, E('maxPriority').value);
			self.loadMaskLayout();
			recalculate_callback()
			}
			ajaxCall('getSchema', {}, schema_callback);
	};

	self.setStatus = function (msg) {
		self.statusDiv.innerHTML = msg;
	}


	self.generate_slitmask_callback = function (data) {
		self.canvasShow.slitsReady = false;
		if (!data) return;
		if (!data.targets) return;
		self.canvasShow.slitsReady = false;
		self.updateLoadedTargets(data);
                self.redraw()
	};

	self.sendTargets2Server = function () {
		// The browser loads the targets and sends them to the server.
		// The server responds with targetList.
		// Slitmask is then generated.
        self.loadAll()
		const filename = E('targetList');
		if (!filename.value) {
			self.setStatus('Please select target list file to load');
			return;
		}

		const form2 = E('form2');
		const formData = new FormData(form2);
		let params = {}
		formData.forEach((value, key) => params[key] = value);
		const fr = new FileReader()

		let data = {
			'formData': params,
			'filename': filename.files[0].name,
			'file': filename.files[0]
		}
		fr.addEventListener(
			"load",
			() => {
				data['file'] = fr.result;
				self.setStatus("Loading ...");
				ajaxPost('sendTargets2Server', data, self.generate_slitmask_callback);
			},
			false,
		);

		fr.readAsText(filename.files[0]);
	};


        self.param_update_callback = function (data) {
                        if (!data.status?.includes('OK')) {
                                alert(data)
                        }
                        self.generate_slitmask_callback(data);
        };

	self.sendParamUpdate = function () {
		self.setStatus("Updating ...");
		const form2 = E('form2');
		self.setStatus("Loading ...");
		let formJson = {};
		Array.from(form2.elements).forEach((input) => {
			if (input.getAttribute('ftype')) {
				if (input.getAttribute('ftype') == 'number') {
					formJson[input.name] = Number(input.value);
				}
				else {
					formJson[input.name] = input.value.trim();
				}
			}
		});


		let data = {
			params: formJson,
		}
		ajaxPost('updateParams4Server', data, self.param_update_callback);
	};

	self.loadMaskLayout = function () {
		function callback(data) {
			self.canvasShow.setMaskLayout(data.mask, data.guiderFOV, data.badColumns);
			return;
		}

		ajaxCall("getMaskLayout", { 'instrument': 'deimos' }, callback);
	};

	self.updateLoadedTargets = function (data) {
		// Called when targets are loaded from server
		if (!data) return;
		if (!data.targets) return;

		self.dssInfo = data.info;

		self.setStatus("Drawing targets ...");
		E('minPriority').value = 0;

		// dssPlatescale in arcsec/micron
		// xpsize in micron/pixel
		let info = data.info;
		let platescl = info['platescl'] // arcsec/micron
		self.xAsPerPixel = platescl * info['xpsize'] / 1000; // arcsec/pixel
		self.yAsPerPixel = platescl * info['ypsize'] / 1000; // arcsec/pixel
		self.setStatus("OK");
		let cs = self.canvasShow;

		cs.xAsPerPixel = self.xAsPerPixel;
		cs.yAsPerPixel = self.yAsPerPixel;
		cs.northAngle = info['northAngle'] * 1;
		cs.eastAngle = info['eastAngle'] * 1;
		cs.centerRaDeg = info['centerRADeg'] * 1;
		cs.centerDecDeg = info['centerDEC'] * 1;
		cs.positionAngle = 0;
		cs.origPA = info['positionAngle'] * 1;
		cs.currRaDeg = cs.centerRaDeg;
		cs.currDecDeg = cs.centerDecDeg;

		cs.setShowPriorities(E('minPriority').value, E('maxPriority').value);
		cs.setTargets(data.targets);
		cs.setGaps(data.xgaps);

		cs.resetDisplay();
		cs.resetOffsets();
		self.redraw();
		self.canvasShow.selectTargetByIndex(self.canvasShow.selectedTargetIdx);
	};

	self.reloadTargets = function (newIdx, info = []) {

		let data = {
			'info': info
		}
		self.updateLoadedTargets(data);
		self.canvasShow.selectTargetByIndex(newIdx);
	};


	self.loadAll = function () {
		self.canvasShow.clearTargetSelection();
		self.canvasShow.slitsReady = 0;
		self.reloadTargets(0);
	};

	self.redraw = function () {
		self.canvasShow.redrawTxImage();
	};

	self.resetDisplay1 = function () {
		// Refit and redraw
		self.canvasShow.resetDisplay();
		self.redraw();
	};

	self.resetOffsets1 = function () {
		self.canvasShow.resetOffsets();
		self.redraw();
	};

	self.setMinPcode = function () {
		self.canvasShow.setShowPriorities(E('minPriority').value, E('maxPriority').value);
		self.canvasShow.redrawTxImage();
	};

	self.showHideParams = function (evt) {
		let curr = this.value;
		let elm = E('paramTableDiv');
		if (curr == 'Show Parameters') {
			this.value = 'Hide Parameters';
			with (elm.style) {
				visibility = 'visible';
				display = 'block';
			}
		} else {
			this.value = 'Show Parameters';
			with (elm.style) {
				visibility = 'hidden';
				display = 'none';
			}
		}
	};


	self.updateParams = function (evt) {
		// Updates params.
		// Sends params to server
		let maskpa = Number(E('MaskPAfd').value)
		let form2 = E('form2');
		form2.submit();
	};






	self.setSlitsPA = function (evt) {
		let pa = Number(E('SlitPAfd').value);
		let tgs = self.canvasShow.targets;
		let ntgs = tgs.length;
		let i;
		for (i = 0; i < ntgs; ++i) {
			if (tgs[i].pcode <= 0) continue;
			tgs[i].slitLPA = pa;
		}
		self.canvasShow.reDrawTable();
		self.redraw();

		let colName = 'slitLPA';
		let value = pa;
		let input = {
			'column': colName,
			'value': value,
		};
		ajaxPost('setColumnValue', input, self.setColumnValueCallback);
	};

	self.setColumnValueCallback = function (data) {
		if (data.status != 'OK') {
			alert(data.msg);
		}
	}

	self.setSlitsLength = function (evt) {
		let asize = Number(E('AlignBoxSizefd').value);
		let ahalf = 0.5 * asize;
		let halfLen = 0.5 * Number(E('MinSlitLengthfd').value);
		let tgs = self.canvasShow.targets;
		let ntgs = tgs.length;
		let i;
		for (i = 0; i < ntgs; ++i) {
			if (tgs[i].pcode <= 0) {
				tgs[i].length1 = ahalf;
				tgs[i].length2 = ahalf;
			}
			else {
				tgs[i].length1 = halfLen;
				tgs[i].length2 = halfLen;
			}
		}
		self.canvasShow.reDrawTable();
		self.redraw();

		let colName = 'length1';
		let value = halfLen;
		let input = {
			'column': colName,
			'value': value,
		};
		ajaxPost('setColumnValue', input, self.setColumnValueCallback);

		colName = 'length2';
		input['column'] = colName;
		ajaxPost('setColumnValue', input, self.setColumnValueCallback);
	};

	self.setSlitsWidth = function (evt) {
		let width = Number(E('SlitWidthfd').value);
		let tgs = self.canvasShow.targets;
		let ntgs = tgs.length;
		let i;
		for (i = 0; i < ntgs; ++i) {
			if (tgs[i].pcode <= 0) continue;
			tgs[i].slitWidth = width;
		}
		self.canvasShow.reDrawTable();
		self.redraw();

		let colName = 'slitWidth';
		let value = width;
		let input = {
			'column': colName,
			'value': value,
		};
		ajaxPost('setColumnValue', input, self.setColumnValueCallback);
	};

	self.clearSelection = function (evt) {
		let tgs = self.canvasShow.targets;
		let ntgs = tgs.length;
		let i;
		for (i = 0; i < ntgs; ++i) {
			if (tgs[i].pcode <= 0) continue;
			tgs[i].selected = 0;
		}
		self.canvasShow.reDrawTable();
		self.canvasShow.slitsReady = 0;
		self.redraw();

		let column = 'selected';
		const value = 0;
		let input = {
			'column': column,
			'value': value,
		};
		ajaxPost('setColumnValue', input, self.setColumnValueCallback);
	};


	self.resetSelection = function (evt) {
		function resetSelectionCallback() {
			self.reloadTargets(0);
		}

		ajaxPost("resetSelection", data, resetSelectionCallback);
	};


	self.recalculateMaskHelper = function (callback) {
		// Send targets that are inside mask to server.
		// Retrieve selected mask information and display.
		let cs = self.canvasShow;
		if (!cs) {
			alert("No targets available");
			return;
		}
		cs.centerRaDeg = cs.currRaDeg;
		cs.centerDecDeg = cs.currDecDeg;

		let params = {
		};
		ajaxPost('recalculateMask', params, callback);
	};

	self.recalculate_callback = function (data) {
		self.canvasShow.slitsReady = false;
		if (!data) return;
		if (!data.targets) console.warn('no targets...');

		self.canvasShow.setTargets(data.targets);
		self.redraw();
	};

	self.recalculateMask = function (evt) {
		self.recalculateMaskHelper(self.recalculate_callback);
	};


	self.generateSlitsHelper = function (callback) {
		// Send targets that are inside mask to server.
		// Retrieve selected mask information and display.
		let cs = self.canvasShow;
		if (!cs) {
			alert("No targets available");
			return;
		}
		cs.centerRaDeg = cs.currRaDeg;
		cs.centerDecDeg = cs.currDecDeg;

		let data = {
		}
		ajaxPost('generateSlits', data, callback);
	};

	self.generateSlits = function (evt) {
		self.setStatus("Loading ...");
		self.generateSlitsHelper(self.generate_slitmask_callback);
	};


	self.updateColumn = function (evt) {
		// Updates an existing target column with a set value.
		function callback(data) {
			self.reloadTargets(idx);
			self.canvasShow.selectedTargetIdx = idx;
		}
		// Sends new target info to server
		let idx = self.canvasShow.selectedTargetIdx;
		let prior = Number(E('targetPrior').value);
		let selected = Number(E('targetSelect').value);
		let slitLPA = Number(E('targetSlitPA').value);
		let slitWidth = Number(E('targetSlitWidth').value);
		let length1 = Number(E('targetLength1').value);
		let length2 = Number(E('targetLength2').value);
		let tname = E("targetName").value;
		let targetRA = E("targetRA").value;
		let targetDEC = E("targetDEC").value;
		let targetMagn = E("targetMagn").value;
		let targetBand = E('targetBand').value;

		let params = {
			'idx': idx, 'raSexa': targetRA, 'decSexa': targetDEC, 'eqx': 2000,
			'mag': targetMagn, 'pBand': targetBand,
			'prior': prior, 'selected': selected, 'slitLPA': slitLPA, 'slitWidth': slitWidth,
			'len1': length1, 'len2': length2, 'targetName': tname
		};
		ajaxPost('updateColumn', { 'values': JSON.stringify(params) }, callback);
	};


	self.selectToggle = function (evt) {
		// Updates an existing or adds a new target.
		function selectToggleCallback(data) {
			self.reloadTargets(idx, data.info);
			self.canvasShow.selectedTargetIdx = i;
			self.canvasShow.reDrawTable();
			self.redraw();
		}
		// Sends new target info to server
		let idx = self.canvasShow.selectedTargetIdx;
		let prior = Number(E('targetPrior').value);
		let sel = Number(E('targetSelect').value);
		let selected;
		if (sel > 0) selected = 0;
		else selected = 1;

		let slitLPA = Number(E('targetSlitPA').value);
		let slitWidth = Number(E('targetSlitWidth').value);
		let length1 = Number(E('targetLength1').value);
		let length2 = Number(E('targetLength2').value);
		let tname = E("targetName").value;
		let targetRA = E("targetRA").value;
		let targetDEC = E("targetDEC").value;
		let targetMagn = E("targetMagn").value;
		let targetBand = E('targetBand').value;

		let values = {
			'idx': idx, 'raSexa': targetRA, 'decSexa': targetDEC, 'eqx': 2000,
			'mag': targetMagn, 'pBand': targetBand,
			'prior': prior, 'selected': selected, 'slitLPA': slitLPA, 'slitWidth': slitWidth,
			'len1': length1, 'len2': length2, 'targetName': tname
		};
		const data = {
			values: values,
		}
		ajaxPost('updateSelection', data, selectToggleCallback);
	};

	self.updateTarget = function (evt) {
		// Updates an existing or adds a new target.
		function updateTargetCallback(data) {
			self.reloadTargets(idx, data.info);
			self.canvasShow.selectedTargetIdx = i;
			self.canvasShow.reDrawTable();
			self.redraw();
		}
		// Sends new target info to server
		let idx = self.canvasShow.selectedTargetIdx;
		let prior = Number(E('targetPrior').value);
		let selected = Number(E('targetSelect').value);
		let slitLPA = Number(E('targetSlitPA').value);
		let slitWidth = Number(E('targetSlitWidth').value);
		let length1 = Number(E('targetLength1').value);
		let length2 = Number(E('targetLength2').value);
		let tname = E("targetName").value;
		let targetRA = E("targetRA").value;
		let targetDEC = E("targetDEC").value;
		let targetMagn = E("targetMagn").value;
		let targetBand = E('targetBand').value;

		let values = {
			'idx': idx, 'raSexa': targetRA, 'decSexa': targetDEC, 'eqx': 2000,
			'mag': targetMagn, 'pBand': targetBand,
			'prior': prior, 'selected': selected, 'slitLPA': slitLPA, 'slitWidth': slitWidth,
			'len1': length1, 'len2': length2, 'targetName': tname
		};
		const data = {
			'values': values
		}
		ajaxPost('updateTarget', data, updateTargetCallback);
	};

	self.deleteTarget = function (evt) {
		function deleteCallback(data) {
			self.reloadTargets(idx, data.info);
			self.canvasShow.selectedTargetIdx = i;
			self.canvasShow.reDrawTable();
			self.updateLoadedTargets(data);
		}

		let idx = self.canvasShow.selectedTargetIdx;
		if (idx < 0) return;
		let data = {
			'idx': Number(idx),
		};

		ajaxPost("deleteTarget", data, deleteCallback);
	};

	self.showDiv = function (divname, cont) {
		let elem = E(divname);

		elem.style.display = "block";
		elem.style.position = "absolute";
		elem.style.visibility = "visible";

		let button = "<br><input type='button' value='Close' id='closeBt'>";
		elem.innerHTML = cont + button;
		let w = document.body.clientWidth;
		let h = document.body.clientWidth;
		let w1 = elem.offsetWidth;
		let h1 = elem.offsetHeight;
		let x1 = document.body.scrollLeft + (w - w1) / 2;
		let y1 = document.body.scrollTop + (h - h1) / 2;
		elem.style.left = "500px";
		elem.style.top = "500px";

		let closeBt = E('closeBt');
		if (closeBt)
			closeBt.onclick = function (evt) { self.hideDiv(divname); };
	};

	self.hideDiv = function (divname) {
		let elem = E(divname);
		let s = elem.style;
		s.display = "none";
		s.visibility = "hidden";
	};

	self.saveMDF = function (evt) {
		async function mdf_callback(data) {
			self.canvasShow.slitsReady = 1;
			self.canvasShow.setTargets(data.targets);
			self.redraw();
			data = {
				mdFile: E('OutputFitsfd').value
			}
			const response = await fetch("saveMaskDesignFile", {
				method: "POST",
				body: JSON.stringify(data),
				headers: {
					'Content-type': 'application/json',
				}
			})
			if(response.status != 200) {
				alert(`Error saving file: ${await response.json()['msg']}`)
				return
			}
			const blob = await response.blob();
			let fname = data.params.OutputFits;
			let fstr = `Fits file<br><b>${fname}</b> successfully saved`;
			self.showDiv("savePopup", `${fstr}`);
			let el = document.createElement("a");
			el.setAttribute("download", [data.mdFile + '.tar.gz'])
			el.setAttribute("target", "_blank")
			let url = URL.createObjectURL(blob);
			el.href = url; // set the href attribute attribute
			el.click();
			el.remove()
		}

		self.recalculateMaskHelper(mdf_callback);
	};

	self.statusDiv = E('statusDiv');

	E('showHideParams').onclick = self.showHideParams;
	E('targetListFrame').onload = self.loadAll;
	E('loadTargets').onclick = self.sendTargets2Server
	E('resetDisplay').onclick = self.resetDisplay1;
	E('resetOffsets').onclick = self.resetOffsets1;
	E('minPriority').onchange = self.setMinPcode;
	E('maxPriority').onchange = self.setMinPcode;

	E('showAll').onchange = self.setMinPcode;
	E('showSelected').onchange = self.setMinPcode;
	E('showAlignBox').onchange = self.redraw;
	E('showGuideBox').onchange = self.redraw;
	E('showByPriority').onchange = self.redraw;

	E('setSlitsPA').onclick = self.setSlitsPA;
	E('setSlitsLength').onclick = self.setSlitsLength;
	E('setSlitsWidth').onclick = self.setSlitsWidth;
	E('updateParams').onclick = self.sendParamUpdate;

	E('recalculateMask').onclick = self.recalculateMask;
	E('generateSlits').onclick = self.generateSlits;
	E('clearSelection').onclick = self.clearSelection;
	E('resetSelection').onclick = self.resetSelection;

	E('updateTarget').onclick = self.updateTarget;
	E('deleteTarget').onclick = self.deleteTarget;
	E('selectToggle').onclick = self.selectToggle;
	E('saveMDF').onclick = self.saveMDF;

	hideDiv("savePopup");

	// init config params
	function init() {
		// init config params
		self.loadConfigParams();
	}
	init()
	return this;
}
