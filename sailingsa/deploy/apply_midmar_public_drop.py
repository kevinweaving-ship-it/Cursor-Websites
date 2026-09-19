#!/usr/bin/env python3
"""Public preview matches real public; SA video drag-drop no longer blocked by file input overlay."""
from pathlib import Path
import shutil
import time

MARK = "MIDMAR_PUBLIC_DROP_v1"
SRC = Path("/tmp/midmar-media-rotate.js")
DEST = Path("/var/www/sailingsa/js/midmar-media-rotate.js")
MEDIA = Path("/var/www/sailingsa/js/midmar-live-media.js")
API = Path("/var/www/sailingsa/api/api.py")

Z_OLD = (
    '      ".regatta-page .regatta-sa-mode-wrap{position:relative;z-index:80;pointer-events:auto;}",\n'
)
FILE_OLD = (
    '      ".midmar-mm-sa-file{position:absolute;left:0;top:0;width:100%;height:100%;max-width:100%;max-height:100%;opacity:0;cursor:pointer;z-index:2;}",\n'
    '      ".midmar-mm-sa-drop.has-file .midmar-mm-sa-file{pointer-events:none;}",'
)
FILE_NEW = (
    '      ".midmar-mm-sa-file{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0;opacity:0;pointer-events:none;}",\n'
    '      ".midmar-mm-sa-drop{cursor:pointer;}",'
)

VIS_OLD = """  function applySaVis(host, sa, isSa) {
    var show = !!isSa && saEditOn();
    if (host) host.classList.toggle("midmar-live-media--sa", !!isSa);
    if (sa) {
      if (show) sa.removeAttribute("hidden");
      else sa.setAttribute("hidden", "");
    }
  }"""

VIS_NEW = """  function applySaVis(host, sa, isSa) {
    var show = !!isSa && saEditOn();
    if (host) host.classList.toggle("midmar-live-media--sa", !!show);
    if (sa) {
      var row = document.getElementById("midmar-mm-row");
      if (show) {
        sa.removeAttribute("hidden");
        if (row && sa.parentNode !== row) row.appendChild(sa);
      } else {
        sa.setAttribute("hidden", "");
        if (sa.parentNode) sa.parentNode.removeChild(sa);
      }
    }
  }"""

BIND_OLD = """    function onDrop(e) {
      e.preventDefault();
      e.stopPropagation();
      if (drop) drop.classList.remove("is-on");
      var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f && mediaOk(f)) showFile(f);
      else setMsg("Use a photo or video.");
    }
    if (fi) {
      fi.addEventListener("change", function () {
        var f = fi.files && fi.files[0];
        fi.value = "";
        if (f && mediaOk(f)) showFile(f);
      });
    }
    if (drop) {
      ["dragenter", "dragover"].forEach(function (ev) {
        drop.addEventListener(ev, function (e) {
          e.preventDefault();
          drop.classList.add("is-on");
        });
      });
      drop.addEventListener("dragleave", function (e) {
        if (!drop.contains(e.relatedTarget)) drop.classList.remove("is-on");
      });
      drop.addEventListener("drop", onDrop, true);
    }"""

BIND_NEW = """    function takeFile(f) {
      if (f && mediaOk(f)) showFile(f);
      else setMsg("Use a photo or video.");
    }
    function onDrop(e) {
      e.preventDefault();
      e.stopPropagation();
      if (drop) drop.classList.remove("is-on");
      var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      takeFile(f);
    }
    function allowDrag(e) {
      e.preventDefault();
      e.stopPropagation();
      try { if (e.dataTransfer) e.dataTransfer.dropEffect = "copy"; } catch (err) {}
      if (drop) drop.classList.add("is-on");
    }
    if (fi) {
      fi.addEventListener("change", function () {
        var f = fi.files && fi.files[0];
        fi.value = "";
        takeFile(f);
      });
    }
    if (drop) {
      ["dragenter", "dragover"].forEach(function (ev) {
        drop.addEventListener(ev, allowDrag);
      });
      drop.addEventListener("dragleave", function (e) {
        if (!drop.contains(e.relatedTarget)) drop.classList.remove("is-on");
      });
      drop.addEventListener("drop", onDrop, true);
      drop.addEventListener("click", function (e) {
        if (e.target && e.target.closest && e.target.closest("button, input, textarea, a")) return;
        if (fi) fi.click();
      });
    }
    if (sa && sa.getAttribute("data-mm-sa-drag") !== "1") {
      sa.setAttribute("data-mm-sa-drag", "1");
      ["dragenter", "dragover"].forEach(function (ev) {
        sa.addEventListener(ev, allowDrag);
      });
      sa.addEventListener("drop", onDrop, true);
    }"""


def main() -> None:
    src = SRC.read_text()
    if "revertBox" not in src:
        raise SystemExit("MISSING_OR_BAD_SRC")
    DEST.write_text(src)
    DEST.chmod(0o644)
    print("JS_OK", DEST.stat().st_size)

    ts = time.strftime("%Y%m%d_%H%M%S")
    media = MEDIA.read_text()
    if MARK in media:
        print("MEDIA_ALREADY")
    else:
        bak = MEDIA.with_name(f"midmar-live-media.js.bak.pubdrop.{ts}")
        shutil.copy2(MEDIA, bak)
        print("BACKUP_MEDIA", bak)
        if Z_OLD in media:
            media = media.replace(Z_OLD, "", 1)
            print("Z80_GONE")
        if FILE_OLD not in media:
            raise SystemExit("FILE_CSS_MISSING")
        media = media.replace(FILE_OLD, FILE_NEW, 1)
        print("FILE_CSS_OK")
        if VIS_OLD not in media:
            raise SystemExit("VIS_MISSING")
        media = media.replace(VIS_OLD, VIS_NEW, 1)
        print("VIS_OK")
        if BIND_OLD not in media:
            raise SystemExit("BIND_MISSING")
        media = media.replace(BIND_OLD, BIND_NEW, 1)
        print("BIND_OK")
        media = media.replace('JS_VER = "midmarwx43"', 'JS_VER = "midmarwx44"', 1)
        media = media.replace(
            'loadScript("/js/midmar-media-rotate.js?v=mmrot2");',
            'loadScript("/js/midmar-media-rotate.js?v=mmrot3");',
            1,
        )
        media = media.replace("  var JS_VER = ", "  // " + MARK + "\n  var JS_VER = ", 1)
        MEDIA.write_text(media)
        print("MEDIA_OK", MEDIA.stat().st_size)

    api = API.read_text()
    api2 = api.replace("midmar-live-media.js?v=midmarwx43", "midmar-live-media.js?v=midmarwx44")
    api2 = api2.replace("midmar-media-rotate.js?v=mmrot2", "midmar-media-rotate.js?v=mmrot3")
    if api2 != api:
        API.write_text(api2)
        print("API_TAG_OK")
    else:
        print("API_TAG_ALREADY")


if __name__ == "__main__":
    main()
