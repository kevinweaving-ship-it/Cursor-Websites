(function () {
  var slug = document.body.getAttribute("data-user") || "";
  var nameEl = document.getElementById("header-user");
  var logout = document.getElementById("user-logout");

  function readSession() {
    var raw = null;
    try { raw = localStorage.getItem("arialUser"); } catch (e) {}
    if (!raw) return null;
    try { return JSON.parse(raw); } catch (e2) { return null; }
  }

  function userSlug(user) {
    var url = user && user.url ? String(user.url) : "";
    var match = /\/users\/([^/]+)/.exec(url);
    return match ? match[1] : "";
  }

  var user = readSession();
  if (!user || userSlug(user) !== slug) {
    window.location.replace("/");
    return;
  }
  if (nameEl) {
    nameEl.textContent = user.name || user.from || "";
    if (user.url) nameEl.setAttribute("href", user.url);
  }
  var panel = document.body.getAttribute("data-panel");
  var page = document.querySelector(".page");
  if (panel && page && !page.querySelector(".panel-frame")) {
    var frame = document.createElement("iframe");
    frame.className = "panel-frame";
    frame.title = "Keypad";
    frame.setAttribute("referrerpolicy", "no-referrer");
    frame.src = panel;
    page.appendChild(frame);
  }
  if (logout) {
    logout.addEventListener("click", function (ev) {
      ev.preventDefault();
      try { localStorage.removeItem("arialUser"); } catch (e) {}
      try { sessionStorage.removeItem("arialUser"); } catch (e2) {}
      window.location.href = "/";
    });
  }
  window.addEventListener("message", function (ev) {
    if (ev.origin !== window.location.origin) return;
    var data = ev.data || {};
    if (data.type === "arial-user" && !data.user) window.location.href = "/";
  });
})();
