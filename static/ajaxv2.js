function AjaxClass() {
    var self = this;

    function array2Query(arr) {
        var buf = new Array();
        for (idx in arr) {
            buf.push(idx + "=" + arr[idx]);
        }
        return buf.join("&");
    }

    function toValue(xt) {
        if (!xt)
            return false;
        var txt = xt.responseText;
        if (!txt)
            return false;
        if (txt[0] != '{' && txt[0] != '[') return txt;
        return eval('(' + txt + ')');
    }

    self.initialize = function () {
        var xt = false;

        if (typeof XMLHttpRequest != 'undefined') {
            xt = new XMLHttpRequest();
        } else {
            try {
                xt = new ActiveXObject("Msxml2.XMLHTTP");
            } catch (e1) {
                try {
                    xt = new ActiveXObject("Microsoft.XMLHTTP");
                } catch (e2) {
                    xt = false;
                }
            }
        }
        self.maxTime = 120000;
        self.xmlHttp = xt;
    };

    self.setMaxTime = function (mtime) {
        self.maxTime = mtime;
    };

    self.sendRequest = function (call, script, params, callback ) {
        var xt = self.xmlHttp;
        if (!xt)
            return;

        var d = new Date();
        params["rnd"] = d.getTime();
        content = JSON.stringify(params)
        xt.onreadystatechange = function () {
            if (xt.readyState == 4)
                callback(toValue(xt));
        };
        xt.open(call, script, true); // true for asyncrhonuous
        xt.timeout = self.maxTime;
        xt.setRequestHeader("Content-type", "application/json");
        xt.send(content);
    };

    self.getBinary = function (script, params, callback) {
        var xt = self.xmlHttp;
        xt.onload = function (resp) {
            var arrayBuffer = xt.response; // Note: not oReq.responseText
            if (arrayBuffer) {
                callback(arrayBuffer);
            }
        };
        var d = new Date();
        params["rnd"] = d.getTime();
        var query = script + "?" + array2Query(params);
        xt.open("GET", query, true); // true for asyncrhonuous
        xt.responseType = "arraybuffer";
        xt.send('');

    };

    self.end = function () {
        try {
            self.xmlHttp.abort();
        } catch (e) {};
    };

    self.initialize();
} // AjaxClass


function ajaxCall(url, parms, callback) {
    var ajax = new AjaxClass();
    ajax.sendRequest('GET', url, parms, callback);
}

function ajaxPost(url, parms, callback) {
    var ajax = new AjaxClass();
    ajax.sendRequest('POST', url, parms, callback);
}

// vim: ts=4 sw=4 et
