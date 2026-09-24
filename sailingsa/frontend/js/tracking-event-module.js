(function () {
  var ENABLED_EVENT = "2026-08-29-lipton-challenge-cup";
  if (window.top !== window) return;
  var match = window.location.pathname.match(/\/regatta\/([^/]+)/);
  var slug = match ? decodeURIComponent(match[1]) : "";
  if (slug !== ENABLED_EVENT) return;

  var link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = "/css/tracking-event-module.css?v=1";
  document.head.appendChild(link);

  var openBtn = document.createElement("button");
  openBtn.type = "button";
  openBtn.className = "tracking-event-open";
  openBtn.textContent = "Tracking";
  var host = document.querySelector(".container") || document.body;
  host.insertBefore(openBtn, host.firstChild);

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

  openBtn.addEventListener("click", function () {
    frame.src = "/tracking-live.html?event=" + encodeURIComponent(slug);
    panel.hidden = false;
    panel.classList.add("is-open");
  });

  window.addEventListener("message", function (ev) {
    if (ev.origin !== window.location.origin) return;
    if (ev.data && ev.data.type === "tracking-live-close") closePanel();
  });
})();
