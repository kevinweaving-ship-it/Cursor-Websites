(function () {
    var statusText = "";

    function pad(n) {
        return String(n).padStart(2, "0");
    }

    function tickTime() {
        var d = new Date();
        var el = document.getElementById("lcd-time");
        if (el) el.textContent = pad(d.getHours()) + ":" + pad(d.getMinutes());
    }

    function statusFromDevice(device) {
        var areas = (device && device.arialAreas) || [];
        var st = areas.length ? String(areas[0].state || "").toLowerCase() : "";
        if (st.indexOf("alarm") !== -1) return "Alarm";
        if (st === "arm") return "System Armed";
        if (st === "stay") return "Stay Armed";
        if (st === "sleep") return "Sleep Armed";
        if (st === "disarm") return "System Ready";
        if (st === "notready") return "Not Ready";
        return st ? st : "";
    }

    async function loadStatus() {
        try {
            var res = await fetch("/api/arial/devices", { credentials: "same-origin" });
            var data = await res.json();
            if (!res.ok) return;
            var devices = data.devices || [];
            var hanse = devices.filter(function (d) {
                return /hansekop/i.test(d.deviceName || "");
            })[0] || devices[0];
            statusText = statusFromDevice(hanse);
            var el = document.getElementById("lcd-2");
            if (el) el.textContent = statusText;
        } catch (e) { /* keep last status */ }
    }

    window.setArialLcd = function (top, bottom) {
        var site = document.getElementById("lcd-site");
        if (site && top != null) site.textContent = String(top);
        var line2 = document.getElementById("lcd-2");
        if (line2 && bottom != null) line2.textContent = String(bottom);
    };

    document.querySelector(".pad").addEventListener("click", function (ev) {
        var btn = ev.target.closest("[data-key]");
        if (!btn) return;
        var key = btn.getAttribute("data-key");
        if (typeof window.onArialKey === "function") window.onArialKey(key);
    });

    tickTime();
    loadStatus();
    setInterval(tickTime, 1000);
    setInterval(loadStatus, 8000);
})();
