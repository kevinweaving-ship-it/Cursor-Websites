/* Cape Classic / regatta results PDF share + print.
 * Keep this as a src file. Inlining it into the sheet HTML lets a footer
 * splice steal the first body/html closer and dump the rest as page text.
 * Print / preview use the stored PDF URL. Never pdf.js (it freezes on the
 * 4.5MB Cape Classic file). Never delayed window.open (iOS blocks it).
 */
(function () {
  var _pdfFile = null;
  var _pdfWarm = null;

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

  function wirePdfLinks() {
    var p = pdfPath();
    if (!p) return p;
    var abs = pdfAbs();
    var dl = document.getElementById("ssaPdfDownload");
    if (dl) {
      dl.setAttribute("href", p + "?download=1");
      dl.setAttribute("download", pdfFileName());
    }
    var pr = document.getElementById("ssaPdfPrint");
    if (pr) {
      pr.setAttribute("href", abs || p);
      pr.setAttribute("target", "_blank");
      pr.setAttribute("rel", "noopener");
    }
    return p;
  }

  function setPdfStatus(msg) {
    var host = document.getElementById("ssaPdfView");
    if (!host) return;
    host.innerHTML = '<p class="ssa-pdf-status"></p>';
    host.firstChild.textContent = msg || "Loading PDF\u2026";
  }

  function embedPdfFrame(host, u) {
    host.innerHTML = "";
    var fr = document.createElement("iframe");
    fr.setAttribute("title", pdfTitle());
    fr.setAttribute("src", u);
    host.appendChild(fr);
  }

  function showPdfPreview() {
    var host = document.getElementById("ssaPdfView");
    if (!host) return;
    var u = pdfAbs();
    if (!u) {
      setPdfStatus("Could not load the PDF file.");
      return;
    }
    embedPdfFrame(host, u);
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

  function u8ToB64(u8) {
    var chunk = 0x8000;
    var s = "";
    for (var i = 0; i < u8.length; i += chunk) {
      s += String.fromCharCode.apply(null, u8.subarray(i, i + chunk));
    }
    return btoa(s);
  }

  function wrap76(b64) {
    return String(b64 || "").replace(/.{1,76}/g, "$&\r\n");
  }

  function emlSubject(s) {
    s = String(s || "SailingSA results");
    if (/^[\x20-\x7e]*$/.test(s)) return s;
    try {
      return "=?UTF-8?B?" + btoa(unescape(encodeURIComponent(s))) + "?=";
    } catch (e) {
      return "SailingSA results";
    }
  }

  function pdfAsEml(file) {
    var name = pdfFileName();
    return file.arrayBuffer().then(function (buf) {
      var b64 = wrap76(u8ToB64(new Uint8Array(buf)));
      var bnd = "ssa_pdf_" + Date.now();
      return (
        "X-Unsent: 1\r\n" +
        "MIME-Version: 1.0\r\n" +
        "To: \r\n" +
        "Subject: " +
        emlSubject(pdfTitle()) +
        "\r\n" +
        'Content-Type: multipart/mixed; boundary="' +
        bnd +
        '"\r\n' +
        "\r\n" +
        "--" +
        bnd +
        "\r\n" +
        'Content-Type: application/pdf; name="' +
        name +
        '"\r\n' +
        "Content-Transfer-Encoding: base64\r\n" +
        'Content-Disposition: attachment; filename="' +
        name +
        '"\r\n' +
        "\r\n" +
        b64 +
        "\r\n" +
        "--" +
        bnd +
        "--\r\n"
      );
    });
  }

  function openEmailWithPdf(file) {
    return pdfAsEml(file).then(function (eml) {
      var blob = new Blob([eml], { type: "message/rfc822" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url;
      a.download = pdfFileName().replace(/\.pdf$/i, "") + ".eml";
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(function () {
        URL.revokeObjectURL(url);
      }, 8000);
    });
  }

  function sharePdfFileOnly(file) {
    if (!file || !navigator.share) return Promise.reject(new Error("no-share"));
    var payload = { files: [file] };
    if (navigator.canShare && !navigator.canShare(payload)) {
      return Promise.reject(new Error("no-files"));
    }
    return navigator.share(payload);
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

  function openWhatsAppUrl() {
    var t = pdfTitle();
    var u = sheetUrl() || pdfAbs() || location.href;
    var text = encodeURIComponent(t + "\n" + u);
    window.open("https://wa.me/?text=" + text, "_blank", "noopener");
  }

  function openMailtoUrl() {
    var t = pdfTitle();
    var u = sheetUrl() || pdfAbs() || location.href;
    location.href =
      "mailto:?subject=" +
      encodeURIComponent(t) +
      "&body=" +
      encodeURIComponent(t + "\n" + u);
  }

  function emailPdf() {
    withPdfFile(function (file) {
      return sharePdfFileOnly(file).catch(function (err) {
        if (err && err.name === "AbortError") return;
        return openEmailWithPdf(file).catch(function () {
          openMailtoUrl();
        });
      });
    }).catch(function () {
      openMailtoUrl();
    });
  }

  function whatsappPdf() {
    withPdfFile(function (file) {
      return sharePdfFileOnly(file).catch(function (err) {
        if (err && err.name === "AbortError") return;
        openWhatsAppUrl();
      });
    }).catch(function () {
      openWhatsAppUrl();
    });
  }

  function printPdf() {
    var u = pdfAbs();
    if (!u) return false;
    var w = window.open(u, "_blank");
    if (w) {
      try {
        w.focus();
      } catch (e) {}
      return true;
    }
    location.assign(u);
    return true;
  }

  function flashShareBtn(msg) {
    var b = document.getElementById("regattaShareBtn");
    if (!b) return;
    var old = b.getAttribute("data-ssa-share-label") || b.textContent;
    b.setAttribute("data-ssa-share-label", old);
    b.textContent = msg;
    setTimeout(function () {
      b.textContent = old || "Share";
    }, 1600);
  }

  function copySheetUrl() {
    var u = sheetUrl() || location.href;
    function ok() {
      flashShareBtn("URL copied");
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(u).then(ok).catch(function () {
        prompt("Copy this URL:", u);
      });
    }
    prompt("Copy this URL:", u);
    return Promise.resolve();
  }

  function shareEventUrl() {
    var t = pdfTitle();
    var u = sheetUrl() || location.href;
    var payload = { title: t, text: t, url: u };
    if (_pdfFile && navigator.canShare) {
      try {
        if (navigator.canShare({ files: [_pdfFile], title: t, url: u })) {
          payload.files = [_pdfFile];
        }
      } catch (e) {}
    }
    if (typeof navigator.share === "function") {
      navigator.share(payload).catch(function (err) {
        if (err && err.name === "AbortError") return;
        copySheetUrl();
      });
      return;
    }
    copySheetUrl();
  }

  function openChooser() {
    var el = document.getElementById("ssaPrintChooser");
    if (!el) {
      printPdf();
      return;
    }
    if (!wirePdfLinks()) {
      printPdf();
      return;
    }
    if (el.parentNode !== document.body) {
      document.body.appendChild(el);
    }
    el.classList.add("is-open");
    showPdfPreview();
    warmPdf().catch(function () {});
  }

  function closeChooser() {
    var el = document.getElementById("ssaPrintChooser");
    if (el) el.classList.remove("is-open");
  }

  window.ssaRegattaPrint = openChooser;
  window.ssaRegattaPrintPdf = printPdf;
  window.ssaRegattaShare = shareEventUrl;

  document.addEventListener("click", function (ev) {
    var t = ev.target;
    if (t && t.id === "ssaPrintChooser") {
      closeChooser();
      return;
    }
    var shareHit = t && t.closest ? t.closest("#regattaShareBtn") : null;
    if (shareHit) {
      ev.preventDefault();
      shareEventUrl();
      return;
    }
    var printHit = t && t.closest ? t.closest("#regattaPrintBtn") : null;
    if (printHit) {
      ev.preventDefault();
      openChooser();
      return;
    }
    var hit = t && t.closest ? t.closest("[data-ssa-print]") : null;
    if (!hit) return;
    var act = hit.getAttribute("data-ssa-print");
    if (act === "whatsapp") {
      ev.preventDefault();
      whatsappPdf();
      return;
    }
    if (act === "email") {
      ev.preventDefault();
      emailPdf();
      return;
    }
    if (act === "download") {
      return;
    }
    if (act === "printer") {
      return;
    }
    if (act === "cancel") {
      ev.preventDefault();
      closeChooser();
    }
  });

  wirePdfLinks();
})();
