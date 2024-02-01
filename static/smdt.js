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
		for (let key of schema.required){
            sortedProps[key] = schema.properties[key]
		}
		for (let [key, props] of Object.entries(sortedProps)) {
			const type = props.type.includes('number') ? 'number': 'text';
			console.log('key', 'default', props.default, 'type', type)
			txt = `<tr><td> ${props.label} :<td><input ftype=${type} id="${key}fd" name="${key}" value="${props.default}"><td>${props.description}`;
			buf.push(txt);
		}
		buf.push('</table>');
		E('paramTableDiv').innerHTML = buf.join('');
	};

	self.loadConfigParams = function () {
		function callback(schema) {
			self.buildParamTable(schema);
		}
		ajaxCall('getSchema', {}, callback);
	};

	self.setStatus = function (msg) {
		self.statusDiv.innerHTML = msg;
	}


	self.generate_slitmask_callback = function (data) {
		self.canvasShow.slitsReady = false;
		if (!data) return;
		if (!data.targets) return;
		self.canvasShow.slitsReady = true;
		self.updateLoadedTargets(data);
		};

	self.sendTargets2Server = function () {
		// The browser loads the targets and sends them to the server.
		// The server responds with targetList.
		// Slitmask is then generated.

		const filename = E('targetList');
		if (!filename.value) {
			self.setStatus('Please select target list file to load');
			return;
		}

		const form2 = E('form2');
		const formData = new FormData(form2);
		const ajax = new AjaxClass()
		self.setStatus("Loading ...");
		ajax.postRequest('sendTargets2Server', formData, self.generate_slitmask_callback, 'mixed');
	};

	self.sendParamUpdate = function () {
		self.setStatus("Updating ...");
		const form2 = E('form2');
		self.setStatus("Loading ...");
		let formJson= {};
		Array.from(form2.elements).forEach((input) => {
			if (input.getAttribute('ftype')) {
				console.log('setting to number', input.name, Number(input.value))
				if (input.getAttribute('ftype') == 'number') {
					formJson[input.name] = Number(input.value);
				}
				else{
					formJson[input.name] = input.value.trim();
				}
			}
		  });
		  console.log('formJson', formJson)

		const param_update_callback = function(data) {
			if (!data.includes('OK')) {
				alert(data)
			}
		}

		const ajax = new AjaxClass()
		ajax.postRequest('updateParams4Server', formJson, param_update_callback, 'purejson');
	};

	self.loadBackgroundImage = function () {
		// This is the DSS image if requested
		// or a blank image, if no DSS.
		// The URL 'getDssImage' returns an image that is pushed to a <img>."
		//self.canvasShow.show('getDSSImage?r=' + Date.now(), 0);
		//self.canvasShow.redrawTxImage();
	};

	self.loadMaskLayout = function () {
		function callback(data) {
			self.canvasShow.setMaskLayout(data.mask, data.guiderFOV, data.badColumns);
			return;
		}

		ajaxCall("getMaskLayout", { 'instrument': 'deimos' }, callback);
	};
	// init config params
	self.loadConfigParams();

	self.updateLoadedTargets = function (data) {
		// Called when targets are loaded from server
		if (!data) return;

		self.targets = data.targets;
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
		cs.setTargets(self.targets);
		cs.setGaps(data.xgaps);

		cs.resetDisplay();
		cs.resetOffsets();
		self.redraw();
		self.canvasShow.selectTargetByIndex(self.canvasShow.selectedTargetIdx);
	};

	self.reloadTargets = function (newIdx) {
		function callback(data) {
			self.updateLoadedTargets(data);
			self.canvasShow.selectTargetByIndex(newIdx);
		}

		ajaxCall("getTargetsAndInfo", {}, callback);
	};


	self.loadAll = function () {
		self.loadBackgroundImage();
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
                let maskpa =  Number(E('MaskPAfd').value)
                self.canvasShow.setMaskPA(maskpa);
                let form2 = E('form2');
                form2.submit();
                self.canvasShow.setMaskPA(maskpa);
        };





	self.setMaskPA = function (evt) {
		let pa = Number(E('MaskPAfd').value);
		self.canvasShow.setMaskPA(pa);
	};

	self.setSlitsPA = function (evt) {
		let pa = Number(E('SlitPAfd').value);
		let tgs = self.canvasShow.targets;
		let ntgs = tgs.length1.length;
		let i;
		for (i = 0; i < ntgs; ++i) {
			if (tgs.pcode[i] <= 0) continue;
			tgs.slitLPA[i] = pa;
		}
		self.canvasShow.reDrawTable();
		self.redraw();

		let colName = 'slitLPA';
		let value = pa;
		let params = { 'colName': colName, 'value': value, 'avalue': value };
		ajaxPost('setColumnValue', params, function () { });
	};

	self.setSlitsLength = function (evt) {
		let asize = Number(E('AlignBoxSizefd').value);
		let ahalf = 0.5 * asize;
		let halfLen = 0.5 * Number(E('MinSlitLengthfd').value);
		let tgs = self.canvasShow.targets;
		let ntgs = tgs.length1.length;
		let i;
		for (i = 0; i < ntgs; ++i) {
			if (tgs.pcode[i] <= 0) {
				tgs.length1[i] = ahalf;
				tgs.length2[i] = ahalf;
			}
			else {
				tgs.length1[i] = halfLen;
				tgs.length2[i] = halfLen;
			}
		}
		self.canvasShow.reDrawTable();
		self.redraw();

		let colName = 'length1';
		let value = halfLen;
		let params = { 'colName': colName, 'value': value, 'avalue': ahalf };
		ajaxPost('setColumnValue', params, function () { });

		colName = 'length2';
		value = halfLen;
		params = { 'colName': colName, 'value': value, 'avalue': ahalf };
		ajaxPost('setColumnValue', params, function () { });
	};

	self.setSlitsWidth = function (evt) {
		let width = Number(E('SlitWidthfd').value);
		let tgs = self.canvasShow.targets;
		let ntgs = tgs.length1.length;
		let i;
		for (i = 0; i < ntgs; ++i) {
			if (tgs.pcode[i] <= 0) continue;
			tgs.slitWidth[i] = width;
		}
		self.canvasShow.reDrawTable();
		self.redraw();

		let colName = 'slitWidth';
		let value = width;
		let params = { 'colName': colName, 'value': value, 'avalue': value };
		ajaxPost('setColumnValue', params, function () { });
	};

	self.clearSelection = function (evt) {
		let tgs = self.canvasShow.targets;
		let ntgs = tgs.length1.length;
		let i;
		for (i = 0; i < ntgs; ++i) {
			if (tgs.pcode[i] <= 0) continue;
			tgs.selected[i] = 0;
		}
		self.canvasShow.reDrawTable();
		self.canvasShow.slitsReady = 0;
		self.redraw();

		let colName = 'selected';
		let params = { 'colName': colName, 'value': 0, 'avalue': 0 };
		ajaxPost('setColumnValue', params, function () { });
	};


        self.resetSelection = function (evt) {
                function callback() {
                        self.reloadTargets(0);
                }

                let params = {};

                ajaxCall("resetSelection", params, callback);
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

		let minSepAs = E('MinSlitSeparationfd').value;
		let minSlitLengthAs = E('MinSlitLengthfd').value;
		let boxSizeAs = E('AlignBoxSizefd').value;
		let extendSlits = E('extendSlits').checked ? 1 : 0;

		let params = {
			'currRaDeg': cs.currRaDeg, 'currDecDeg': cs.currDecDeg,
			'currAngleDeg': cs.positionAngle + cs.origPA,
			'minSepAs': minSepAs,
			'minSlitLengthAs': minSlitLengthAs,
			'boxSize': boxSizeAs,
			'extendSlits': extendSlits
		};
		let ajax = new AjaxClass();
		ajax.postRequest('recalculateMask', params, callback);
	};

	self.recalculateMask = function (evt) {
		function callback(data) {
			self.canvasShow.slitsReady = false;
			if (!data) return;
			if (!data.targets) return;

			self.canvasShow.slitsReady = false;
			self.updateLoadedTargets(data);
		}
		self.recalculateMaskHelper(callback);
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

                let minSepAs = E('MinSlitSeparationfd').value;
                let minSlitLengthAs = E('MinSlitLengthfd').value;
                let boxSizeAs = E('AlignBoxSizefd').value;
                let extendSlits = E('extendSlits').checked ? 1 : 0;

                let params = {
                        'currRaDeg': cs.currRaDeg, 'currDecDeg': cs.currDecDeg,
                        'currAngleDeg': cs.positionAngle + cs.origPA,
                        'minSepAs': minSepAs,
                        'minSlitLengthAs': minSlitLengthAs,
                        'boxSize': boxSizeAs,
                        'extendSlits': extendSlits
                };
                let ajax = new AjaxClass();
                ajax.postRequest('generateSlits', params, callback);
        };

        self.generateSlits = function (evt) {
		    self.setStatus("Loading ...");
			self.generateSlitsHelper(self.generate_slitmask_callback);
        };


        self.updateColumn = function (evt) {
                // Updates an existing target column with a set value.
                function callback(data) {
                        let i = idx;
                        if (data && data.length > 0)
                                i = data
                        self.reloadTargets(idx, i);
                        self.canvasShow.selectedTargetIdx = i;
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
                let ajax = new AjaxClass();
                ajax.postRequest('updateColumn', { 'values': JSON.stringify(params) }, callback);
        };


        self.selectToggle = function (evt) {
                // Updates an existing or adds a new target.
                function callback(data) {
                        let i = idx;
                        if (data && data.length > 0)
                                i = data
                        self.reloadTargets(idx, i);
                        self.updateLoadedTargets(data);
                        self.canvasShow.selectedTargetIdx = i;
                        self.canvasShow.reDrawTable();
                        self.redraw();

                }
                // Sends new target info to server
                let idx = self.canvasShow.selectedTargetIdx;
                let prior = Number(E('targetPrior').value);
                let sel = Number(E('targetSelect').value);
                let selected;
                if ( sel > 0) selected = 0;
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

                let params = {
                        'idx': idx, 'raSexa': targetRA, 'decSexa': targetDEC, 'eqx': 2000,
                        'mag': targetMagn, 'pBand': targetBand,
                        'prior': prior, 'selected': selected, 'slitLPA': slitLPA, 'slitWidth': slitWidth,
                        'len1': length1, 'len2': length2, 'targetName': tname
                };
                let ajax = new AjaxClass();
                ajax.postRequest('updateSelection', { 'values': JSON.stringify(params) }, callback);
        };

	self.updateTarget = function (evt) {
		// Updates an existing or adds a new target.
		function callback(data) {
			let i = idx;
			if (data && data.length > 0)
				i = data
			self.reloadTargets(idx, i);
                        self.updateLoadedTargets(data);
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

		let params = {
			'idx': idx, 'raSexa': targetRA, 'decSexa': targetDEC, 'eqx': 2000,
			'mag': targetMagn, 'pBand': targetBand,
			'prior': prior, 'selected': selected, 'slitLPA': slitLPA, 'slitWidth': slitWidth,
			'len1': length1, 'len2': length2, 'targetName': tname
		};
		let ajax = new AjaxClass();
		ajax.postRequest('updateTarget', { 'values': JSON.stringify(params) }, callback);
	};

	self.deleteTarget = function (evt) {
		function callback() {
			self.reloadTargets(idx, 0);
		}

		let idx = self.canvasShow.selectedTargetIdx;
		if (idx < 0) return;
		let params = { 'idx': idx };

		ajaxCall("deleteTarget", params, callback);
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
		function callbackSave(data) {
			let fname = data['fitsname'];
			let lname = data['listname']
			let path = data['path'];
			let errstr = data['errstr'];
			let fbackup = data['fbackup'];
			let lbackup = data['lbackup'];
                        errstr = "OK";
			if (errstr != "OK") {
				alert(`Failed to save mask design ${mdFile}`);
				return;
			}
			let fbstr = "";
			if (fbackup != null) {
				fbstr = `<br>Backup file:  <b>${fbackup}</b>`;
			}
			let lbstr = "";
			if (lbackup != null) {
				lbstr = `<br>Backup file: <b>${lbackup}</b>`;
			}
			let fstr = `Fits file<br><b>${fname}</b> successfully saved to <b>${path}</b> ${fbstr}`;
			let lstr = `Target list<br><b>${lname}</b> successfully saved to <b>${path}</b> ${lbstr}`;

			self.showDiv("savePopup", `${fstr}<br><br>${lstr}`);

		}

		function callback(data) {
			self.targets = data;
			//self.canvasShow.setShowPriorities(E('minPriority').value, E('maxPriority').value);
			self.canvasShow.slitsReady = 1;
			self.canvasShow.setTargets(data.targets);
			self.redraw();

			ajaxCall("saveMaskDesignFile", params, callbackSave);
		}

		let mdFile = E('OutputFitsfd').value;
		let params = { 'mdFile': mdFile };
		self.recalculateMaskHelper(callback);
	};

	function splitArgs() {
		var parts = window.location.search.replace('?', '').split("&");
		var out = Array();
		for (arg in parts) {
			var twoparts = parts[arg].split('=');
			out[twoparts[0]] = twoparts[1];
		}
		return out;
	} // splitArgs	

	self.checkQuit = function () {
		let args = splitArgs();
		if (!args["quit"]) return;

		ajaxCall("quit", {}, function () { });
		return "Quit";
	};

	window.onbeforeunload = self.checkQuit

	self.statusDiv = E('statusDiv');
	self.canvasShow = new CanvasShow('canvasDiv', 'zoomCanvasDiv');
	self.canvasShow.setShowPriorities(E('minPriority').value, E('maxPriority').value);
	self.loadMaskLayout();
	self.loadBackgroundImage();

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
	E('setMaskPA').onclick = self.setMaskPA;
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

	return this;
}
