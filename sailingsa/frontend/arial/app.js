(function () {
    var state = { me: null, devices: [], deviceId: null, view: "dashboard", poll: null };

    function $(id) { return document.getElementById(id); }

    function showFlash(msg, ok) {
        var el = $("flash");
        el.className = "flash " + (ok ? "flash-ok" : "flash-error");
        el.textContent = msg;
        el.classList.remove("hidden");
        setTimeout(function () { el.classList.add("hidden"); }, 5000);
    }

    async function api(path, opts) {
        opts = opts || {};
        var res = await fetch(path, {
            method: opts.method || "GET",
            credentials: "same-origin",
            headers: opts.body ? { "Content-Type": "application/json" } : undefined,
            body: opts.body ? JSON.stringify(opts.body) : undefined
        });
        var data = {};
        try { data = await res.json(); } catch (e) { data = {}; }
        if (!res.ok) {
            var err = (data && (data.error || data.detail)) || ("HTTP " + res.status);
            throw new Error(typeof err === "string" ? err : JSON.stringify(err));
        }
        return data;
    }

    function pillClass(v) {
        v = String(v || "").toLowerCase();
        if (v === "online" || v === "ok" || v === "disarm" || v === "closed" || v === "c") return "pill-ok";
        if (v === "arm" || v === "stay" || v === "sleep" || v === "active" || v === "a" || v === "notready") return "pill-warn";
        if (v === "alarm" || v === "al" || v === "offline") return "pill-bad";
        return "pill-info";
    }

    function formatWhen(ms) {
        if (!ms) return "—";
        var d = new Date(Number(ms));
        if (isNaN(d.getTime())) return String(ms);
        return d.toLocaleString("en-ZA", { hour12: false });
    }

    function setView(name) {
        state.view = name;
        ["auth", "dashboard", "events", "profile"].forEach(function (v) {
            var el = $("view-" + v);
            if (el) el.classList.toggle("hidden", v !== name);
        });
        document.querySelectorAll(".header-nav a").forEach(function (a) {
            a.classList.toggle("is-active", a.getAttribute("data-view") === name);
        });
        if (name === "events") loadEvents();
        if (name === "profile") fillProfile();
        if (name === "dashboard") loadDevices();
    }

    function paintAuthNav() {
        var a = $("nav-auth");
        if (state.me) {
            a.textContent = "Sign out";
            a.setAttribute("data-view", "logout");
        } else {
            a.textContent = "Sign in";
            a.setAttribute("data-view", "auth");
        }
    }

    function fillProfile() {
        if (!state.me) return;
        $("prof-name").value = state.me.display_name || "";
        $("prof-email").value = state.me.email || "";
        $("prof-phone").value = state.me.phone || "";
        $("prof-notes").value = state.me.notes || "";
    }

    function areaButtons(device, area) {
        var actions = ((device.deviceAlarmTypeActions || {}).areas) || [];
        var map = {
            "area-disarm": "Disarm",
            "area-arm": "Arm",
            "area-stay": "Stay",
            "area-sleep": "Sleep"
        };
        return actions.map(function (cmd) {
            return '<button type="button" data-cmd="' + cmd + '" data-num="' + area.num + '" data-id="' + device.deviceId + '">' + (map[cmd] || cmd) + "</button>";
        }).join("");
    }

    function renderDevice(device) {
        state.deviceId = device.deviceId;
        var st = device.deviceState || {};
        $("device-meta").innerHTML =
            "<h2 class=\"section-title\">" + (device.deviceName || "Device") + "</h2>" +
            "<div class=\"stats-row\">" +
            "<span>Status <span class=\"pill " + pillClass(device.deviceStatus) + "\">" + (device.deviceStatus || "—") + "</span></span>" +
            "<span>Panel " + (device.deviceAlarmType || "") + " / " + (device.deviceType || "") + "</span>" +
            "<span>AC <span class=\"pill " + pillClass(st.powerAC) + "\">" + (st.powerAC || "—") + "</span></span>" +
            "<span>Battery <span class=\"pill " + pillClass(st.powerBattery) + "\">" + (st.powerBattery || "—") + "</span></span>" +
            "<span>Updated " + formatWhen(device.deviceTimestamp) + "</span>" +
            "</div>" +
            "<p class=\"muted\">Dev dashboard · shared Olarm account · arm/disarm talks to the live panel.</p>";

        var areasHtml = (device.arialAreas || []).map(function (area) {
            return "<div class=\"card\">" +
                "<h2 class=\"section-title\">" + area.label + "</h2>" +
                "<p>State <span class=\"pill " + pillClass(area.state) + "\">" + (area.state || "—") + "</span></p>" +
                "<div class=\"btn-row\">" + areaButtons(device, area) + "</div>" +
                "</div>";
        }).join("");
        $("device-areas").innerHTML = areasHtml || "<div class=\"card\"><p class=\"muted\">No areas on this device.</p></div>";

        var tb = document.querySelector("#zones-table tbody");
        tb.innerHTML = (device.arialZones || []).map(function (z) {
            return "<tr><td>" + z.num + "</td><td>" + z.label + "</td><td>" + z.typeLabel + "</td><td><span class=\"pill " +
                pillClass(z.state) + "\">" + z.stateLabel + "</span></td></tr>";
        }).join("") || "<tr><td colspan=\"4\">No named zones</td></tr>";
    }

    async function loadDevices() {
        if (!state.me) return;
        try {
            var data = await api("/api/arial/devices");
            state.devices = data.devices || [];
            if (!state.devices.length) {
                $("device-meta").innerHTML = "<h2 class=\"section-title\">No devices</h2><p class=\"muted\">Olarm returned no panels for this token.</p>";
                return;
            }
            renderDevice(state.devices[0]);
        } catch (e) {
            showFlash(e.message || String(e), false);
        }
    }

    async function loadEvents() {
        if (!state.me || !state.deviceId) return;
        try {
            var data = await api("/api/arial/devices/" + encodeURIComponent(state.deviceId) + "/events?limit=30");
            var tb = document.querySelector("#events-table tbody");
            tb.innerHTML = (data.events || []).map(function (ev) {
                return "<tr><td>" + formatWhen(ev.eventTime) + "</td><td>" + (ev.eventMsg || (ev.eventAction + " " + ev.eventState)) +
                    "</td><td>" + (ev.userFullname || "—") + "</td></tr>";
            }).join("") || "<tr><td colspan=\"3\">No events</td></tr>";
        } catch (e) {
            showFlash(e.message || String(e), false);
        }
    }

    async function sendAction(deviceId, cmd, num) {
        var label = cmd + (num ? (" #" + num) : "");
        if (!window.confirm("Send " + label + " to the live alarm?")) return;
        try {
            await api("/api/arial/devices/" + encodeURIComponent(deviceId) + "/actions", {
                method: "POST",
                body: { actionCmd: cmd, actionNum: num }
            });
            showFlash("Sent " + label, true);
            await loadDevices();
        } catch (e) {
            showFlash(e.message || String(e), false);
        }
    }

    async function refreshMe() {
        try {
            var st = await api("/api/arial/status");
            state.me = st.signedIn ? st.me : null;
            if (!st.olarmConfigured) showFlash("OLARM_API_TOKEN is not set on the API process", false);
        } catch (e) {
            state.me = null;
        }
        paintAuthNav();
        if (state.me) {
            if (state.view === "auth") setView("dashboard");
            else if (state.view === "dashboard") loadDevices();
        } else {
            setView("auth");
        }
    }

    function startPoll() {
        if (state.poll) clearInterval(state.poll);
        state.poll = setInterval(function () {
            if (state.me && state.view === "dashboard") loadDevices();
            if (state.me && state.view === "events") loadEvents();
        }, 8000);
    }

    document.querySelector(".header-nav").addEventListener("click", function (ev) {
        var a = ev.target.closest("a");
        if (!a) return;
        ev.preventDefault();
        var v = a.getAttribute("data-view");
        if (v === "logout") {
            api("/api/arial/auth/logout", { method: "POST" }).then(function () {
                state.me = null;
                paintAuthNav();
                setView("auth");
            });
            return;
        }
        if (!state.me && v !== "auth") {
            setView("auth");
            return;
        }
        setView(v);
    });

    $("device-areas").addEventListener("click", function (ev) {
        var btn = ev.target.closest("button");
        if (!btn) return;
        sendAction(btn.getAttribute("data-id"), btn.getAttribute("data-cmd"), Number(btn.getAttribute("data-num")));
    });

    $("btn-login").addEventListener("click", async function () {
        try {
            var data = await api("/api/arial/auth/login", {
                method: "POST",
                body: { email: $("auth-email").value, password: $("auth-password").value }
            });
            state.me = data.me;
            paintAuthNav();
            setView("dashboard");
        } catch (e) { showFlash(e.message, false); }
    });

    $("btn-register").addEventListener("click", async function () {
        try {
            var data = await api("/api/arial/auth/register", {
                method: "POST",
                body: {
                    email: $("auth-email").value,
                    password: $("auth-password").value,
                    display_name: $("auth-name").value
                }
            });
            state.me = data.me;
            paintAuthNav();
            setView("profile");
            fillProfile();
            showFlash("Profile created", true);
        } catch (e) { showFlash(e.message, false); }
    });

    $("btn-save-profile").addEventListener("click", async function () {
        try {
            var data = await api("/api/arial/me", {
                method: "PUT",
                body: {
                    display_name: $("prof-name").value,
                    phone: $("prof-phone").value,
                    notes: $("prof-notes").value
                }
            });
            state.me = data.me;
            showFlash("Profile saved", true);
        } catch (e) { showFlash(e.message, false); }
    });

    $("btn-logout").addEventListener("click", async function () {
        await api("/api/arial/auth/logout", { method: "POST" });
        state.me = null;
        paintAuthNav();
        setView("auth");
    });

    refreshMe().then(startPoll);
})();
