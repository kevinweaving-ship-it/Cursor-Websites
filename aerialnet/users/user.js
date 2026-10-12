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
  if (nameEl) nameEl.textContent = user.name || user.from || "";
  if (logout) {
    logout.addEventListener("click", function (ev) {
      ev.preventDefault();
      try { localStorage.removeItem("arialUser"); } catch (e) {}
      try { sessionStorage.removeItem("arialUser"); } catch (e2) {}
      window.location.href = "/";
    });
  }
})();
