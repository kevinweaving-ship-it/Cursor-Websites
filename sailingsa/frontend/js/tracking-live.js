(function () {
  var params = new URLSearchParams(window.location.search);
  var eventSlug = params.get("event") || "";
  var statusEl = document.getElementById("tracking-live-status");
  var mapEl = document.getElementById("tracking-live-map");
  var names = { 2619: "MagTrack", 2079: "KingPet1" };
  var map = null;
  var markers = {};
  var lines = {};

  function say(text) {
    if (statusEl) statusEl.textContent = text;
  }

  document.getElementById("tracking-live-close").addEventListener("click", function () {
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ type: "tracking-live-close" }, window.location.origin);
    }
  });

  function ensureMap(lat, lon) {
    if (!window.L || !mapEl) return null;
    if (!map) {
      map = L.map(mapEl).setView([lat, lon], 13);
      L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
        maxZoom: 19,
        attribution: "Tiles © Esri"
      }).addTo(map);
    }
    return map;
  }

  function draw(assets) {
    var bounds = [];
    assets.forEach(function (asset) {
      var pos = asset.position || {};
      if (pos.lat == null || pos.lon == null) return;
      var id = asset.userId;
      var label = names[id] || String(id);
      var mapRef = ensureMap(pos.lat, pos.lon);
      if (!mapRef) return;
      bounds.push([pos.lat, pos.lon]);
      if (!markers[id]) {
        markers[id] = L.marker([pos.lat, pos.lon]).addTo(mapRef);
      } else {
        markers[id].setLatLng([pos.lat, pos.lon]);
      }
      var bits = [label];
      if (pos.utc) bits.push(pos.utc);
      if (pos.groundSpeed != null) bits.push("speed " + pos.groundSpeed);
      if (pos.heading != null) bits.push("hdg " + pos.heading);
      markers[id].bindPopup(bits.join(" · "));
      var pts = (asset.track || []).filter(function (p) {
        return p.lat != null && p.lon != null;
      }).map(function (p) { return [p.lat, p.lon]; });
      if (pts.length > 1) {
        if (!lines[id]) lines[id] = L.polyline(pts).addTo(mapRef);
        else lines[id].setLatLngs(pts);
      }
    });
    if (map && bounds.length) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 16 });
  }

  function tick() {
    if (!eventSlug) {
      say("Tracking is off.");
      return;
    }
    var day = new Date().toISOString().slice(0, 10);
    fetch("/api/tracking/live?event=" + encodeURIComponent(eventSlug) + "&date=" + day, { cache: "no-store" })
      .then(function (res) {
        if (res.status === 404) {
          say("Tracking is off for this event.");
          return null;
        }
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (body) {
        if (!body || !body.assets) return;
        draw(body.assets);
        say(body.assets.length + " tracker(s)");
      })
      .catch(function () {
        say("Tracking unavailable.");
      });
  }

  tick();
  setInterval(tick, 8000);
})();
