/**
 * Weekend Roundup cards on the homepage.
 * Default = most recent issue. Swipe left for older weekends, swipe right
 * to come back forward. Does not touch the master header.
 */
(function () {
  "use strict";

  var section = document.getElementById("landing-top-card");
  if (!section) return;

  var track = document.getElementById("landing-roundup-track");
  var viewport = document.getElementById("landing-roundup-viewport");
  var dotsHost = document.getElementById("landing-roundup-dots");
  var legacyFace = document.getElementById("landing-roundup-face");

  if (!track || !viewport) {
    if (!legacyFace) return;
    viewport = document.createElement("div");
    viewport.className = "landing-roundup-viewport";
    viewport.id = "landing-roundup-viewport";
    track = document.createElement("div");
    track.className = "landing-roundup-track";
    track.id = "landing-roundup-track";
    viewport.appendChild(track);
    legacyFace.replaceWith(viewport);
    if (!dotsHost) {
      dotsHost = document.createElement("div");
      dotsHost.className = "landing-roundup-dots";
      dotsHost.id = "landing-roundup-dots";
      viewport.after(dotsHost);
    }
  }

  function absUrl(pageUrl, value) {
    try {
      return new URL(value, pageUrl).href;
    } catch (e) {
      return value;
    }
  }

  function heroFrom(html, pageUrl) {
    if (html.indexOf(">The Weekend Roundup</h1>") < 0) return null;
    var leadMatch = html.match(/<article[^>]*edition-lead[\s\S]*?<\/article>/);
    var leadHtml = leadMatch ? leadMatch[0] : "";
    var searchIn = leadHtml && /<div class=['"]photo-set/.test(leadHtml) ? leadHtml : html;
    var mark = searchIn.search(/<div class=['"]photo-set/);
    var slice = mark >= 0 ? searchIn.slice(mark) : searchIn;
    var fig = slice.match(/<figure[\s\S]*?<\/figure>/);
    if (!fig) return null;
    var block = fig[0];
    var cap = (block.match(/<figcaption>([\s\S]*?)<\/figcaption>/) || ["", ""])[1];
    cap = cap.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
    if (!cap) return null;
    block = block.replace(/(href|src)=(['"])(?!https?:|\/\/)([^'"]+)\2/g, function (_, attr, q, url) {
      return attr + "=" + q + absUrl(pageUrl, url) + q;
    });
    block = block.replace(/<figcaption[\s\S]*?<\/figcaption>/, "");
    var title = ((leadHtml.match(/<h1[^>]*>([\s\S]*?)<\/h1>/) || ["", ""])[1] || "")
      .replace(/<[^>]+>/g, "")
      .replace(/\s+/g, " ")
      .trim();
    var date = ((leadHtml.match(/<p class=["']deck["']>([\s\S]*?)<\/p>/) || ["", ""])[1] || "")
      .replace(/<[^>]+>/g, "")
      .replace(/\s+/g, " ")
      .trim();
    var copy = (leadHtml.match(/<div class=["']copy["']>([\s\S]*?)<\/div>/) || ["", ""])[1] || "";
    var paragraphs = [];
    var pm;
    var pre = /<p[^>]*>([\s\S]*?)<\/p>/g;
    while ((pm = pre.exec(copy))) {
      var text = pm[1].replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
      if (text) paragraphs.push(text);
    }
    return {
      html: block,
      caption: cap,
      pageUrl: pageUrl,
      title: title || "The Weekend Roundup",
      date: date,
      paragraphs: paragraphs,
    };
  }

  function fitTitle(el) {
    var box = el && el.parentElement;
    if (!box) return;
    var avail = box.clientWidth - 20;
    el.style.display = "block";
    el.style.width = "max-content";
    el.style.maxWidth = "none";
    var lo = 12;
    var hi = Math.max(lo, avail);
    while (lo < hi) {
      var mid = Math.ceil((lo + hi) / 2);
      el.style.fontSize = mid + "px";
      if (el.scrollWidth <= avail) lo = mid;
      else hi = mid - 1;
    }
    el.style.fontSize = lo + "px";
  }

  function fillCard(root, hero) {
    var paras = (hero.paragraphs || []).map(function () { return "<p></p>"; }).join("");
    root.innerHTML =
      '<a class="landing-roundup-link" href="' +
      hero.pageUrl +
      '">' +
      '<div class="landing-roundup-hero">' +
      hero.html +
      "</div>" +
      '<p class="landing-top-card-caption"></p>' +
      '<p class="landing-roundup-title"></p>' +
      '<p class="landing-roundup-date"></p>' +
      '<div class="landing-roundup-copy">' +
      paras +
      "</div>" +
      '<p class="landing-roundup-more"><span>Read the full roundup \u2192</span></p></a>';
    root.querySelector(".landing-top-card-caption").textContent = hero.caption;
    root.querySelector(".landing-roundup-title").textContent = hero.title;
    root.querySelector(".landing-roundup-date").textContent = hero.date;
    var nodes = root.querySelectorAll(".landing-roundup-copy p");
    (hero.paragraphs || []).forEach(function (text, i) {
      if (nodes[i]) nodes[i].textContent = text;
    });
    fitTitle(root.querySelector(".landing-roundup-title"));
  }

  function renderDots(count, index) {
    if (!dotsHost) return;
    if (count < 2) {
      dotsHost.hidden = true;
      dotsHost.innerHTML = "";
      return;
    }
    dotsHost.hidden = false;
    dotsHost.innerHTML = "";
    for (var i = 0; i < count; i++) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "landing-roundup-dot" + (i === index ? " is-active" : "");
      btn.setAttribute("aria-label", "Weekend roundup " + (i + 1) + " of " + count);
      btn.setAttribute("aria-current", i === index ? "true" : "false");
      btn.setAttribute("data-roundup-index", String(i));
      dotsHost.appendChild(btn);
    }
  }

  function bindCarousel(count) {
    var index = 0;
    var startX = 0;
    var startY = 0;
    var dx = 0;
    var dragging = false;
    var locked = null;
    var ignoreClick = false;
    var width = function () {
      return viewport.clientWidth || 1;
    };

    function setIndex(next, animate) {
      index = Math.max(0, Math.min(count - 1, next));
      track.style.transition = animate === false ? "none" : "transform .28s ease";
      track.style.transform = "translate3d(" + -index * 100 + "%,0,0)";
      section.setAttribute("data-roundup-index", String(index));
      renderDots(count, index);
    }

    function finishDrag() {
      if (!dragging) return;
      dragging = false;
      var w = width();
      if (locked === "x" && Math.abs(dx) > Math.min(56, w * 0.18)) {
        ignoreClick = true;
        setIndex(index + (dx < 0 ? 1 : -1), true);
      } else {
        if (locked === "x" && Math.abs(dx) > 8) ignoreClick = true;
        setIndex(index, true);
      }
      locked = null;
      dx = 0;
    }

    viewport.addEventListener(
      "touchstart",
      function (e) {
        if (!e.touches || !e.touches[0] || count < 2) return;
        dragging = true;
        locked = null;
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        dx = 0;
        track.style.transition = "none";
      },
      { passive: true }
    );

    viewport.addEventListener(
      "touchmove",
      function (e) {
        if (!dragging || !e.touches || !e.touches[0]) return;
        var x = e.touches[0].clientX;
        var y = e.touches[0].clientY;
        var adx = Math.abs(x - startX);
        var ady = Math.abs(y - startY);
        if (locked == null && (adx > 8 || ady > 8)) locked = adx > ady ? "x" : "y";
        if (locked !== "x") return;
        dx = x - startX;
        var extra = dx;
        if ((index === 0 && dx > 0) || (index === count - 1 && dx < 0)) extra = dx * 0.22;
        track.style.transform = "translate3d(" + (-index * width() + extra) + "px,0,0)";
        if (e.cancelable) e.preventDefault();
      },
      { passive: false }
    );

    viewport.addEventListener("touchend", finishDrag, { passive: true });
    viewport.addEventListener("touchcancel", finishDrag, { passive: true });

    viewport.addEventListener("pointerdown", function (e) {
      if (e.pointerType === "touch" || count < 2) return;
      if (e.pointerType === "mouse" && e.button !== 0) return;
      dragging = true;
      locked = "x";
      startX = e.clientX;
      startY = e.clientY;
      dx = 0;
      track.style.transition = "none";
      try {
        viewport.setPointerCapture(e.pointerId);
      } catch (err) {}
    });

    viewport.addEventListener("pointermove", function (e) {
      if (!dragging || e.pointerType === "touch") return;
      dx = e.clientX - startX;
      if (Math.abs(dx) < 2) return;
      var extra = dx;
      if ((index === 0 && dx > 0) || (index === count - 1 && dx < 0)) extra = dx * 0.22;
      track.style.transform = "translate3d(" + (-index * width() + extra) + "px,0,0)";
    });

    viewport.addEventListener("pointerup", function (e) {
      if (e.pointerType === "touch") return;
      finishDrag();
    });
    viewport.addEventListener("pointercancel", function (e) {
      if (e.pointerType === "touch") return;
      finishDrag();
    });

    viewport.addEventListener(
      "click",
      function (e) {
        if (!ignoreClick) return;
        e.preventDefault();
        e.stopPropagation();
        ignoreClick = false;
      },
      true
    );

    if (dotsHost) {
      dotsHost.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-roundup-index]");
        if (!btn) return;
        setIndex(parseInt(btn.getAttribute("data-roundup-index"), 10) || 0, true);
      });
    }

    section.tabIndex = 0;
    section.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        setIndex(index - 1, true);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setIndex(index + 1, true);
      }
    });

    window.addEventListener("resize", function () {
      Array.prototype.forEach.call(track.querySelectorAll(".landing-roundup-title"), fitTitle);
      setIndex(index, false);
    });

    setIndex(0, false);
    return { setIndex: setIndex };
  }

  function paintAll(heroes) {
    track.innerHTML = "";
    heroes.forEach(function (hero, i) {
      var slide = document.createElement("article");
      slide.className = "landing-top-card-face landing-roundup-slide";
      if (i === 0) slide.id = "landing-roundup-face";
      fillCard(slide, hero);
      track.appendChild(slide);
    });
    viewport.setAttribute("aria-live", "polite");
    bindCarousel(heroes.length);
  }

  fetch("/sailing-roundup/feed.json", { cache: "no-store" })
    .then(function (r) {
      return r.json();
    })
    .then(function (items) {
      var urls = [];
      (items || []).forEach(function (item) {
        if (item && item.url) urls.push(item.url);
      });
      if (!urls.length) return;
      return Promise.all(
        urls.map(function (url) {
          return fetch(url, { cache: "no-store" })
            .then(function (r) {
              return r.text();
            })
            .then(function (html) {
              return heroFrom(html, url);
            })
            .catch(function () {
              return null;
            });
        })
      ).then(function (found) {
        var heroes = (found || []).filter(Boolean);
        if (heroes.length) paintAll(heroes);
      });
    })
    .catch(function () {});
})();
