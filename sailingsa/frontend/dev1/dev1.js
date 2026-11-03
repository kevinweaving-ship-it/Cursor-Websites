/**
 * /dev1/ chrome — one pass, no setInterval polling, no header enforcer.
 * Order: cards.js paints slides → this file fills the actions row that
 * already exists in the HTML (so first paint already has the navy shell).
 */
(function () {
  "use strict";

  var SEND_SVG =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20 21 12 4 4l3 8-3 8Zm3-8h14"/></svg>';
  var PATHS = {
    up: "M7 10v10H4V10h3l4-8 2 3v4h6l-2 12H7",
    heart:
      "M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z",
    down: "M17 14V4h3v10h-3l-4 8-2-3v-4H5L3 3h14",
  };

  function activeSlide() {
    return (
      document.querySelector("#landing-roundup-track .landing-roundup-slide[aria-hidden='false']") ||
      document.querySelector("#landing-roundup-track .landing-roundup-slide")
    );
  }

  function activeIssue() {
    var slide = activeSlide();
    if (!slide) return null;
    var url = slide.getAttribute("data-issue-url") || "";
    var match = url.match(/issues\/(\d{4}-\d{2}-\d{2})/);
    if (!match) return null;
    var title = slide.querySelector(".landing-roundup-title");
    return {
      key: match[1],
      url: url,
      headline: ((title && title.textContent) || "Weekly Roundup").trim().slice(0, 72),
    };
  }

  function paintReadBar() {
    var host = document.getElementById("landing-roundup-actions");
    var slide = activeSlide();
    if (!host) return;
    var link = document.getElementById("dev1-read-active");
    if (!link) {
      link = document.createElement("a");
      link.id = "dev1-read-active";
      link.textContent = "Read full roundup";
      host.appendChild(link);
    }
    link.href =
      (slide && slide.getAttribute("data-issue-url")) || "/sailing-roundup/latest/";
    var reads = slide && slide.querySelector(".landing-roundup-reads");
    var count = document.getElementById("dev1-read-count");
    if (!count) {
      count = document.createElement("span");
      count.id = "dev1-read-count";
    }
    if (count.nextElementSibling !== link) host.insertBefore(count, link);
    count.textContent =
      reads && reads.textContent.trim() ? "◉ " + reads.textContent.trim() : "";
  }

  function attachComposer() {
    var host = document.getElementById("landing-roundup-actions");
    if (!host) return;
    var form = document.getElementById("dev1-card-compose");
    if (!form) {
      form = document.createElement("form");
      form.id = "dev1-card-compose";
      var field = document.createElement("input");
      field.type = "text";
      field.maxLength = 2000;
      field.required = true;
      field.placeholder = "Write a comment…";
      field.setAttribute("aria-label", "Write a comment on this roundup");
      var button = document.createElement("button");
      button.type = "submit";
      button.className = "dev1-canonical-send";
      button.setAttribute("aria-label", "Post comment to Dockside Chat");
      button.innerHTML = SEND_SVG;
      form.append(field, button);
      var before =
        document.getElementById("dev1-read-count") ||
        document.getElementById("dev1-read-active");
      if (before) host.insertBefore(form, before);
      else host.appendChild(form);
    }
    if (form.getAttribute("data-dev1-bound") === "1") return;
    form.setAttribute("data-dev1-bound", "1");
    var field = form.querySelector("input");
    var button = form.querySelector("button");
    var msg = document.getElementById("dev1-card-message");
    if (!msg) {
      msg = document.createElement("div");
      msg.id = "dev1-card-message";
      host.appendChild(msg);
    }
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      event.stopPropagation();
      var info = activeIssue();
      var body = field ? field.value.trim() : "";
      if (!info || !body || !button || button.disabled) return;
      button.disabled = true;
      msg.textContent = "";
      fetch("/api/dockside/roundup/" + encodeURIComponent(info.key) + "/posts", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          body: body,
          parent_post_id: null,
          headline: info.headline,
        }),
      })
        .then(function (response) {
          return response.json().catch(function () {
            return {};
          }).then(function (data) {
            return { response: response, data: data };
          });
        })
        .then(function (pack) {
          if (pack.response.status === 401 || pack.response.status === 403) {
            msg.textContent = "Sign in to publish this comment.";
            try {
              sessionStorage.setItem(
                "dev1-roundup-pending",
                JSON.stringify({ body: body, key: info.key })
              );
            } catch (err) {}
            if (typeof window.sailingHandleHeaderSignUp === "function") {
              window.sailingHandleHeaderSignUp();
            } else {
              var signup = document.getElementById("authSignUpBtn");
              if (signup) signup.click();
            }
            return;
          }
          if (!pack.response.ok || !pack.data.topic) {
            msg.textContent = pack.data.detail || "Comment not saved";
            return;
          }
          field.value = "";
          msg.textContent = "Posted to Dockside Chat.";
          if (typeof window.docksideOpenComment === "function") {
            window.docksideOpenComment(info);
          }
        })
        .catch(function () {
          msg.textContent = "Connection error — not posted.";
        })
        .finally(function () {
          button.disabled = false;
        });
    });
  }

  function paintReactionOutlines() {
    document
      .querySelectorAll(
        "#dev1-root button[data-roundup-kind], #dev1-root .dockside-reacts button"
      )
      .forEach(function (button) {
        if (button.dataset.outline) return;
        var kind = button.dataset.roundupKind;
        var text = button.textContent.trim();
        if (!kind) {
          kind = text.indexOf("👍") === 0 ? "up" : text.indexOf("❤️") === 0 ? "heart" : text.indexOf("👎") === 0 ? "down" : "";
        }
        if (!PATHS[kind]) return;
        var num = (text.match(/\d+/) || [])[0] || "";
        button.dataset.outline = kind;
        button.innerHTML =
          '<svg width="17" height="17" viewBox="0 0 24 24" fill="' +
          (button.classList.contains("is-mine") ? "currentColor" : "none") +
          '" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"><path d="' +
          PATHS[kind] +
          '"/></svg>' +
          (num ? " " + num : "");
      });
  }

  function syncCountFill() {
    document
      .querySelectorAll(
        "#dev1-root .roundup-reacts button[data-roundup-kind], #dev1-root .dockside-reacts button[data-outline]"
      )
      .forEach(function (button) {
        var match = (button.textContent || "").match(/\d+/);
        button.dataset.hasCount = match && Number(match[0]) > 0 ? "1" : "0";
      });
  }

  function paintSendIcons() {
    document
      .querySelectorAll(
        "#dev1-card-compose button[type=submit], #dockside-landing .dockside-compose button[type=submit], #dockside-landing .dockside-inline-reply button[type=submit]"
      )
      .forEach(function (button) {
        if (button.classList.contains("dev1-canonical-send")) return;
        button.classList.add("dev1-canonical-send");
        button.setAttribute("aria-label", "Post");
        button.innerHTML = SEND_SVG;
      });
  }

  function bindFocus() {
    var root = document.getElementById("dev1-root");
    if (!root || root.getAttribute("data-dev1-focus") === "1") return;
    root.setAttribute("data-dev1-focus", "1");
    root.addEventListener("click", function (event) {
      var reply = event.target.closest("button.dockside-mini");
      var wrap = event.target.closest(
        "#dev1-card-compose, #dockside-reply-form, #dockside-start-form, .dockside-inline-reply"
      );
      var scope = null;
      if (reply && /reply/i.test(reply.textContent || "")) {
        scope = reply.closest(".dockside-comment, .dockside-reply") || root;
      } else if (wrap && !event.target.closest("button, input, textarea, a")) {
        scope = wrap;
      }
      if (!scope) return;
      var inputs = Array.prototype.filter.call(
        scope.querySelectorAll("input:not([type=hidden]), textarea"),
        function (input) {
          return input.getClientRects().length && !input.disabled;
        }
      );
      if (!inputs.length) return;
      var input = inputs[inputs.length - 1];
      try {
        input.focus({ preventScroll: true });
      } catch (err) {
        input.focus();
      }
    });
  }

  function bindFloatingCompose() {
    var chat = document.getElementById("dockside-landing");
    var top = document.getElementById("dockside-original");
    var form = document.getElementById("dockside-reply-form");
    if (!chat || !top || !form || form.getAttribute("data-dev1-float") === "1") return;
    form.setAttribute("data-dev1-float", "1");
    var raf = 0;
    function update() {
      raf = 0;
      if (form.hidden || !top.getClientRects().length) {
        form.classList.remove("dev1-floating-compose");
        return;
      }
      var a = top.getBoundingClientRect();
      var b = chat.getBoundingClientRect();
      var h = window.innerHeight;
      form.classList.toggle(
        "dev1-floating-compose",
        a.bottom < 65 && b.bottom > h * 0.32 && b.top < h * 0.65
      );
    }
    function schedule() {
      if (!raf) raf = window.requestAnimationFrame(update);
    }
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule, { passive: true });
    schedule();
  }

  function bootChrome() {
    attachComposer();
    paintReadBar();
    paintReactionOutlines();
    syncCountFill();
    paintSendIcons();
    bindFocus();
    bindFloatingCompose();
  }

  var root = document.getElementById("dev1-root");
  var pending = false;
  function scheduleChrome() {
    if (pending) return;
    pending = true;
    queueMicrotask(function () {
      pending = false;
      bootChrome();
    });
  }

  document.addEventListener("dev1:roundup-ready", bootChrome);
  document.addEventListener("dev1:roundup-slide", paintReadBar);
  if (root && typeof MutationObserver === "function") {
    new MutationObserver(scheduleChrome).observe(root, {
      childList: true,
      subtree: true,
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootChrome, { once: true });
  } else {
    bootChrome();
  }
})();
