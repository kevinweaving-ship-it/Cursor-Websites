(function () {
  var pad = document.getElementById("pad-frame");
  var below = document.querySelector(".arial-below");
  if (!pad || !below || pad.parentNode.classList.contains("arial-desk")) return;
  var desk = document.createElement("div");
  desk.className = "arial-desk";
  pad.parentNode.insertBefore(desk, pad);
  desk.appendChild(pad);
  desk.appendChild(below);
})();
