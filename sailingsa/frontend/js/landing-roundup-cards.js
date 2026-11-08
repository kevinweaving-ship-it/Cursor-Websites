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

  function ensureRoundupControl(id, className, label, glyph) {
    var btn = document.getElementById(id);
    if (!btn) {
      btn = document.createElement("button");
      btn.type = "button";
      btn.id = id;
      btn.className = className;
      btn.setAttribute("aria-label", label);
      btn.textContent = glyph;
      section.appendChild(btn);
    }
    return btn;
  }
  var prevBtn = ensureRoundupControl(
    "landing-roundup-prev",
    "landing-roundup-arrow is-prev",
    "Previous Weekly Roundup",
    "\u2039"
  );
  var nextBtn = ensureRoundupControl(
    "landing-roundup-next",
    "landing-roundup-arrow is-next",
    "Next Weekly Roundup",
    "\u203a"
  );

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


  // The active edition owns the height; upcoming cards consume that budget.
  var layoutFrame = 0;
  function scheduleLayout() {
    if (layoutFrame) return;
    layoutFrame = window.requestAnimationFrame(function () {
      layoutFrame = 0;
      var index = parseInt(section.getAttribute("data-roundup-index"), 10) || 0;
      var active = track.children[index];
      if (!active) return;
      var height = Math.ceil(active.getBoundingClientRect().height);
      if (height > 0 && viewport.style.height !== height + "px") viewport.style.height = height + "px";
      var col = document.getElementById("temp-landing-hero-image");
      if (!col) return;
      var inner = col.querySelector(":scope > .landing-events-fit");
      if (!inner) {
        inner = document.createElement("div");
        inner.className = "landing-events-fit";
        while (col.firstChild) inner.appendChild(col.firstChild);
        col.appendChild(inner);
      }
      var cards = Array.prototype.slice.call(col.querySelectorAll(".landing-event-card"));
      cards.forEach(function (card) { card.hidden = false; });
      var sideBySide = window.matchMedia("(min-width:1024px), (orientation:landscape)").matches;
      if (inner) {
        inner.style.removeProperty("transform");
        inner.style.removeProperty("width");
      }
      var used = 0;
      var count = 0;
      var budgetExhausted = false;
      var parent = inner || col;
      var gap = parseFloat(window.getComputedStyle(parent).rowGap) || 12;
      cards.forEach(function (card, i) {
        var cardHeight = card.getBoundingClientRect().height;
        var next = used + (count ? gap : 0) + cardHeight;
        var fits = i < 4;
        if (fits) { used = next; count++; }
        else { card.hidden = true; if (sideBySide) budgetExhausted = true; }
      });
      col.dataset.visibleCount = String(count);
      col.dataset.heightBudget = String(height);
      placeArrows();
    });
  }

  function placeArrows() {
    if (!prevBtn || !nextBtn || (prevBtn.hidden && nextBtn.hidden)) return;
    var index = parseInt(section.getAttribute("data-roundup-index"), 10) || 0;
    var slide = track.children[index];
    if (!slide) return;
    var sec = section.getBoundingClientRect();
    var hero = slide.querySelector(".landing-roundup-hero");
    var box = hero && hero.getBoundingClientRect();
    var mid;
    if (box && box.height) {
      mid = box.top - sec.top + box.height / 2;
    } else {
      // Some editions have no photo: place navigation in the gap between
      // the headline and the read-more row, not below the clipped card.
      var title = slide.querySelector(".landing-roundup-title");
      var more = slide.querySelector(".landing-roundup-more");
      var titleBox = title && title.getBoundingClientRect();
      var moreBox = more && more.getBoundingClientRect();
      if (titleBox && moreBox && moreBox.top - titleBox.bottom > 30) {
        mid = (titleBox.bottom + moreBox.top) / 2 - sec.top;
      } else {
        mid = moreBox ? moreBox.top - sec.top - 18 : sec.height / 2;
      }
    }
    if (!sec.height || !Number.isFinite(mid)) return;
    mid = Math.max(18, Math.min(sec.height - 18, mid));
    prevBtn.style.setProperty("top", mid + "px", "important");
    nextBtn.style.setProperty("top", mid + "px", "important");
    prevBtn.style.setProperty("margin-top", "-13px", "important");
    nextBtn.style.setProperty("margin-top", "-13px", "important");
  }

  var layoutStyle = document.createElement("style");
  layoutStyle.id = "weekly-roundup-responsive-layout";
  layoutStyle.textContent = [
    "#landing-top-card{align-self:start!important;min-height:0!important;height:auto!important;margin:0!important;padding:0!important}",
    "#landing-top-card .landing-roundup-track{align-items:flex-start!important}",
    "#landing-top-card .landing-roundup-slide{height:auto!important;min-height:0!important;padding:12px!important;align-self:flex-start!important}",
    "#landing-top-card .landing-roundup-viewport{min-height:0!important;transition:height .15s ease}",
    "#landing-top-card .landing-roundup-series{margin:0 0 6px!important;padding:0!important;font:700 11px/1.25 system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#786142}",
    "#landing-top-card .landing-roundup-title{margin:0!important;padding:0!important;font:700 24px/1.15 Georgia,serif!important;letter-spacing:normal!important;white-space:normal!important;color:#001f3f}",
    "#landing-top-card .landing-roundup-date{margin:8px 0 0!important;padding:0!important;font:600 13px/1.35 system-ui,sans-serif!important}",
    "#landing-top-card .landing-roundup-hero{margin:12px 0 0!important;padding:0!important;width:100%!important;height:auto!important;max-height:none!important;aspect-ratio:auto!important;background:transparent!important}",
    "#landing-top-card .landing-roundup-hero img{display:block!important;width:100%!important;height:auto!important;max-height:none!important;object-fit:contain!important}",
    "#landing-top-card .landing-top-card-caption{margin:6px 0 0!important;padding:0!important;font:10px/1.4 system-ui,sans-serif!important}",
    "#landing-top-card .landing-top-card-caption:empty{display:none!important}",
    "#landing-top-card .landing-roundup-more{margin:12px 0 0!important;padding:0!important;line-height:1.4}",
    "#landing-top-card .landing-roundup-more span{display:inline-block;margin:0!important;padding:0 0 4px!important;font-size:11px!important}",
    "#landing-top-card .landing-roundup-dots{margin:8px 0 0!important;padding:0!important}",
    "#temp-landing-hero-image .landing-events-fit{transform:none!important;width:100%!important;display:flex!important;flex-direction:column!important;gap:12px!important}",
    "#temp-landing-hero-image .landing-event-card{margin:0!important;flex-shrink:0!important}",
    "#temp-landing-hero-image .landing-event-card[hidden]{display:none!important}",
    "@media(min-width:1024px),(orientation:landscape){.landing-top-row{display:grid!important;grid-template-columns:minmax(0,1fr) minmax(0,1fr)!important;align-items:start!important}.landing-top-row>#temp-landing-hero-image{position:static!important;grid-column:2!important;grid-row:1!important;width:100%!important;max-width:100%!important;height:auto!important;min-height:0!important;overflow:visible!important;margin:0!important}}",
    "@media(max-width:1023px) and (orientation:portrait){.landing-top-row{display:block!important}.landing-top-row>#temp-landing-hero-image{position:static!important;width:100%!important;max-width:100%!important;height:auto!important;margin:12px 0 0!important;overflow:visible!important}}"
  ].join("\n");
  function loadRoundupEditorialStyles() {
    if (document.getElementById("roundup-editorial-font-css")) return;
    var link = document.createElement("link");
    link.id = "roundup-editorial-font-css";
    link.rel = "stylesheet";
    link.href = "/sailing-roundup/roundup-editorial-font.css?v=20261108";
    document.head.appendChild(link);
  }
  document.head.appendChild(layoutStyle);
  var pagerStyle = document.createElement("style");
  pagerStyle.id = "landing-roundup-pager";
  pagerStyle.textContent = [
    "#landing-top-card .landing-roundup-slide{padding-bottom:34px!important}",
    "#landing-top-card .landing-roundup-dots{position:absolute!important;left:0!important;right:0!important;bottom:12px!important;z-index:6!important;display:flex!important;justify-content:center!important;align-items:center!important;gap:8px!important;margin:0!important;padding:0!important;width:auto!important;height:auto!important}",
    "#landing-top-card .landing-roundup-dot{flex:0 0 8px!important;width:8px!important;height:8px!important;min-width:8px!important;max-width:8px!important;border-radius:50%!important;border:0!important;padding:0!important;background:rgba(244,238,228,.45)!important;box-shadow:none!important}",
    "#landing-top-card .landing-roundup-dot.is-active{background:#f4eee4!important}",
    "#landing-top-card .landing-roundup-arrow{position:absolute!important;z-index:7!important;width:26px!important;height:26px!important;margin:0!important;padding:0 0 2px!important;border-radius:50%!important;border:1px solid rgba(229,195,148,.9)!important;background:rgba(0,31,63,.62)!important;color:#e5c394!important;font:600 20px/24px Georgia,serif!important;line-height:24px!important;text-align:center!important;cursor:pointer;box-shadow:none!important}",
    "#landing-top-card .landing-roundup-arrow.is-prev{left:8px!important}",
    "#landing-top-card .landing-roundup-arrow.is-next{right:8px!important}",
    "#landing-top-card .landing-roundup-arrow:disabled{opacity:.32!important;cursor:default!important}",
    "#landing-top-card .landing-roundup-edition{margin-left:8px!important;font:400 10px/1 Georgia,serif!important;letter-spacing:.02em!important;text-transform:none!important;color:#f4eee4!important;white-space:nowrap!important}",
    "#landing-top-card .landing-roundup-slide{position:relative!important}",
    "#landing-top-card .landing-roundup-reads{position:absolute!important;right:8px!important;bottom:40px!important;z-index:8!important;font:600 11px/1 Arial,sans-serif!important;letter-spacing:0!important;text-transform:none!important;color:#e5c394!important;background:rgba(0,31,63,.78)!important;border:1px solid rgba(229,195,148,.9)!important;border-radius:9px!important;padding:3px 6px!important;pointer-events:none!important}"
  ].join("\n");
  document.head.appendChild(pagerStyle);
  window.addEventListener("resize", scheduleLayout);
  window.addEventListener("orientationchange", scheduleLayout);
  window.addEventListener("load", scheduleLayout);
  track.addEventListener("load", scheduleLayout, true);
  track.addEventListener("error", scheduleLayout, true);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(scheduleLayout);
  if (window.ResizeObserver) {
    var layoutObserver = new ResizeObserver(scheduleLayout);
    layoutObserver.observe(section);
    layoutObserver.observe(track);
  }
  var upcomingCol = document.getElementById("temp-landing-hero-image");
  if (upcomingCol && window.MutationObserver) {
    new MutationObserver(scheduleLayout).observe(upcomingCol, {childList:true,subtree:true});
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

  function issuePath(url) {
    try {
      var abs = new URL(fullIssueUrl(url));
      return abs.pathname + abs.search;
    } catch (e) {
      return url;
    }
  }

  function htmlEscape(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  function decodeEntities(value) {
    var box = document.createElement("textarea");
    box.innerHTML = String(value || "");
    return box.value.replace(/\s+/g, " ").trim();
  }

  function bannedHero(src) {
    var low = String(src || "").toLowerCase();
    if (!low) return true;
    // Club flags, logos, and Facebook profile pictures are not event photos.
    if (/burgee|pennant|ensign|club[-_ ]?logo|event[-_ ]?logo|class[-_ ]?logo/.test(low)) return true;
    if (/artwork\/(event|club|class)/.test(low)) return true;
    if (/\/t39\.30808-1\//.test(low)) return true;
    if (/\/picture\?/.test(low)) return true;
    if (/profile[_-]?pic/.test(low)) return true;
    return false;
  }

  function firstFigure(html) {
    var leadMatch = html.match(/<article[^>]*edition-lead[\s\S]*?<\/article>/);
    var leadHtml = leadMatch ? leadMatch[0] : "";
    // Only the week lead photo. Never steal a later event's video still.
    return { leadHtml: leadHtml, figures: leadHtml.match(/<figure[\s\S]*?<\/figure>/g) || [] };
  }

  function figurePhoto(figureHtml, pageUrl) {
    if (!figureHtml) return null;
    var img = figureHtml.match(/<img[^>]+src=(['"])([^'"]+)\1/i);
    if (!img) return null;
    var src = absUrl(pageUrl, img[2]);
    if (bannedHero(src)) return null;
    var cap = (figureHtml.match(/<figcaption>([\s\S]*?)<\/figcaption>/) || ["", ""])[1];
    cap = cap.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
    return { src: src, caption: cap };
  }

  function heroImgTag(html, pageUrl, item) {
    var found = firstFigure(html || "");
    if (item && Object.prototype.hasOwnProperty.call(item, "image") && !item.image)
      return { html: "", caption: "", leadHtml: found.leadHtml };
    var photo = null;
    if (item && item.image) {
      var fallback = item.image.indexOf("http") === 0 ? item.image : absUrl("https://sailingsa.co.za/sailing-roundup/", item.image);
      if (!bannedHero(fallback)) photo = { src: fallback, caption: item.image_caption || "" };
    }
    var i;
    for (i = 0; !photo && i < found.figures.length; i++) {
      photo = figurePhoto(found.figures[i], pageUrl);
    }
    if (!photo) return { html: "", caption: "", leadHtml: found.leadHtml };
    return {
      html: '<img src="' + htmlEscape(photo.src) + '" alt=""' + ((item && /^(?:100|[0-9]{1,2})% (?:100|[0-9]{1,2})%$/.test(item.image_focus || "")) ? ' style="--roundup-hero-position:' + item.image_focus + '"' : "") + '>',
      caption: photo.caption,
      leadHtml: found.leadHtml,
    };
  }

  function heroFrom(html, pageUrl, item) {
    var found = heroImgTag(html || "", pageUrl, item);
    var leadHtml = found.leadHtml;
    var cap = found.caption || "";
    var title = decodeEntities(((leadHtml.match(/<h1[^>]*>([\s\S]*?)<\/h1>/) || leadHtml.match(/<h2[^>]*>([\s\S]*?)<\/h2>/) || ["", ""])[1] || "").replace(/<[^>]+>/g, ""));
    var date = decodeEntities(((leadHtml.match(/<p class=["']deck["']>([\s\S]*?)<\/p>/) || ["", ""])[1] || "").replace(/<[^>]+>/g, ""));
    var copy = (leadHtml.match(/<div class=["']copy["']>([\s\S]*?)<\/div>/) || ["", ""])[1] || "";
    var paragraphs = [];
    var pm;
    var pre = /<p[^>]*>([\s\S]*?)<\/p>/g;
    while ((pm = pre.exec(copy))) {
      var text = decodeEntities(pm[1].replace(/<[^>]+>/g, ""));
      if (text) paragraphs.push(text);
    }
    return {
      html: found.html,
      caption: cap,
      pageUrl: fullIssueUrl(pageUrl),
      title: (item && item.headline) || title || (item && item.title) || "Weekly Roundup",
      date: date || (item && item.published_at) || "",
      paragraphs: paragraphs.length ? paragraphs : ((item && item.excerpt) ? [item.excerpt] : []),
    };
  }

  function loadDeferredHero(slide) {
    if (!slide) return;
    var img = slide.querySelector("img[data-hero-src]");
    if (!img || img.getAttribute("src")) return;
    img.setAttribute("src", img.getAttribute("data-hero-src"));
  }

  function fillCard(root, hero, opts) {
    var eager = !!(opts && opts.eager);
    root.setAttribute("data-issue-url", hero.pageUrl);
    root.innerHTML =
      '<p class="landing-roundup-series">Weekly Roundup' +
      (opts && opts.edition ? '<span class="landing-roundup-edition">Edition ' + opts.edition + '</span>' : '') +
      '</p>' +
      '<p class="landing-roundup-title"></p>' +
      '<p class="landing-roundup-date"></p>' +
      (hero.html ? '<div class="landing-roundup-hero">' + hero.html + '</div>' : '') +
      (hero.caption ? '<p class="landing-top-card-caption"></p>' : '') +
      '<p class="landing-roundup-more"><span>Read the full roundup \u2192</span></p>';
    root.querySelector(".landing-roundup-title").textContent = hero.title;
    root.querySelector(".landing-roundup-date").textContent = hero.date;
    var captionNode = root.querySelector(".landing-top-card-caption");
    if (captionNode) captionNode.textContent = hero.caption;
    var img = root.querySelector("img");
    if (img) {
      img.alt = hero.caption || hero.title;
      if (eager) {
        img.setAttribute("fetchpriority", "high");
        img.setAttribute("decoding", "async");
      } else if (img.getAttribute("src")) {
        img.setAttribute("data-hero-src", img.getAttribute("src"));
        img.removeAttribute("src");
      }
    }
  }

  function renderDots(count, index) {
    var multi = count > 1;
    if (prevBtn) {
      prevBtn.hidden = !multi || index <= 0;
      prevBtn.disabled = index <= 0;
    }
    if (nextBtn) {
      nextBtn.hidden = !multi || index >= count - 1;
      nextBtn.disabled = index >= count - 1;
    }
    if (!dotsHost) return;
    if (!multi) {
      dotsHost.hidden = true;
      dotsHost.innerHTML = "";
      return;
    }
    dotsHost.hidden = false;
    dotsHost.innerHTML = "";
    var windowSize = Math.min(8, count);
    var start = Math.max(0, Math.min(index - 3, count - windowSize));
    for (var i = start; i < start + windowSize; i++) {
      var btn = document.createElement("button");
      var slide = track.children[i];
      var when = "";
      if (slide) {
        var dateNode = slide.querySelector(".landing-roundup-date");
        when = dateNode ? dateNode.textContent.trim() : "";
      }
      btn.type = "button";
      btn.className = "landing-roundup-dot" + (i === index ? " is-active" : "");
      btn.setAttribute(
        "aria-label",
        (when ? when + ", " : "") + "Weekly Roundup " + (i + 1) + " of " + count
      );
      btn.setAttribute("aria-current", i === index ? "true" : "false");
      btn.setAttribute("data-roundup-index", String(i));
      dotsHost.appendChild(btn);
    }
  }

  function slideWidth() {
    var box = viewport.getBoundingClientRect();
    return Math.round(box.width || viewport.clientWidth || section.clientWidth || 0);
  }

  function sizeSlides() {
    var w = slideWidth();
    if (!w) return;
    viewport.style.setProperty("--roundup-card-width", w + "px");
    track.style.width = w * track.children.length + "px";
    Array.prototype.forEach.call(track.children, function (slide) {
      slide.style.width = w + "px";
      slide.style.minWidth = w + "px";
      slide.style.maxWidth = w + "px";
      slide.style.flex = "0 0 " + w + "px";
      slide.style.boxSizing = "border-box";
    });
  }

  function showOnly(index, also) {
    Array.prototype.forEach.call(track.children, function (slide, i) {
      var on = i === index || i === also;
      slide.style.visibility = on ? "visible" : "hidden";
      slide.inert = !on;
      slide.setAttribute("aria-hidden", on ? "false" : "true");
      if (on) loadDeferredHero(slide);
    });
  }

  function openIssue(url) {
    if (!url) return;
    window.location.assign(url);
  }

  function bindCarousel(count) {
    var index = 0;
    var startX = 0;
    var startY = 0;
    var dx = 0;
    var dragging = false;
    var axis = null;
    var ignoreClick = false;

    function currentUrl() {
      var slide = track.children[index];
      return slide ? slide.getAttribute("data-issue-url") : "";
    }

    function setIndex(next, animate) {
      var dest = Math.max(0, Math.min(count - 1, next));
      showOnly(index, dest);
      index = dest;
      sizeSlides();
      var w = slideWidth() || 1;
      track.style.transition = animate === false ? "none" : "transform .28s ease";
      track.style.transform = "translate3d(" + -index * w + "px,0,0)";
      section.setAttribute("data-roundup-index", String(index));
      hydrateDeck(track.children[index]);
      renderDots(count, index);
      scheduleLayout();
      if (animate === false) {
        showOnly(index);
        return;
      }
      window.setTimeout(function () {
        showOnly(index);
      }, 320);
    }

    function finish(openIfTap) {
      if (!dragging) return;
      dragging = false;
      var w = viewport.clientWidth || 1;
      var swiped = axis === "x" && Math.abs(dx) > Math.min(48, w * 0.16);
      var tapped = openIfTap && axis !== "y" && !swiped;
      if (swiped) {
        ignoreClick = true;
        setIndex(index + (dx < 0 ? 1 : -1), true);
      } else {
        setIndex(index, true);
      }
      axis = null;
      dx = 0;
      if (tapped) openIssue(currentUrl());
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
        showOnly(index, index + (dx < 0 ? 1 : -1));
        var extra = dx;
        if ((index === 0 && dx > 0) || (index === count - 1 && dx < 0)) extra = dx * 0.2;
        track.style.transform = "translate3d(" + (-index * (slideWidth() || 1) + extra) + "px,0,0)";
        if (e.cancelable) e.preventDefault();
      },
      { passive: false }
    );
    viewport.addEventListener(
      "touchend",
      function () {
        finish(true);
      },
      { passive: true }
    );
    viewport.addEventListener(
      "touchcancel",
      function () {
        finish(false);
      },
      { passive: true }
    );

    viewport.addEventListener(
      "click",
      function (e) {
        if (e.target.closest && e.target.closest(".landing-roundup-dot, .landing-roundup-arrow, button")) return;
        e.preventDefault();
        e.stopImmediatePropagation();
        if (ignoreClick) {
          ignoreClick = false;
          return;
        }
        openIssue(currentUrl());
      },
      true
    );

    if (dotsHost) {
      dotsHost.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-roundup-index]");
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();
        setIndex(parseInt(btn.getAttribute("data-roundup-index"), 10) || 0, true);
      });
    }
    function onArrow(e, delta) {
      e.preventDefault();
      e.stopPropagation();
      setIndex(index + delta, true);
    }
    if (prevBtn) prevBtn.addEventListener("click", function (e) { onArrow(e, -1); });
    if (nextBtn) nextBtn.addEventListener("click", function (e) { onArrow(e, 1); });

    section.tabIndex = 0;
    section.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        setIndex(index - 1, true);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setIndex(index + 1, true);
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openIssue(currentUrl());
      }
    });

    window.addEventListener("resize", function () {
      setIndex(index, false);
    });

    setIndex(0, false);
  }

  function hydrateDeck(slide) {
    if (!slide || slide.getAttribute("data-deck") === "1") return;
    var url = slide.getAttribute("data-issue-url");
    if (!url) return;
    slide.setAttribute("data-deck", "1");
    fetch(issuePath(url), { cache: "no-store" })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        var hero = heroFrom(html, url, null);
        var dateNode = slide.querySelector(".landing-roundup-date");
        if (dateNode && hero.date) dateNode.textContent = hero.date;
      })
      .catch(function () {});
  }

  function issueStamp(hero) {
    var m = String((hero && hero.pageUrl) || "").match(/(\d{4}-\d{2}-\d{2})/);
    return m ? m[1] : "";
  }

  function paintAll(heroes) {
    track.innerHTML = "";
    // Edition 1 is the earliest issue. A newer date always takes the next number.
    var editionByUrl = {};
    heroes.slice().sort(function (a, b) {
      var da = issueStamp(a);
      var db = issueStamp(b);
      if (da < db) return -1;
      if (da > db) return 1;
      return 0;
    }).forEach(function (hero, n) {
      editionByUrl[hero.pageUrl] = n + 1;
    });
    heroes.forEach(function (hero, i) {
      var slide = document.createElement("article");
      slide.className = "landing-top-card-face landing-roundup-slide";
      if (i === 0) {
        slide.id = "landing-roundup-face";
        slide.setAttribute("data-deck", "1");
      }
      fillCard(slide, hero, { eager: i === 0, edition: editionByUrl[hero.pageUrl] });
      slide.style.visibility = i === 0 ? "visible" : "hidden";
      track.appendChild(slide);
      if (layoutObserver) layoutObserver.observe(slide);
    });
    sizeSlides();
    bindCarousel(heroes.length);
    paintReads();
    // Keep the heavy editorial font/CSS off the critical card-rendering path.
    requestAnimationFrame(loadRoundupEditorialStyles);
  }

  var roundupReadMap = null;
  function paintReads() {
    if (!roundupReadMap) return;
    Array.prototype.forEach.call(track.children, function (slide) {
      var url = slide.getAttribute("data-issue-url") || "";
      var match = url.match(/(\d{4}-\d{2}-\d{2})/);
      var reads = match ? roundupReadMap[match[1]] : null;
      var node = slide.querySelector(".landing-roundup-reads");
      if (!node) {
        node = document.createElement("span");
        node.className = "landing-roundup-reads";
        slide.appendChild(node);
      }
      if (reads == null) {
        node.hidden = true;
        return;
      }
      node.hidden = false;
      node.textContent = String(reads);
      node.setAttribute("aria-label", reads + " reads");
    });
  }

  fetch("/api/roundup-read-counts", { cache: "no-store" })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (!data || !data.by_date) return;
      roundupReadMap = data.by_date;
      paintReads();
    })
    .catch(function () {});

  fetch("/sailing-roundup/feed.json", { cache: "default" })
    .then(function (r) {
      return r.json();
    })
    .then(function (items) {
      var rows = (items || []).filter(function (item) {
        return item && item.url;
      });
      if (!rows.length) return;
      var firstImage = rows[0].image;
      if (firstImage) {
        var preload = document.createElement("link");
        preload.rel = "preload";
        preload.as = "image";
        preload.href = firstImage.indexOf("http") === 0 ? firstImage : absUrl("https://sailingsa.co.za/sailing-roundup/", firstImage);
        preload.setAttribute("fetchpriority", "high");
        document.head.appendChild(preload);
      }
      // Feed already contains the titles, dates, and images for every card.
      // Paint immediately; never wait for the newest issue HTML on the critical path.
      var heroes = rows.map(function (item) {
        return heroFrom("", fullIssueUrl(item.url), item);
      }).filter(function (hero) {
        return hero && hero.pageUrl;
      });
      if (heroes.length) paintAll(heroes);
      var firstUrl = fullIssueUrl(rows[0].url);
      fetch(issuePath(firstUrl), { cache: "default" })
        .then(function (r) { return r.ok ? r.text() : ""; })
        .then(function (html) {
          if (!html) return;
          var detail = heroFrom(html, firstUrl, rows[0]);
          var firstSlide = track.firstElementChild;
          var dateNode = firstSlide && firstSlide.querySelector(".landing-roundup-date");
          if (dateNode && detail.date && dateNode.isConnected) dateNode.textContent = detail.date;
        })
        .catch(function () {});
    })
    .catch(function () {});
})();
