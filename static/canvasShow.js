/**
 *
 * Displays an image, allowing pan, zoom, rotate, contrast/brightness change.
 *
 * This is derived from imgShow.js. 2018-03-30, skwok.
 *
 */

function TxMatrix() {
    var self = this;
    self.scaleFactor = 1;

    function norm(x) {
        while (x < 0) x += 360;
        while (x >= 360) x -= 360;
        return x;
    }

    function normRad(x) {
        while (x < 0) x += Math.PI * 2;
        while (x > Math.PI * 2) x -= Math.PI * 2;
        return x;
    }

    self.translate = function (tx, ty) {
        with (self) {
            mat[0][2] += tx;
            mat[1][2] += ty;
        }
    };

    self.rotate = function (angRad, xc, yc) {
        // Rotates incrementally
        with (self) {
            angRad = normRad(angRad);
            var sina = Math.sin(angRad);
            var cosa = Math.cos(angRad);
            var a = mat[0][0];
            var b = mat[0][1];
            var c = mat[1][0];
            var d = mat[1][1];

            var e = mat[0][2] - xc;
            var f = mat[1][2] - yc;

            mat[0][0] = a * cosa - b * sina;
            mat[0][1] = a * sina + b * cosa;

            // mat[1][0] = c * cosa - d * sina;
            // mat[1][1] = c * sina + d * cosa;
            mat[1][0] = -mat[0][1];
            mat[1][1] = mat[0][0];

            mat[0][2] = e * cosa - f * sina + xc;
            mat[1][2] = e * sina + f * cosa + yc;
            return;
        }
    };

    self.getScale = function () {
        with (self) {
            var ca2 = mat[0][0] * mat[1][1];
            var sa2 = mat[0][1] * mat[1][0];
            return Math.sqrt(Math.abs(ca2 - sa2));
        }
    };

    self.setRotAngle = function (angRad) {
        with (self) {
            var s = self.getScale();
            var sina = Math.sin(angRad);
            var cosa = Math.cos(angRad);
            mat[0][0] = mat[1][1] = s * cosa;
            mat[0][1] = s * sina;
            mat[1][0] = -s * sina;
        }
    };

    self.setRotAngleTrans = function (angRad, xc, yc) {
        with (self) {
            var sina = Math.sin(angRad);
            var cosa = Math.cos(angRad);

            mat[0][0] = mat[1][1] = cosa;
            mat[0][1] = sina;
            mat[1][0] = -sina;

            mat[0][2] = xc;
            mat[1][2] = yc;
        }
    };

    self.setTranslation = function (x, y) {
        with (self) {
            mat[0][2] = x;
            mat[1][2] = y;
        }
    };

    self.getRotAngle = function () {
        // Returns angle in radians
        with (self) {
            var ca = (mat[0][0] + mat[1][1]) / 2;
            var sa = (mat[0][1] - mat[1][0]) / 2;
            return Math.atan2(sa, ca);
        }
    };

    self.scale = function (s) {
        with (self) {
            mat[0][0] *= s;
            mat[0][1] *= s;
            mat[1][0] *= s;
            mat[1][1] *= s;
        }
    };

    self.scaleCenter = function (s, xc, yc) {
        // Scale such that the pixel in the center of the canvas stays there.
        with (self) {
            scale(s);
            mat[0][2] = mat[0][2] * s + xc * (1 - s);
            mat[1][2] = mat[1][2] * s + yc * (1 - s);
        }
    };

    // Returns arguments for Ctx.transform()
    // First 4 values represents 2x2 rotation/scale matrix
    // Last 2 values are translation.
    self.getTx = function (flipY) {
        with (self) {
            var r0 = mat[0];
            var r1 = mat[1];
            if (flipY) return [r0[0], r0[1], -r1[0], -r1[1], r0[2], r1[2]];
            else return [r0[0], r0[1], r1[0], r1[1], r0[2], r1[2]];
        }
    };

    self.reset = function (height) {
        self.mat = [
            [1, 0, 0],
            [0, 1, height],
            [0, 0, 1],
        ];
    };

    self.rotatePnt = function (x, y, flipY = 0) {
        var tx = self.getTx(flipY);
        var x1 = x * tx[0] + y * tx[1];
        var y1 = x * tx[2] + y * tx[3];

        return [x1, y1];
    };

    // World to screen coordinates
    self.w2s = function (x, y, flipY = 0) {
        var tx = self.getTx(flipY);
        var x1 = x * tx[0] - y * tx[1] + tx[4];
        var y1 = -x * tx[2] + y * tx[3] + tx[5];

        return [x1, y1];
    };

    // Screen to world coordinates
    self.s2w = function (x, y, flipY = 0) {
        // inverse transform
        var tx = self.getTx(flipY);
        var det = tx[0] * tx[3] - tx[1] * tx[2];
        var x1 = x - tx[4];
        var y1 = y - tx[5];
        var x2 = (x1 * tx[3] - y1 * tx[2]) / det;
        var y2 = (-x1 * tx[1] + y1 * tx[0]) / det;

        return [x2, y2];
    };

    self.toString = function () {
        var angDeg = (self.getRotAngle() / Math.PI) * 180.0;
        var tx = self.getTx(0);
        var out =
            "<table><tr>" +
            "<td>" +
            tx[0].toFixed(2) +
            "<td>" +
            tx[1].toFixed(2) +
            "<td>Angle:" +
            angDeg.toFixed(2) +
            "<tr>" +
            "<td>" +
            tx[2].toFixed(2) +
            "<td>" +
            tx[3].toFixed(2) +
            "<tr>" +
            "<td>" +
            tx[4].toFixed(2) +
            "<td>" +
            tx[5].toFixed(2) +
            "</table>";
        return out;
    };

    self.reset(0);
} // TxMatrix

function toggleSmoothing(ctx, onoff) {
    ctx.imageSmoothingEnabled = onoff;
    //ctx.mozImageSmoothingEnabled = onoff;
    //ctx.webkitImageSmoothingEnabled = onoff;
    //ctx.msImageSmoothingEnabled = onoff;
}

function Filter(ctx, width, height) {
    /*
     * Creates a temporary canvas element with given width and height. ctx
     * is the destination canvas context.
     */
    var self = this;
    self.scale = 1.4;

    self.offset = -42;
    self.outCtx = ctx;

    self.tmpCanvas = document.createElement("canvas");
    self.tmpCanvas.width = width;
    self.tmpCanvas.height = height;
    self.tmpCtx = self.tmpCanvas.getContext("2d");

    self.tmpCanvas2 = document.createElement("canvas");
    self.tmpCanvas2.width = width;
    self.tmpCanvas2.height = height;
    self.tmpCtx2 = self.tmpCanvas2.getContext("2d");

    toggleSmoothing(self.tmpCtx, false);
    toggleSmoothing(self.tmpCtx2, false);

    self.applyScaleOffset = function (data, scale, offset) {
        /*
         * This is for contrast and brightness control. Scales and offsets
         * the pixel values.
         */
        var len = data.length;
        var t = 0;
        var i = 0;

        while (i < len) {
            data[i] = data[i] * scale + offset;
            ++i;

            data[i] = data[i] * scale + offset;
            ++i;

            data[i] = data[i] * scale + offset;
            ++i;

            ++i; // skip alpha
        }
    };

    self.setParams = function (scale, offset) {
        /*
         * Sets the contrast (scale) and brightness (offset) parameters.
         */
        self.scale = scale;
        self.offset = offset;
    };

    // Split drawImage into two functions
    self.drawToOutputPart1 = function (img, offx, offy) {
        self.tmpCtx.drawImage(img, offx, offy);

        var imgData = self.tmpCtx.getImageData(0, 0, self.tmpCanvas.width, self.tmpCanvas.height);

        // Applies contrast
        self.applyScaleOffset(imgData.data, self.scale, self.offset);
        // Copies image to ctx2
        self.tmpCtx2.putImageData(imgData, 0, 0);
        // After this, new update should go to ctx2.
    };

    self.drawToOutputPart2 = function () {
        // When updates are completed, copy ctx2 to output
        var imgData = self.tmpCtx2.getImageData(0, 0, self.tmpCanvas.width, self.tmpCanvas.height);
        self.outCtx.putImageData(imgData, 0, 0);
    };
    return this;
} /* End of Filter */

// This is main function for the canvas show object.

function CanvasShow(containerName, zoomContainer) {
    var self = this;

    var AlignBox = -2;
    var GuideBox = -1;

    // For displaying mouse-over values and cuts
    // self.rawData = null;

    // Variables for mouse handling.
    self.anchorx = 0;
    self.anchory = 0;
    self.dragging = 0;

    self.mustFit = 1;

    self.centerRaDeg = 0; // original center RA deg
    self.centerDecDeg = 0; // original center DEC deg

    self.currRaDeg = 0;
    self.currDecDeg = 0;

    self.positionAngle = 0;
    self.origPA = 0;

    self.xAsPerPixel = 1;
    self.yAsPerPixel = 1;
    self.showMinPriority = -999;

    self.scale = 1;
    self.tMatrix = new TxMatrix(); // describes the view

    // Difference btw targetMatrix and origSkyMatrix 
    // is that origSkyMatrix is rotated by origPA relative to targetMatrix
    self.targetMatrix = new TxMatrix(); // describes the sky
    self.origSkyMatrix = new TxMatrix(); // describes the orignal sky PA


    self.maskOffsetX = 0;
    self.maskOffsetY = 270;
    self.slitColor = "#FF0000";
    self.maskColor = "#8888FF";
    self.guiderFOVColor = "#FFFF88";
    self.badColumnsColor = "#FFaaaa";

    self.slitsReady = false;

    // for selecting targets
    self.findIt = 0;
    self.searchX = 0;
    self.searchY = 0;
    self.thold = 0;
    self.selectedTargetIdx = -1;

    self.centerMarker = [
        // Center of mask
        [-11.85, 0.0, 0],
        [11.85, 0.0, 3],
        [0.0, -11.85, 0],
        [0.0, 11.85, 3],

        // Optical axis        
        [-11.85, 270.0, 0],
        [11.85, 270.0, 3],
        [0.0, 270 - 11.85, 0],
        [0.0, 270 + 11.85, 3],
    ];

    self.maskLayout = [];

    self.contElem = E(containerName);
    self.zoomElem = E(zoomContainer);

    self.mouseAction = "panSky";
    self.showInfo = function () { };
    // End variables

    function E(n) {
        return document.getElementById(n);
    }

    function abs(x) {
        if (x < 0) return -x;
        return x;
    }

    function showMsg(dname, msg) {
        E(dname).innerHTML = msg;
    }

    function limit(x, lo, hi) {
        if (x < lo) return lo;
        if (x > hi) return hi;
        return x;
    }

    function toSexa(inDeg) {
        var val = inDeg;
        var sign = " ";
        if (val < 0) {
            sign = "-";
            val = -val;
        }
        var dd = Math.floor(val);
        val = (val - dd) * 60;
        var mm = Math.floor(val);
        var ss = (val - mm) * 60;
        if (dd < 10) dd = "0" + dd;
        if (mm < 10) mm = "0" + mm;
        var cc = ":";
        var ss100 = Math.round(ss * 100);
        ss = ss100 / 100;
        if (ss100 < 1000) cc = ":0";
        return sign + dd + ":" + mm + cc + ss.toFixed(2);
    }

    function toBoolean(s) {
        // String to boolean
        s = s.toUpperCase();
        return s == "YES" || s == "1" || s == "TRUE" || s == "ON";
    }

    function norm360(x) {
        while (x > 360) x -= 360;
        while (x < 0) x += 360;
        return x;
    }

    function norm180(x) {
        if (x > 180) return x - 360;
        if (x < -180) return x + 360;
        return x;
    }

    function degrees(rad) {
        return norm180((rad * 180.0) / Math.PI);
    }

    function radians(deg) {
        return (deg * Math.PI) / 180.0;
    }

    function rotate(angRad, x, y) {
        var sa = Math.sin(angRad);
        var ca = Math.cos(angRad);
        return rotateSaCa(sa, ca, x, y);
    }

    function rotateSaCa(sa, ca, x, y) {
        var x1 = x * ca - y * sa;
        var y1 = x * sa + y * ca;
        return [x1, y1];
    }

    self.onloadImage = function () {
        if (self.mustFit) {
            // self.fitMask();
            self.resetDisplay();
            self.resetOffsets();
            self.mustFit = 0;
        }
        self.redrawTxImage();
    };

    self.initialize = function () {
        /*
         * Creates a canvas and puts it in the container. Sets default size to
         * 400x400 if not defined. Instantiates a filter object to process the
         * image.
         */
        var cv = document.createElement("canvas");
        if (cv.getContext) {
            var cont = self.contElem;
            self._Canvas = cv;
            cv.tabIndex = 99999;
            cont.tabIndex = 99999;
            var w = Math.max(1000, cont.clientWidth);
            cv.width = w;
            cv.height = Math.max(500, w / 3);
            if (cv.width == 0 || cv.height == 0) {
                cv.width = cv.height = 400;
            }
            cont.replaceChild(cv, cont.childNodes[0]);
            self.ctx = cv.getContext("2d");
            self.ctx.scale(1, 1);
            toggleSmoothing(self.ctx, false);
            self.destCtx = self.ctx;
            self.filter = new Filter(self.ctx, cv.width, cv.height);
            self._Ctx = self.filter.tmpCtx;
            // Creates a hidden image element to store the source image.
            self.bgImg = new Image();
            self.bgImg.onload = self.onloadImage;
            self.findMaskMinMax();
        } else {
            alert("Your browser does not support canvas\nPlease use another browser.");
        }
    };

    self.findMaskMinMax = function () {
        var layout = self.maskLayout;
        var i;
        var minx, miny, maxx, maxy;
        minx = miny = 999999;
        maxx = maxy = -999999;

        for (i in layout) {
            var row = layout[i];
            var x = row[0];
            var y = row[1];
            minx = Math.min(minx, x);
            miny = Math.min(miny, y);
            maxx = Math.max(maxx, x);
            maxy = Math.max(maxy, y);
        }
        self.maskMinMax = [minx, miny, maxx, maxy];
    };

    self.initialize();

    self.fitMask = function (atx, aty) {
        // Fit display centered at world coord atx,aty
        var mmm = self.maskMinMax;
        var xrange = mmm[2] - mmm[0];
        var yrange = mmm[3] - mmm[1];

        var cv = self._Canvas;
        var sw = cv.width / xrange;
        var sh = cv.height / yrange;
        var scale = Math.min(sw, sh) * 0.9;

        var x = cv.width / 2;
        var y = cv.height / 2;

        self.tMatrix.reset(0);
        self.tMatrix.setRotAngle(0);
        self.tMatrix.scale(scale);
        var sxy = self.tMatrix.w2s(atx, aty);
        self.tMatrix.translate(x + sxy[0], y + sxy[1]);
    };

    self.showPositionInfo = function () {
        // Updates the current PA, center RA/DEC
        // and shows them in the parameter form.

        var tmatAngleRad = self.tMatrix.getRotAngle();

        var sxy = self.origSkyMatrix.s2w(self.maskOffsetX, self.maskOffsetY, 0);

        self.currDecDeg = self.centerDecDeg + (sxy[0] + self.maskOffsetX) / 3600;

        var cosDec = Math.cos(radians(self.currDecDeg));
        cosDec = Math.max(cosDec, 1e-4);

        self.currRaDeg = self.centerRaDeg + (self.maskOffsetY - sxy[1]) / 3600 / cosDec;

        var raSexa = toSexa(self.currRaDeg / 15);
        var decSexa = toSexa(self.currDecDeg);
        var paDeg = self.positionAngle + self.origPA;

        if (E("InputRAfd")) {
            E("InputRAfd").value = raSexa;
            E("InputDECfd").value = decSexa;
            E("MaskPAfd").value = paDeg.toFixed(3);

            showMsg(
                "centerDiv",
                " RA= <b>" + raSexa + "</b> hrs; DEC= <b>" + decSexa + "</b> deg; Pos Ang= <b>" + paDeg.toFixed(2) + "</b> deg "
            );
        }
    };


    self.calcPAng = function () {
        var dec = radians(self.currDecDeg);
        var ha = radians(Number(E("HourAnglefd").value) * -15.);
        var phi = radians(19.8);
        const cp = Math.cos(phi);
        const sqsz = cp * Math.sin(ha);
        const cqsz = Math.sin(phi) * Math.cos(dec) - cp * Math.sin(dec) * Math.cos(ha);

        if (sqsz === 0 && cqsz === 0) {
            cqsz = 1;
        }

        const pa = radians(degrees(Math.atan2(sqsz, cqsz)) - 90);
        return pa;
    };


    self.drawCompass = function (ctx) {
        var color = "#ffff00";
        var pangColor = "#ff0000";
        var rotAngleDeg = self.compassNorthDeg; // calculated in calcualteAngles()

        var aRad = radians(rotAngleDeg);
        var ca = Math.cos(aRad);
        var sa = Math.sin(aRad);

        var x0 = 70;
        var y0 = 70;
        var len = 50;

        var north = rotateSaCa(sa, ca, 0, -len);
        var northText = rotateSaCa(sa, ca, 0, -len - 10);
        var east = rotateSaCa(sa, ca, -len, 0);
        var eastText = rotateSaCa(sa, ca, -len - 10, 0);

        var pangRad = self.calcPAng();
        var capa = Math.cos(pangRad);
        var sapa = Math.sin(pangRad);
        var pang = rotateSaCa(sapa, capa, 0, -len);
        var pangText = rotateSaCa(sapa, capa, 0, -len - 10);

        with (ctx) {
            //setTransform(1, 0, 0, 1, 0, 0);
            strokeStyle = pangColor;
            lineWidth = 1;

            //beginPath();
            drawArrow(ctx, x0, y0, x0 + pang[0], y0 + pang[1], 8);
            //stroke();
            strokeText("Par Ang", x0 + pangText[0], y0 + pangText[1]);
        }

        with (ctx) {
            //setTransform(1, 0, 0, 1, 0, 0);
            strokeStyle = color;
            lineWidth = 1;

            //beginPath();
            drawArrow(ctx, x0, y0, x0 + north[0], y0 + north[1], 8);
            drawArrow(ctx, x0, y0, x0 + east[0], y0 + east[1], 8);

            //stroke();

            strokeText("N", x0 + northText[0], y0 + northText[1]);
            strokeText("E", x0 + eastText[0], y0 + eastText[1]);
        }
    };

    self.calculateAngles = function () {
        // positionAngle is telescope PA
        // view angle in screen coordinates
        let tmAngle = self.tMatrix.getRotAngle();
        let tmDeg = degrees(tmAngle)

        self.positionAngle = degrees(self.targetMatrix.getRotAngle());

        let skyPA = self.positionAngle + self.origPA;
        // compass North in screen angle
        self.compassNorthDeg = tmDeg + 90 + skyPA;

        // slit angle in screen angle
        self.slitBaseAngleDeg = self.compassNorthDeg;
        //self.slitBaseAngleDeg = tmDeg;

        self.slitRel2Mask = 0; //radians(skyPA);

        // mask angle in screen angle
        self.maskBaseAngleRad = tmAngle;
    };

    self.reallyDrawTxImage = function () {
        // Applies transform and redraws image.
        var cv = self._Canvas;
        var tx = self.tMatrix;
        var tp = tx.getTx(self.flipY);
        var scaleF = tx.getScale();

        var iwidth = self.bgImg.width / 2;
        var iheight = self.bgImg.height / 2;

        self.calculateAngles();

        with (self._Ctx) {
            setTransform(1, 0, 0, 1, 0, 0);
            clearRect(0, 0, cv.width, cv.height);
            transform(tp[0], tp[1], tp[2], tp[3], tp[4], tp[5]);
        }

        // Draws the background images, applies contrast and copies result to
        // tmpCtx2

        self.filter.drawToOutputPart1(self.bgImg, -iwidth, -iheight);

        // Draw this after drawing the DSS/background image
        // because contrast filter is applied to the DSS/background image.
        var ctx2 = self.filter.tmpCtx2;
        with (ctx2) {
            setTransform(1, 0, 0, 1, 0, 0);
            self.drawGuiderFOV(ctx2, self.guiderFOV);
            self.drawBadColumns(ctx2, self.badColumns);
            var rotatedMask = self.drawMask(ctx2, self.maskLayout);

            var checker = new InOutChecker(rotatedMask);
            self.drawTargets(ctx2, checker);
            self.drawCompass(ctx2);
        }
        // Copies result to destCtx
        self.filter.drawToOutputPart2();

        self.showPositionInfo();
    };

    self.redrawTxImage = function () {
        window.requestAnimationFrame(self.reallyDrawTxImage);
    };

    self.drawGaps = function (ctx, gaps, y0, color, lw) {
        let tmax = self.tMatrix;
        let minSlitLen = Number(E("MinSlitLengthfd").value);

        let x0 = 0,
            x1 = 0;
        let len = gaps.length;
        let i;
        let yOff = 0;
        let y1 = y0;

        minSlitLen = Math.max(4, minSlitLen);
        with (ctx) {
            strokeStyle = color;

            lineWidth = lw;
            beginPath();

            for (i = 0; i < len; ++i) {
                let gap = gaps[i];
                //if (gap[1] - gap[0] < minSlitLen) continue;
                y1 = y0 + (i % 2) * 10;
                let sxy0 = tmax.w2s(gap[0], y1);
                let sxy1 = tmax.w2s(gap[1], y1);
                moveTo(sxy0[0], sxy1[1]);
                lineTo(sxy1[0], sxy1[1]);
                lineTo(sxy1[0], sxy1[1] + 10);
            }
            stroke();
        }
    };

    //
    // Draws targets according to options
    //
    self.drawTargets = function (ctx, checker) {
        // This function is called once per target.
        // It adds the target to the given list.

        function checkClick(idx, x, y) {
            if (self.findIt) {
                // Check if target is near to where the mouse was clicked.
                var dx = Math.abs(self.searchX - x);
                var dy = Math.abs(self.searchY - y);
                if (dx < self.thold && dy < self.thold) {
                    // If close enough, then if this target is the closest one.
                    var dist = Math.hypot(dx, dy);
                    if (dist < minDist) {
                        minDist = dist;
                        self.minDist = dist;
                        self.selectedTargetIdx = idx;
                    }
                }
            }
        }

        function classify() {
            // Depending on if target is inside/outside, or selected, push it to
            // a different list to be displayed later.
            for (i = 0; i < len; ++i) {
                var xy = self.targetMatrix.w2s(xpos[i], ypos[i]);
                var x = xy[0];
                var y = xy[1];
                var sxy = tmax.w2s(x, y);
                var sx = sxy[0];
                var sy = sxy[1];

                var pri = pcode[i];
                var inMask = checker.checkPoint(sx, sy);

                xOut.push(sx);
                yOut.push(sy);

                checkClick(i, x, y);

                if (pri == GuideBox) {
                    if (inMask) guideBoxInIdx.push(i);
                    else guideBoxOutIdx.push(i);
                    continue;
                }

                if (pri == AlignBox) {
                    if (inMask) alignBoxInIdx.push(i);
                    else alignBoxOutIdx.push(i);
                    continue;
                }

                if (showSelected || (showMinPriority <= pri && pri <= showMaxPriority)) {
                    if (inMask) {
                        showInIdx.push(i);
                    } else showOutIdx.push(i);

                    if (selected[i]) {
                        if (inMask) {
                            selectedInIdx.push(i);
                        } else selectedOutIdx.push(i);
                    }
                }
            }
        }

        function drawGuideBox(idx) {
            var x = xOut[idx];
            var y = yOut[idx];

            var l1 = length1s[idx] * arc2Pixel;
            var l2 = length2s[idx] * arc2Pixel;
            drawRect(ctx, x - l1, y - l1, x + l2, y + l2);
        }

        function drawAlignBox(idx) {
            // alignemtn box
            var x = xOut[idx];
            var y = yOut[idx];

            var l1 = length1s[idx] * arc2Pixel;
            var l2 = length2s[idx] * arc2Pixel;
            drawRect(ctx, x - l1, y - l1, x + l2, y + l2);
        }

        function drawTarget(idx) {
            var x = xOut[idx];
            var y = yOut[idx];
            var bSize = targetSizeScale * 2; // magn[idx];
            bSize = limit(bSize, 3, 20);
            drawCircle(ctx, x, y, bSize);
        }

        function drawSelTarget(idx) {
            var x = xOut[idx];
            var y = yOut[idx];
            var bSize = targetSizeScale * 2; // magn[idx];
            bSize = limit(bSize, 3, 20);
            drawPlusBig(ctx, x, y, bSize, bSize);
        }

        function drawClickedOn(idx) {
            var x = xOut[idx];
            var y = yOut[idx];
            var bSize = targetSizeScale * 2; // magn[idx];
            bSize = limit(bSize, 3, 20);
            drawCrossBig(ctx, x, y, bSize, bSize);
        }

        function drawSlit(idx) {
            /*-
             * Position of the star is at x/y, already transformed to screen coordinates
             * Lengths to left and right are l1/l2, in screen coordinates
             * Slit width adjusted by scale.			 *
             */

            let x = xOut[idx];
            let y = yOut[idx];
            let scale = tmScale / self.xAsPerPixel;
            let l1 = length1s[idx] * scale;
            let l2 = length2s[idx] * scale;

            let slitWidth = slitWidths[idx];
            let halfWidth = slitWidth * scale * 0.5;

            // The slit angle is relative to screen
            let slitAngle = radians(Number(slitPAs[idx]));
            let slitAngleOnScreen = 1 * radians(self.slitBaseAngleDeg) + slitAngle;


            let xgeom = -Math.cos(slitAngleOnScreen);
            let ygeom = Math.sin(slitAngleOnScreen);

            if (projSlitLen) {

                xgeom = xgeom / Math.abs(Math.cos(slitAngleOnScreen))
                ygeom = ygeom / Math.abs(Math.cos(slitAngleOnScreen))
            }

            if (xgeom > 0) {
                x11 = x - l1 * xgeom;
                y11 = y - l1 * ygeom;
                x12 = x + l2 * xgeom;
                y12 = y + l2 * ygeom;

            }
            else {
                x11 = x + l2 * xgeom;
                y11 = y + l2 * ygeom;
                x12 = x - l1 * xgeom;
                y12 = y - l1 * ygeom;
            }



            let xy1 = self.targetMatrix.w2s(slitX1[idx], slitY1[idx]);
            let x1 = xy1[0];
            let y1 = xy1[1];
            let sxy1 = tmax.w2s(x1, y1);
            let sx1 = sxy1[0];
            let sy1 = sxy1[1];

            let xy2 = self.targetMatrix.w2s(slitX2[idx], slitY2[idx]);
            let x2 = xy2[0];
            let y2 = xy2[1];
            let sxy2 = tmax.w2s(x2, y2);
            let sx2 = sxy2[0];
            let sy2 = sxy2[1];

            let xy3 = self.targetMatrix.w2s(slitX3[idx], slitY3[idx]);
            let x3 = xy3[0];
            let y3 = xy3[1];
            let sxy3 = tmax.w2s(x3, y3);
            let sx3 = sxy3[0];
            let sy3 = sxy3[1];

            let xy4 = self.targetMatrix.w2s(slitX4[idx], slitY4[idx]);
            let x4 = xy4[0];
            let y4 = xy4[1];
            let sxy4 = tmax.w2s(x4, y4);
            let sx4 = sxy4[0];
            let sy4 = sxy4[1];


            drawQuadrilateral(ctx,
                sx1, sy1, sx2, sy2,
                sx3, sy3, sx4, sy4);

            drawPlus(ctx, x, y, 2 * halfWidth, 2 * halfWidth);
        }

        function drawListIdx(tlist, color, fnc) {
            var idx;
            ctx.strokeStyle = color;
            ctx.beginPath();
            for (idx in tlist) {
                fnc(tlist[idx]);
            }
            ctx.stroke();
        }

        var targets = self.targets;
        if (!targets) return;


        // Write lists from targets dynamically
        var tmax = self.tMatrix;
        const mylists = {
            'xpos': 'xarcs', 'ypos': 'yarcs',
            'slitX1': 'arcslitX1', 'slitX2': 'arcslitX2', 'slitX3': 'arcslitX3', 'slitX4': 'arcslitX4',
            'slitY1': 'arcslitY1', 'slitY2': 'arcslitY2', 'slitY3': 'arcslitY3', 'slitY4': 'arcslitY4',
            'slitPAs': 'slitLPA', 'slitWidths': 'slitWidth',
            'length1s': 'rlength1', 'length2s': 'rlength2',
            'selected': 'selected', 'pcode': 'pcode', 'magn': 'mag'
        }
        var myVars = {}
        Object.keys(mylists).forEach((key) => { myVars[key] = [] })

        for (let tgt of targets) {
            for (let [key, tkey] of Object.entries(mylists)) {
                myVars[key].push(tgt[tkey])
            }
        }

        for (let [key, value] of Object.entries(myVars)) {
            const string = key + ' = ' + JSON.stringify(value)
            eval(string)
        }
        var len = targets.length;

        var selectedInIdx = [];
        var selectedOutIdx = [];
        var showInIdx = [];
        var showOutIdx = [];
        var alignBoxInIdx = [];
        var alignBoxOutIdx = [];
        var guideBoxInIdx = [];
        var guideBoxOutIdx = [];
        var xOut = [];
        var yOut = [];

        var i;

        var tmScale = tmax.getScale();
        var targetSizeScale = tmScale;

        var arc2Pixel = tmScale / self.xAsPerPixel;
        var minDist = 1e10;

        var projSlitLen = toBoolean(E("ProjSlitLengthfd").value);

        var showAll = E("showAll").checked;
        var showAlignBox = E("showAlignBox").checked;
        var showGuideBox = E("showGuideBox").checked;
        var showSelected = E("showSelected").checked;
        var showByPriority = E("showByPriority").checked;
        var showMinPriority = Number(E("minPriority").value);
        var showMaxPriority = Number(E("maxPriority").value);

        if (showAll) {
            showByPriority = true;
            showMinPriority = 0;
            showMaxPriority = 99999;
        }

        ctx.lineWidth = 1;
        ctx.lineCap = "square";

        classify();

        if (showAlignBox) {
            drawListIdx(alignBoxInIdx, "#99ff99", drawAlignBox);
            drawListIdx(alignBoxOutIdx, "#ff0000", drawAlignBox);
        }

        if (showGuideBox) {
            drawListIdx(guideBoxInIdx, "#ffff99", drawGuideBox);
            drawListIdx(guideBoxOutIdx, "#ff0000", drawGuideBox);
        }

        if (showByPriority) {
            drawListIdx(showInIdx, "#99ff99", drawTarget);
            drawListIdx(showOutIdx, "#ff0000", drawTarget);
        } else {
            drawListIdx(selectedInIdx, "#99ff99", drawTarget);
            drawListIdx(selectedOutIdx, "#ff0000", drawTarget);
        }

        if (self.slitsReady) {
            drawListIdx(selectedInIdx, "#99ff99", drawSlit);
            // for debugging only
            //self.drawGaps(ctx, self.xgaps, 350, "#dddd44", 1);
        } else {
            drawListIdx(selectedInIdx, "#99ff99", drawSelTarget);
            drawListIdx(selectedOutIdx, "#ff0000", drawSelTarget);
        }

        if (self.selectedTargetIdx >= 0) {
            drawListIdx([self.selectedTargetIdx], "#ffffff", drawClickedOn);
        }
    };

    self.clearTargetSelection = function () {
        self.targetTable.markNormal(self.targetTable.selectedIdx);
    };

    self.selectTargetByIndex = function (newIdx) {
        let targets = self.targets;
        let nTargets = targets ? targets.length : 0;
        newIdx = Math.min(newIdx, nTargets - 1);

        self.clearTargetSelection();

        if (newIdx >= 0) {
            self.showTargetForm(newIdx);
            self.targetTable.scrollTo(newIdx);
            self.targetTable.markSelected(newIdx);
            self.selectedTargetIdx = newIdx;
        }
    };

    self.selectTarget = function (mx, my) {
        // Selecte target with mouse
        var tmat = self.tMatrix;
        var scale = tmat.getScale();
        var xy = tmat.s2w(mx, my, 0);

        self.searchX = xy[0];
        self.searchY = xy[1];
        self.thold = Math.min(7 / scale, 7);

        var sIdx = self.selectedTargetIdx;
        self.clearTargetSelection();
        self.findIt = 1;
        self.reallyDrawTxImage();
        self.findIt = 0;
        if (self.selectedTargetIdx < 0) {
            self.selectedTargetIdx = sIdx;
        }
        self.selectTargetByIndex(self.selectedTargetIdx);
    };

    self.showTargetForm = function (idx) {
        var targetTable = self.targetTable;
        var targetIdx = idx;
        var targets = targetTable.targets;

        E("targetName").value = targets[targetIdx].objectId;
        E("targetRA").value = targets[targetIdx].raSexa;
        E("targetDEC").value = targets[targetIdx].decSexa;

        E("targetPrior").value = targets[targetIdx].pcode;
        E("targetSelect").value = targets[targetIdx].selected;
        E("targetSlitPA").value = targets[targetIdx].slitLPA;
        E("targetSlitWidth").value = targets[targetIdx].slitWidth;
        E("targetLength1").value = targets[targetIdx].length1.toFixed(2);
        E("targetLength2").value = targets[targetIdx].length2.toFixed(2);
        E("targetMagn").value = targets[targetIdx].mag;
        E("targetBand").value = targets[targetIdx].pBand;
    };

    self.updateTarget = function (idx) {
        // Updates target in targets
        if (idx < 0) return;

        targets[idx].pcode = Number(E("targetPrior").value);
        targets[idx].selected = Number(E("targetSelect").value);
        targets[idx].slitLPA = Number(E("targetSlitPA").value);
        targets[idx].slitWidth = Number(E("targetSlitWidth").value);
        targets[idx].length1 = Number(E("targetLength1").value);
        targets[idx].length2 = Number(E("targetLength2").value);

        self.reDrawTable();
        self.targetTable.scrollTo(idx);
        self.targetTable.highLight(idx);
        self.reallyDrawTxImage();
    };


    self.addAlign = function () {
        function callback(data) {
            data.targets && localStorage.setItem('targets', JSON.stringify(data.targets));
            data.params && localStorage.setItem('params', JSON.stringify(data.params));
            self.SlitmaskDesignTool.reloadTargets(idx);
            self.selectedTargetIdx = idx;
            self.reDrawTable();
            self.SlitmaskDesignTool.redraw();
            self.targetTable.scrollTo(idx);
            self.targetTable.highLight(idx);
            self.reallyDrawTxImage();
        }
        // Updates an existing or adds a new target.
        // Sends new target info to server
        let idx = self.selectedTargetIdx;
        let prior = Number(-2);
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
            'targets': JSON.parse(localStorage.getItem('targets')),
            'params': JSON.parse(localStorage.getItem('params')),
            'values': values
        }
        ajaxPost('updateTarget', data, callback);
    };

    self.selTarget = function () {
        function callback(data) {
            data.targets && localStorage.setItem('targets', JSON.stringify(data.targets));
            data.params && localStorage.setItem('params', JSON.stringify(data.params));
            self.smdt.reloadTargets(idx);
            self.selectedTargetIdx = idx;
            self.reDrawTable();
            self.SlitmaskDesignTool.redraw();
            self.targetTable.scrollTo(idx);
            self.targetTable.highLight(idx);
            self.reallyDrawTxImage();

        }
        // Updates an existing or adds a new target.
        // Sends new target info to server
        let idx = self.selectedTargetIdx;
        let prior = Number(E('targetPrior').value);
        let selected = Number(1);
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
            'targets': JSON.parse(localStorage.getItem('targets')),
            'params': JSON.parse(localStorage.getItem('params')),
            'values': values
        }
        ajaxPost('updateTarget', data, callback);
    };

    self.deselTarget = function () {
        function callback(data) {
            data.targets && localStorage.setItem('targets', JSON.stringify(data.targets));
            data.params && localStorage.setItem('params', JSON.stringify(data.params));
            self.SlitmaskDesignTool.reloadTargets(idx);
            self.selectedTargetIdx = idx;
            self.reDrawTable();
            self.SlitmaskDesignTool.redraw();
            self.targetTable.scrollTo(idx);
            self.targetTable.highLight(idx);
            self.reallyDrawTxImage();
        }
        // Updates an existing or adds a new target.
        // Sends new target info to server
        let idx = self.selectedTargetIdx;
        let prior = Number(E('targetPrior').value);
        let selected = Number(0);
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
            'targets': JSON.parse(localStorage.getItem('targets')),
            'params': JSON.parse(localStorage.getItem('params')),
            'values': values
        }
        ajaxPost('updateTarget', data, callback);
    };


    self.clickedRow = function (evt) {
        // Called when clicked on a row in the target table
        console.log('clicked row!')
        var tId = this.id;
        var idx = Number(tId.replace("target", ""));

        self.selectedTargetIdx = idx;
        self.selectTargetByIndex(self.selectedTargetIdx);
        self.redrawTxImage();
    };

    self.rotateMaskLayout = function (mask) {
        // Rotates mask layout for drawing.
        // Applies rotation directly to the vertices of the mask.
        // Returns the rotated coordinates of the mask for drawing.
        var sx = 1.0 / self.xAsPerPixel;
        var sy = 1.0 / self.yAsPerPixel;
        var rotX = self.maskOffsetX;
        var rotY = self.maskOffsetY;
        var tmax = self.tMatrix;
        var i;

        var out = Array();
        for (i in mask) {
            var row = mask[i];

            var sxy = tmax.w2s(row[0], row[1]);
            var x0 = sxy[0];
            var y0 = sxy[1];
            out.push([x0, y0, row[2]]);
        }
        return out;
    };

    self.drawGuiderFOV = function (ctx, guiderFOV) {
        if (!E("showGuiderFOV").checked) return;
        var layout = self.rotateMaskLayout(guiderFOV);
        drawPolylines(ctx, layout, self.guiderFOVColor, 1);
    };

    self.drawBadColumns = function (ctx, badColumns) {
        if (!E("showBadColumns").checked) return;
        var layout = self.rotateMaskLayout(badColumns);
        drawPolylines(ctx, layout, self.BadColumnsColor, 1);
    };

    self.drawMask = function (ctx, mask) {
        var layout = mask.concat(self.centerMarker);
        var layout1 = self.rotateMaskLayout(layout);
        drawPolylines(ctx, layout1, self.maskColor, 1);
        return layout1;
    };

    // Gets absolute position x/y in pixel coordinates of an element.
    // Returns array [x, y]
    function getAbsPosition(elem) {
        var prent = elem.offsetParent;
        var absLeft = elem.offsetLeft;
        var absTop = elem.offsetTop;
        while (prent) {
            absLeft += prent.offsetLeft;
            absTop += prent.offsetTop;
            prent = prent.offsetParent;
        }
        return {
            x: absLeft,
            y: absTop,
        };
    }

    self.mouseUp = function (evt) {
        evt = evt || window.event;
        evt.stopPropagation();
        evt.preventDefault();
        var mx = evt.pageX;
        var my = evt.pageY;
        var dx = mx - self.anchorx;
        var dy = my - self.anchory;
        self.dragging = 0;
        if (E("enableSelection").checked && abs(dx) < 2 && abs(dy) < 2) {
            var ePos = getAbsPosition(self.contElem);
            self.selectTarget(mx - ePos.x, my - ePos.y);
        }
        self.redrawTxImage();
        return false;
    };

    self.mouseDown = function (evt) {
        evt = evt || window.event;
        evt.stopPropagation();
        evt.preventDefault();
        self.contElem.focus();
        self.lastmx = self.anchorx = evt.pageX;
        self.lastmy = self.anchory = evt.pageY;
        self.dragging = 1;
        var cv = self._Canvas;
        var ePos = getAbsPosition(self.contElem);
        var xc = cv.width / 2 + ePos.x;
        var yc = cv.height / 2 + ePos.y;
        self.baseAngle = Math.atan2(self.anchory - yc, self.anchorx - xc);
        return false;
    };

    self.mouseWheel = function (evt) {
        var activeElem = document.activeElement;
        if (self.contElem != activeElem) return true;
        evt = evt || window.event;
        evt.stopPropagation();
        evt.preventDefault();
        var delta = 6 * Math.sign(evt.wheelDelta || evt.deltaY);
        self.zoomAll(delta);

        self.redrawTxImage();
        return false;
    };

    self.reportPxValue = function (mx, my) {
        if (!self.targets) return;
        var sx = self.xAsPerPixel;
        var sy = self.yAsPerPixel;
        var tmat = self.tMatrix;

        // screen to focal plane
        var xy0 = tmat.s2w(mx * sx, my * sy, 0);

        // focal plane to sky
        var rxy = self.origSkyMatrix.s2w(xy0[0], xy0[1], 0);

        var dec = self.centerDecDeg + (rxy[0] + self.maskOffsetX) / 3600;
        var cosDec = Math.cos(radians(dec));
        cosDec = Math.max(cosDec, 1e-4);
        rxy[1] = (rxy[1] - self.maskOffsetY) / cosDec;
        var raHrs = (self.centerRaDeg - rxy[1] / 3600) / 15;
        while (raHrs > 24) raHrs -= 24;
        while (raHrs < 0) raHrs += 24;

        showMsg("mouseStatus", "RA= <b>" + toSexa(raHrs) + "</b> hrs; DEC= <b>" + toSexa(dec) + "</b> deg");

        if (E("extraStatusDiv")) {
            let skyxy = self.targetMatrix.s2w(xy0[0], xy0[1], 0);
            let msg = `Xarc= ${skyxy[0].toFixed(2)} Yarc= ${skyxy[1].toFixed(2)} `;
            showMsg("extraStatusDiv", msg);
        }
    };

    self.zoomAll = function (mv) {
        var tx = self.tMatrix;
        var cv = self._Canvas;
        var xc = cv.width / 2;
        var yc = cv.height / 2;
        var scale = Math.pow(1.01, mv);
        tx.scaleCenter(scale, xc, yc);
    };

    self.panAll = function (dx, dy) {
        var tx = self.tMatrix;
        tx.translate(dx, dy);
    };

    self.rotateAll = function (diffAngRad) {
        // Rotates the image around center of canvas incrementally
        var tx = self.tMatrix;
        var cv = self._Canvas;
        var xc = cv.width / 2;
        var yc = cv.height / 2;
        tx.rotate(diffAngRad, xc, yc);
    };

    self.panSky = function (dx, dy) {
        var txM = self.tMatrix;
        var scale = txM.getScale();
        var ndxy = txM.rotatePnt(dx, dy, 0);
        var s2 = scale * scale;
        self.targetMatrix.translate(ndxy[0] / s2, ndxy[1] / s2);
        self.origSkyMatrix.translate(ndxy[0] / s2, ndxy[1] / s2);
    };

    self.rotateSky = function (diffAngRad) {
        // Rotates mask around center of canvas incrementally
        self.targetMatrix.rotate(diffAngRad, self.maskOffsetX, self.maskOffsetY);
        self.origSkyMatrix.rotate(diffAngRad, self.maskOffsetX, self.maskOffsetY);
    };

    self.mouseMove = function (evt) {

        self._Canvas.style.cursor = "crosshair";

        function whichButton(evt) {
            var bbb = evt.buttons || evt.which || evt.button;
            if (bbb === 1) return 1;
            if (bbb === 2) return 2;
            if (bbb === 4) return 4;
            return 0;
        }

        // Not used
        function contrasting() {
            // Contrast/Brightness
            var f = (mx - ePos.x) / xc;
            var sc = 1;
            if (0 < f && f < 2) {
                sc = -1.0 / (f - 2);
                var ofs = (127 * (my - ePos.y - yc)) / yc;
                self.filter.setParams(sc, ofs);
            }
        }

        function performMouseAction() {
            var diffAngle = newAngle - self.baseAngle;
            switch (self.mouseAction) {
                case "panAll":
                    self.panAll(dx, dy);
                    break;
                case "panSky":
                    self.panSky(dx, dy);
                    break;
                case "rotateAll":
                    self.rotateAll(diffAngle);
                    break;
                case "rotateSky":
                    self.rotateSky(diffAngle);
                    break;
                case "zoom":
                    break;
                case "contrast":
                    contrasting();
                    break;
            }
        }

        evt = evt || window.event;

        evt.stopPropagation();
        evt.preventDefault();

        var mx = evt.pageX;
        var my = evt.pageY;

        self.mousemx = mx;
        self.mousemy = my;

        var dx = mx - self.lastmx;
        var dy = my - self.lastmy;
        var ePos = getAbsPosition(self.contElem);

        if (!self.dragging) {
            self.reportPxValue(mx - ePos.x, my - ePos.y);
            return;
        }

        var tx = self.tMatrix;
        var cv = self._Canvas;
        var xc = cv.width / 2;
        var yc = cv.height / 2;
        var scale = tx.getScale();

        var newAngle = Math.atan2(my - yc - ePos.y, mx - xc - ePos.x);
        var button = whichButton(evt);

        performMouseAction();

        self.redrawTxImage();
        self.lastmx = mx;
        self.lastmy = my;
        self.baseAngle = newAngle;
        return false;
    };

    self.mouseExit = function (evt) {
        self.dragging = 0;
        self.contElem.blur();
    };

    self.moveLeft = function () {
        self.targetMatrix.translate(-10, 0);
        self.origSkyMatrix.translate(-10, 0);
    };

    self.moveRight = function () {
        self.targetMatrix.translate(+10, 0);
        self.origSkyMatrix.translate(+10, 0);
    };

    self.moveUp = function () {
        self.targetMatrix.translate(0, -10);
        self.origSkyMatrix.translate(0, -10);
    };

    self.moveDown = function () {
        self.targetMatrix.translate(0, 10);
        self.origSkyMatrix.translate(0, 10);
    };


    self.keypressed = function (evt) {
        var activeElem = document.activeElement;
        if (self.contElem != activeElem) return true;
        evt.preventDefault();
        var k = evt.key;
        switch (k) {
            case "a":
                var mx = self.mousemx;
                var my = self.mousemy;
                var ePos = getAbsPosition(self.contElem);
                self.selectTarget(mx - ePos.x, my - ePos.y);
                self.addAlign();
                break;
            case "s":
                var mx = self.mousemx;
                var my = self.mousemy;
                var ePos = getAbsPosition(self.contElem);
                self.selectTarget(mx - ePos.x, my - ePos.y);
                self.selTarget();
                break;
            case "d":
                var mx = self.mousemx;
                var my = self.mousemy;
                var ePos = getAbsPosition(self.contElem);
                self.selectTarget(mx - ePos.x, my - ePos.y);
                self.deselTarget();
                break;
            case "h":
                self.panSky(-5, 0);
                break;
            case "l":
                self.panSky(5, 0);
                break;
            case "j":
                self.panSky(0, 5);
                break;
            case "k":
                self.panSky(0, -5);
                break;
            case "+":
            case ">":
            case ".":
                self.zoomAll(3);
                break;
            case "-":
            case "<":
            case ",":
                self.zoomAll(-3);
                break;
            default:
                break;
        }
        self.redrawTxImage();
        return false;
    };

    self.captureContext = function (evt) {
        var activeElem = document.activeElement;
        if (self.contElem != activeElem) return true;

        return false;
    };

    self.setShowPriorities = function (minP, maxP) {
        self.showMinPriority = Number(minP);
        self.showMaxPriority = Number(maxP);
    };

    self.showBgImage = function (imgUrl, flipY) {
        self.bgImg.src = imgUrl;
        self.flipY = flipY;
    };

    self.fit = function () {
        self.mustFit = 1;
    };

    self.resetDisplay = function () {
        // Refits image and redraw

        self.fitMask(self.maskOffsetX, self.maskOffsetY + 60);

        var tx = self.tMatrix;
        var xy = tx.w2s(0, 0, 0);
        tx.rotate(Math.PI, xy[0], xy[1]);

        // Only for changing contrast, not needed now
        //self.filter.setParams(1, 0);
    };

    self.resetOffsets = function () {
        // Resets the target matrix.
        self.targetMatrix.reset(0);
        self.targetMatrix.scale(1);
        self.origSkyMatrix.reset(0);
        self.origSkyMatrix.scale(1);
        self.origSkyMatrix.rotate(radians(self.origPA), self.maskOffsetX, self.maskOffsetY);
    };

    self.reDrawTable = function () {
        E("targetTableDiv").innerHTML = self.targetTable.showTable();
        self.targetTable.setOnClickCB(self.clickedRow);
        self.targetTable.setSortClickCB(self.reDrawTable);
    };

    self.setGaps = function (gaps) {
        self.xgaps = gaps;
    };

    self.setTargets = function (targets) {
        self.targets = targets.map((tgt) => {
            tgt.raSexa = toSexa(tgt.raHour);
            tgt.decSexa = toSexa(tgt.decDeg);
            return tgt
        })

        self.origSkyMatrix.reset(0);
        self.origSkyMatrix.rotate(radians(self.origPA), self.maskOffsetX, self.maskOffsetY);

        self.targetTable = new TargetTable(self.targets);
        self.reDrawTable();
    };

    self.setMaskLayout = function (layout, guiderFOV, badCols) {
        self.maskLayout = layout;
        self.guiderFOV = guiderFOV;
        self.badColumns = badCols;
        self.findMaskMinMax();
        self.resetDisplay();
        self.resetOffsets();
        self.reallyDrawTxImage();
    };



    E("showGuiderFOV").onchange = self.reallyDrawTxImage;
    E("showBadColumns").onchange = self.reallyDrawTxImage;

    E("panAll").onchange = function () {
        self.mouseAction = "panAll";
    };
    E("panSky").onchange = function () {
        self.mouseAction = "panSky";
    };
    E("rotateAll").onchange = function () {
        self.mouseAction = "rotateAll";
    };
    E("rotateSky").onchange = function () {
        self.mouseAction = "rotateSky";
    };

    E("enableSelection").checked = true;

    self.contElem.onmouseup = self.mouseUp;
    self.contElem.onmousedown = self.mouseDown;
    self.contElem.onmousemove = self.mouseMove;
    self.contElem.onmouseout = self.mouseExit;
    self.contElem.ondblclick = self.doubleClick;
    self.contElem.onwheel = self.mouseWheel;
    window.onkeypress = self.keypressed;
    document.oncontextmenu = self.captureContext;

    self.targetTable = new TargetTable(false);
    self.reDrawTable();

    return this;
}
