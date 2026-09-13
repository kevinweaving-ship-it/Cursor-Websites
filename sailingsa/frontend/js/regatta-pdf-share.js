/* Cape Classic / regatta results PDF share + print.
 * Keep this as a src file. Inlining it into the sheet HTML lets a footer
 * splice steal the first body/html closer and dump the rest as page text.
 */
(function () {
  var _pdfFile = null;
  var _pdfWarm = null;
  var _pdfJsWarm = null;

  function sheetUrl() {
    var c = document.querySelector('link[rel="canonical"]');
    if (c && c.href && c.href.indexOf("http") === 0) {
      return c.href.split("#")[0].split("?")[0];
    }
    var u = (location.href || "").split("#")[0].split("?")[0];
    if (u.indexOf("http") === 0) return u;
    var p = location.pathname || "";
    if (p.indexOf("/regatta/") === 0) {
      return "https://sailingsa.co.za" + p.replace(/\/+$/, "");
    }
    return "";
  }

  function pdfPath() {
    var p = (location.pathname || "").replace(/\/+$/, "");
    if (p.indexOf("/regatta/") !== 0) return "";
    if (/\/results\.pdf$/i.test(p)) return p;
    return p + "/results.pdf";
  }

  function pdfAbs() {
    var p = pdfPath();
    if (!p) return "";
    if (p.indexOf("http") === 0) return p;
    return (location.origin || "https://sailingsa.co.za") + p;
  }

  function pdfTitle() {
    var n = document.querySelector(".regatta-name");
    var t = (n && n.textContent || document.title || "SailingSA results")
      .replace(/\s*\|\s*SailingSA\s*$/i, "")
      .replace(/\s+/g, " ")
      .trim();
    return t || "SailingSA results PDF";
  }

  function pdfFileName() {
    var p = pdfPath().replace(/\/+$/, "").replace(/\/results\.pdf$/i, "");
    var tail = (p.split("/").filter(Boolean).pop() || "results").replace(/\.pdf$/i, "");
    return tail + ".pdf";
  }

  function setPdfStatus(msg) {
    var host = document.getElementById("ssaPdfView");
    if (!host) return;
    host.innerHTML = '<p class="ssa-pdf-status"></p>';
    host.firstChild.textContent = msg || "Loading PDF\u2026";
  }

  function loadPdfFile() {
    var u = pdfAbs();
    if (!u) return Promise.reject(new Error("no-pdf"));
    return fetch(u, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("pdf");
        return r.blob();
      })
      .then(function (blob) {
        var file = new File([blob], pdfFileName(), { type: "application/pdf" });
        _pdfFile = file;
        return file;
      });
  }

  function warmPdf() {
    if (!_pdfWarm) {
      _pdfWarm = loadPdfFile().catch(function (err) {
        _pdfWarm = null;
        throw err;
      });
    }
    return _pdfWarm;
  }

  function withPdfFile(fn) {
    if (_pdfFile) return Promise.resolve(fn(_pdfFile));
    return warmPdf().then(fn);
  }

  function loadPdfJs() {
    if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
    if (_pdfJsWarm) return _pdfJsWarm;
    _pdfJsWarm = new Promise(function (res, rej) {
      var s = document.createElement("script");
      s.src = (location.origin || "") + "/js/vendor/pdfjs/pdf.min.js";
      s.onload = function () {
        try {
          if (window.pdfjsLib && pdfjsLib.GlobalWorkerOptions) {
            pdfjsLib.GlobalWorkerOptions.workerSrc =
              (location.origin || "") + "/js/vendor/pdfjs/pdf.min.js";
          }
        } catch (e) {}
        res(window.pdfjsLib);
      };
      s.onerror = function () {
        _pdfJsWarm = null;
        rej(new Error("pdfjs"));
      };
      document.head.appendChild(s);
    });
    return _pdfJsWarm;
  }

  function renderPdfPreview(file) {
    var host = document.getElementById("ssaPdfView");
    if (!host || !file) return Promise.reject(new Error("view"));
    setPdfStatus("Opening PDF\u2026");
    return file.arrayBuffer().then(function (buf) {
      return loadPdfJs()
        .then(function (pdfjs) {
          if (!pdfjs || !pdfjs.getDocument) throw new Error("pdfjs");
          return pdfjs.getDocument({ data: buf, disableWorker: true }).promise;
        })
        .then(function (pdf) {
          host.innerHTML = "";
          var scale = Math.max(1.15, (host.clientWidth || 480) / 612);
          var chain = Promise.resolve();
          for (var n = 1; n <= pdf.numPages; n++) {
            (function (pageNo) {
              chain = chain
                .then(function () {
                  return pdf.getPage(pageNo);
                })
                .then(function (page) {
                  var vp = page.getViewport({ scale: scale });
                  var canvas = document.createElement("canvas");
                  canvas.width = vp.width;
                  canvas.height = vp.height;
                  canvas.setAttribute("aria-label", "PDF page " + pageNo);
                  host.appendChild(canvas);
                  return page.render({
                    canvasContext: canvas.getContext("2d"),
                    viewport: vp,
                  }).promise;
                });
            })(n);
          }
          return chain;
        });
    });
  }

  function sharePdfFile(file) {
    if (!file || !navigator.share) return Promise.reject(new Error("no-share"));
    var payload = { files: [file], title: pdfTitle() };
    if (navigator.canShare && !navigator.canShare(payload)) {
      return Promise.reject(new Error("no-files"));
    }
    return navigator.share(payload);
  }

  function downloadPdfFile(file) {
    if (!file) return;
    var url = URL.createObjectURL(file);
    var a = document.createElement("a");
    a.href = url;
    a.download = pdfFileName();
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 2500);
  }

  function sharePdfAttach() {
    withPdfFile(function (file) {
      return sharePdfFile(file).catch(function () {
        downloadPdfFile(file);
      });
    }).catch(function () {
      downloadPdfAttach();
    });
  }

  function downloadPdfAttach() {
    withPdfFile(function (file) {
      downloadPdfFile(file);
    }).catch(function () {
      var u = pdfAbs();
      if (!u) return;
      var a = document.createElement("a");
      a.href = u + (u.indexOf("?") >= 0 ? "&" : "?") + "download=1";
      a.download = pdfFileName();
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
  }

  function printPdf() {
    var u = pdfAbs();
    if (!u) return;
    var fr = document.getElementById("ssaPdfPrintFrame");
    if (!fr) {
      fr = document.createElement("iframe");
      fr.id = "ssaPdfPrintFrame";
      fr.setAttribute("title", "Print PDF");
      fr.style.cssText =
        "position:fixed;right:0;bottom:0;width:1px;height:1px;opacity:0;border:0";
      document.body.appendChild(fr);
    }
    var printed = false;
    var fallback = setTimeout(function () {
      if (printed) return;
      window.open(u, "_blank", "noopener");
    }, 1600);
    fr.onload = function () {
      printed = true;
      clearTimeout(fallback);
      try {
        fr.contentWindow.focus();
        fr.contentWindow.print();
      } catch (e) {
        window.open(u, "_blank", "noopener");
      }
    };
    fr.src = u;
  }

  function shareEventUrl() {
    var t = pdfTitle();
    var u = sheetUrl() || location.href;
    var b = document.getElementById("regattaShareBtn");
    function copied() {
      if (!b) return;
      var old = b.textContent;
      b.textContent = "URL copied";
      setTimeout(function () {
        b.textContent = old || "Share URL";
      }, 1600);
    }
    if (navigator.share) {
      navigator.share({ title: t, url: u }).catch(function () {});
      return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(u).then(copied).catch(function () {
        prompt("Copy this URL:", u);
      });
      return;
    }
    prompt("Copy this URL:", u);
  }

  function openChooser() {
    var el = document.getElementById("ssaPrintChooser");
    if (!el) return;
    if (!pdfPath()) return;
    var dl = document.getElementById("ssaPdfDownload");
    if (dl) {
      dl.setAttribute("href", pdfPath() + "?download=1");
      dl.setAttribute("download", pdfFileName());
    }
    setPdfStatus("Loading PDF\u2026");
    el.classList.add("is-open");
    withPdfFile(function (file) {
      return renderPdfPreview(file).catch(function () {
        setPdfStatus(
          "PDF is ready. Use Download or Print if the preview cannot open in this browser."
        );
      });
    }).catch(function () {
      setPdfStatus("Could not load the PDF file.");
    });
  }

  function closeChooser() {
    var el = document.getElementById("ssaPrintChooser");
    if (el) el.classList.remove("is-open");
  }

  window.ssaRegattaPrint = openChooser;
  document.addEventListener("click", function (ev) {
    var t = ev.target;
    if (t && t.id === "ssaPrintChooser") {
      closeChooser();
      return;
    }
    var hit = t && t.closest ? t.closest("[data-ssa-print]") : null;
    if (!hit) return;
    var act = hit.getAttribute("data-ssa-print");
    if (act === "whatsapp" || act === "email") {
      ev.preventDefault();
      sharePdfAttach();
      return;
    }
    if (act === "download") {
      ev.preventDefault();
      downloadPdfAttach();
      return;
    }
    if (act === "printer") {
      ev.preventDefault();
      printPdf();
      return;
    }
    if (act === "cancel") {
      ev.preventDefault();
      closeChooser();
    }
  });
  var b = document.getElementById("regattaShareBtn");
  if (b) {
    b.addEventListener("click", function () {
      shareEventUrl();
    });
  }
  warmPdf();
})();
