/**
 * Weekend Roundup cards on the homepage.
 * Default = most recent issue. Swipe left for older weekends, swipe right
 * to come back forward. A tap opens the full issue URL.
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

  function fullIssueUrl(url) {
    try {
      return new URL(url, "https://sailingsa.co.za/sailing-roundup/").href;
    } catch (e) {
      return url;
    }
  }

  function heroFrom(html, pageUrl, item) {
    var leadMatch = html.match(/<article[^>]*edition-lead[\s\S]*?<\/article>/);
    var leadHtml = leadMatch ? leadMatch[0] : "";
    var searchIn = leadHtml && /<div class=['"]photo-set/.test(leadHtml) ? leadHtml : html;
    var mark = searchIn.search(/<div class=['"]photo-set/);
    var slice = mark >= 0 ? searchIn.slice(mark) : searchIn;
    var fig = slice.match(/<figure[\s\S]*?<\/figure>/);
    var block = fig ? fig[0] : "";
    var cap = "";
    if (block) {
      cap = (block.match(/<figcaption>([\s\S]*?)<\/figcaption>/) || ["", ""])[1];
      cap = cap.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
      block = block.replace(/(href|src)=(['"])(?!https?:|\/\/)([^'"]+)\2/g, function (_, attr, q, url) {
        return attr + "=" + q + absUrl(pageUrl, url) + q;
      });
      block = block.replace(/<figcaption[\s\S]*?<\/figcaption>/, "");
    }
    if (!block && item && item.image) {
      var img = item.image.indexOf("http") === 0 ? item.image : absUrl("https://sailingsa.co.za/sailing-roundup/", item.image);
      block = '<img src="' + img + '" alt="">';
    }
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
      pageUrl: fullIssueUrl(pageUrl),
      title: title || "The Weekend Roundup",
      date: date || (item && item.published_at) || "",
      paragraphs: paragraphs,
    };
  }

  function fillCard(root, hero) {
    var href = htmlEscape(hero.pageUrl);
    var paras = (hero.paragraphs || []).map(function () { return "<p></p>"; }).join("");
    root.innerHTML =
      '<a class="landing-roundup-link" href="' +
      href +
      '">' +
      (hero.html ? '<div class="landing-roundup-hero">' + hero.html + "</div>" : "") +
      '<p class="landing-top-card-caption"></p>' +
      '<p class="landing-roundup-title"></p>' +
      '<p class="landing-roundup-date"></p>' +
      '<div class="landing-roundup-copy">' +
      paras +
      "</div>" +
      '<p class="landing-roundup-more"><span>Read the full roundup \u2192</span></p></a>';
    var cap = root.querySelector(".landing-top-card-caption");
    if (cap) cap.textContent = hero.caption || "";
    root.querySelector(".landing-roundup-title").textContent = hero.title;
    root.querySelector(".landing-roundup-date").textContent = hero.date;
    var nodes = root.querySelectorAll(".landing-roundup-copy p");
    (hero.paragraphs || []).forEach(function (text, i) {
      if (nodes[i]) nodes[i].textContent = text;
    });
  }

  function htmlEscape(value) {
    return String(value || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
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
      btn.setAttribute("data-roundup-index", String(i));
      dotsHost.appendChild(btn);
    }
  }

  function sizeSlides() {
    var w = viewport.clientWidth || section.clientWidth;
    if (!w) return;
    viewport.style.setProperty("--roundup-card-width", w + "px");
    Array.prototype.forEach.call(track.children, function (slide) {
      slide.style.width = w + "px";
      slide.style.minWidth = w + "px";
      slide.style.maxWidth = w + "px";
      slide.style.flex = "0 0 " + w + "px";
    });
  }

  function bindCarousel(count) {
    var index = 0;
    var startX = 0;
    var startY = 0;
    var dx = 0;
    var dragging = false;
    var axis = null;
    var ignoreClick = false;

    function setIndex(next, animate) {
      index = Math.max(0, Math.min(count - 1, next));
      sizeSlides();
      var w = viewport.clientWidth || 1;
      track.style.transition = animate === false ? "none" : "transform .28s ease";
      track.style.transform = "translate3d(" + -index * w + "px,0,0)";
      section.setAttribute("data-roundup-index", String(index));
      renderDots(count, index);
    }

    function finish() {
      if (!dragging) return;
      dragging = false;
      var w = viewport.clientWidth || 1;
      if (axis === "x" && Math.abs(dx) > Math.min(48, w * 0.16)) {
        ignoreClick = true;
        setIndex(index + (dx < 0 ? 1 : -1), true);
      } else {
        setIndex(index, true);
      }
      axis = null;
      dx = 0;
    }

    viewport.addEventListener(
      "touchstart",
      function (e) {
        if (!e.touches || !e.touches[0] || count < 2) return;
        dragging = true;
        axis = null;
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
        if (axis == null && (adx > 10 || ady > 10)) axis = adx > ady ? "x" : "y";
        if (axis !== "x") return;
        dx = x - startX;
        var extra = dx;
        if ((index === 0 && dx > 0) || (index === count - 1 && dx < 0)) extra = dx * 0.2;
        track.style.transform = "translate3d(" + (-index * (viewport.clientWidth || 1) + extra) + "px,0,0)";
        if (e.cancelable) e.preventDefault();
      },
      { passive: false }
    );
    viewport.addEventListener("touchend", finish, { passive: true });
    viewport.addEventListener("touchcancel", finish, { passive: true });

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
        e.preventDefault();
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
      setIndex(index, false);
    });

    setIndex(0, false);
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
    sizeSlides();
    bindCarousel(heroes.length);
  }

  fetch("/sailing-roundup/feed.json", { cache: "no-store" })
    .then(function (r) {
      return r.json();
    })
    .then(function (items) {
      var rows = (items || []).filter(function (item) {
        return item && item.url;
      });
      if (!rows.length) return;
      return Promise.all(
        rows.map(function (item) {
          var url = fullIssueUrl(item.url);
          return fetch(url, { cache: "no-store" })
            .then(function (r) {
              return r.text();
            })
            .then(function (html) {
              return heroFrom(html, url, item);
            })
            .catch(function () {
              return heroFrom("", url, item);
            });
        })
      ).then(function (found) {
        var heroes = (found || []).filter(function (hero) {
          return hero && hero.pageUrl;
        });
        if (heroes.length) paintAll(heroes);
      });
    })
    .catch(function () {});
})();
