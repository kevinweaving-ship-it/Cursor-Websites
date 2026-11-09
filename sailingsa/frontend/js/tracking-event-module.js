(function () {
  if (window.top !== window) return;
  var slot = document.getElementById("tracking-event-slot");
  if (!slot) return;
  var slug = slot.getAttribute("data-event") || "";
  if (!slug) return;

  var link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "/css/tracking-event-module.css?v=2";
  document.head.appendChild(link);

  var panel = document.createElement("div");
  panel.className = "tracking-event-module";
  panel.hidden = true;
  var frame = document.createElement("iframe");
  frame.title = "Live tracking";
  frame.src = "about:blank";
  panel.appendChild(frame);
  document.body.appendChild(panel);

  function closePanel() {
    panel.classList.remove("is-open");
    panel.hidden = true;
    frame.src = "about:blank";
  }

  window.addEventListener("message", function (ev) {
    if (ev.origin !== window.location.origin) return;
    if (ev.data && ev.data.type === "tracking-live-close") closePanel();
  });

  fetch("/api/tracking/live?event=" + encodeURIComponent(slug), { cache: "no-store" })
    .then(function (res) {
      if (!res.ok) return null;
      return res.json();
    })
    .then(function (body) {
      if (!body || !body.show || !body.assets || !body.assets.length) return;
      var card = document.createElement("section");
      card.className = "tracking-event-card";
      var title = document.createElement("h2");
      title.className = "tracking-event-card-title";
      title.textContent = "Tracking";
      var line = document.createElement("p");
      line.className = "tracking-event-card-assets";
      line.textContent = body.assets.map(function (asset) {
        return (asset.name || "Tracker") + " " + asset.userId;
      }).join(", ");
      var openBtn = document.createElement("button");
      openBtn.type = "button";
      openBtn.className = "tracking-event-open";
      openBtn.textContent = "Open tracking";
      openBtn.addEventListener("click", function () {
        frame.src = "/tracking-live.html?event=" + encodeURIComponent(slug);
        panel.hidden = false;
        panel.classList.add("is-open");
      });
      card.appendChild(title);
      card.appendChild(line);
      card.appendChild(openBtn);
      slot.appendChild(card);
    })
    .catch(function () {});
})();
