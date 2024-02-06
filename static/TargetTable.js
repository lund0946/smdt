function TargetTable(targets) {

	function E(n) {
		return document.getElementById(n);
	}

	var self = this;
	self.reDrawTargetTable = function () { };
	self.selectedIdx = -1;

	self.targets = targets;
	self.columns = [
		['#', 60, 'orgIndex', 0],
		['Name', 160, 'objectId', 0],
		['RA', 80, 'raSexa', 0],
		['DEC', 80, 'decSexa', 0],
		
		['Magn', 60, 'mag', 0],
		['Band', 50, 'pBand', 0],	
		['Prior', 60, 'pcode', 0],		
		['Sel', 35, 'selected', 0],
		['Slit PA', 60, 'slitLPA', 0],
		['Len1', 50, 'length1', 0],
		['Len2', 50, 'length2', 0],
		['SlitWidth', 60, 'slitWidth', 0],
		['In', 35, 'inMask', 0],
	].map(function (x) {
		return {label: x[0], width: x[1], key: x[2], dir: x[3]};
	});

	self.sortedIndices = new Array(self.targets.length);
	self.reverseIndices = new Array(self.targets.length);

	self.showTable = function () {
		// columns: name, width, up/down:-1,0,1

		let sum = 0;
		let bufHeader = [];
		let buf = []

		// Build the header row
		for (i in self.columns) {
			const col = self.columns[i]
			let arrow = '';
			if (col.dir > 0) arrow = ' &#9650; ';
			if (col.dir < 0) arrow = ' &#9660; ';
			bufHeader.push("<th width='" + col.width + "px' id='sortIdx" + i + "'>" + col.label + arrow + "</td>");
			sum += col.width;
		}
		self.tableWidth = sum;
		buf.push("<table id='targetTable'>");
		buf.push("<thead><tr>");
		buf.push(bufHeader.join(''));
		buf.push("</tr></thead>");
		buf.push("<tbody id='targetTableBody'>");


		for (let idx=0; idx < targets.length; ++idx) {
			// Table body content
			const sortedIdx = self.sortedIndices[idx];
			const tgt = targets[sortedIdx];
			let tId = "target" + sortedIdx;
			// 
			// Alternating color is done in CSS with tr:nth-child(even) and tr:nth-child(odd) 			
			//
			buf.push("<tr id='" + tId + "'>");
			const nums = ['mag', 'rlength1', 'rlength2', 'slitWidth']
			for (let kdx = 0 ; kdx < self.columns.length; ++kdx) {
				const col = self.columns[kdx];
				const val = nums.includes(tgt[col.key]) ? tgt[col.key].toFixed(2) : tgt[col.key];
				buf.push("<td width='" + col.width + "px'>" + val);
			}
			buf.push("</tr>");
		}
		buf.push("</tbody></table>");

		// Returns table as HTML string
		return buf.join("");
	};

	self.genSortFunction = function (idx) {
		// Returns the function with the sort index
		return function () {
			self.sortTable(idx);
		};
	};

	self.setSortClickCB = function (fn) {
		// Setup the callback of the header row.
		let i;
		for (i in self.columns) {
			E('sortIdx' + i).onclick = self.genSortFunction(i);
		}
		// fn is a callback function to allow the caller 
		// to send the content of the table to an element that is unknown to this class.
		self.reDrawTargetTable = fn;
	};

	self.setOnClickCB = function (fn) {
		// Setup the function to call when a row in the target table is clicked on.
		let i;
		for (i in self.targets.orgIndex) {
			E('target' + i).onclick = fn;
		}
	};

	self.scrollTo = function (idx) {
		// Smooth scroll to the desired idx/reversed-idx.
		// See CSS file.
		if (idx < 0) return;
		let tBody = E('targetTableBody');
		if (tBody && self.targets.orgIndex) {
			let nRows = self.targets.orgIndex.length;
			let pixelPerRow = tBody.scrollHeight / nRows;
			let visibleRows = tBody.clientHeight / pixelPerRow; // no margin, scrollbar
			let nIdx = self.reverseIndices[idx];
			let scrollY = nIdx * pixelPerRow;

			// Where are we now?
			let topRow = tBody.scrollTop / pixelPerRow;

			if (nIdx < visibleRows) {
				// In first page
				scrollY = 0;
			} else {
				nIdx -= 5;
				nIdx = Math.max(0, nIdx);
				scrollY = nIdx * pixelPerRow;
			}

			tBody.scrollTop = scrollY;
		}
	};

	self.highLight = function (idx) {
		if (idx < 0) return;
		let elem = E('target' + idx);
		if (elem) elem.className = 'hiRow';
	};

	self.markSelected = function (idx) {
		self.selectedIdx = idx;
		if (idx < 0) return;
		let elem = E('target' + idx);
		if (elem) elem.className = 'selectedRow';
	};

	self.markNormal = function (idx) {
		if (idx < 0) return;
		// Make sure target/elem exists.
		let elem = E('target' + idx);
		//if (elem) elem.className = idx % 2 == 0 ? 'evenRow' : 'oddRow';
		if (elem) elem.className = '';
	};

	self.sortTable = function (idx) {
		function sortUp(a, b) {
			let elem1 = dataCol[a];
			let elem2 = dataCol[b];
			if (elem1 < elem2) return -1;
			if (elem1 > elem2) return 1;
			return 0;
		}

		function sortDown(a, b) {
			let elem1 = dataCol[a];
			let elem2 = dataCol[b];
			if (elem1 < elem2) return 1;
			if (elem1 > elem2) return -1;
			return 0;
		}

		if (!self.targets) return;

		let info = self.columns[Math.max(idx, 0)];
		let dataCol = self.targets.map( (x) => x[info.key]);
		let indices = new Array(self.columns);
		let upDown = info.dir;

		// Remember original sort order
		for (let i = 0; i < self.targets.length; ++i) {
			indices[i] = i;
		}

		// Reset all sort flags
		for (let i = 0; i < self.columns.length; ++i) {
			self.columns[i].dir = 0;
		}

		// idx < 0 means original order, same as no sort
		if (idx >= 0) {
			// Check sort order up or down
			if (upDown >= 0) {
				indices.sort(sortUp);
				info.dir = -1;
			} else {
				indices.sort(sortDown);
				info.dir = 1;
			}
		}

		// Setup reversed index table.
		for (i = 0; i < indices.length; ++i) {
			self.reverseIndices[indices[i]] = i;
		}
		self.sortedIndices = indices;

		// Call the caller supplied function.
		self.reDrawTargetTable();
	};

	self.sortTable(0);

	return self;
}
