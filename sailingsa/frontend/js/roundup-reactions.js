(function () {
    if (window.__roundupReacts) return;
    window.__roundupReacts = true;

    var KINDS = [["up", "👍"], ["heart", "❤️"], ["down", "👎"]];
    var cache = {};
    var ACTIONS_ID = "landing-roundup-actions";

    function issueKey(url) {
        var match = String(url || "").match(/\/issues\/(\d{4}-\d{2}-\d{2})(?:\/|#|\?|$)/);
        return match ? match[1] : "";
    }

    function countText(emoji, count) {
        return count ? (emoji + " " + count) : emoji;
    }

    function stop(event) {
        if (event.stopImmediatePropagation) event.stopImmediatePropagation();
        else event.stopPropagation();
    }

    function compactHeadline(value, key) {
        var text = String(value || "").replace(/\s+/g, " ").trim();
        if (text.length > 72) text = text.slice(0, 69).replace(/\s+\S*$/, "") + "...";
        if (text.length < 3) text = "Roundup " + key;
        return text;
    }

    function slideInfo(slide) {
        var url = (slide && slide.getAttribute("data-issue-url")) || "";
        var key = issueKey(url);
        var titleNode = slide && slide.querySelector(".landing-roundup-title");
        var headline = compactHeadline(titleNode ? titleNode.textContent : "", key);
        return {
            key: key,
            url: url || ("/sailing-roundup/issues/" + key + "/"),
            headline: headline
        };
    }

    function rowInfo(row) {
        var key = (row && row.getAttribute("data-issue-key")) || "";
        return {
            key: key,
            url: (row && row.getAttribute("data-issue-url")) || ("/sailing-roundup/issues/" + key + "/"),
            headline: (row && row.getAttribute("data-issue-headline")) || ("Roundup " + key)
        };
    }

    function openDocksideComment(info) {
        if (!info || !info.key) return;
        if (!window.__docksideRoundupLeaders) window.__docksideRoundupLeaders = {};
        var tag = "@" + String(info.headline || "").replace(/\s+/g, " ").trim();
        window.__docksideRoundupLeaders[tag] = {
            key: info.key,
            url: info.url,
            headline: String(info.headline || "").replace(/\s+/g, " ").trim(),
            tag: tag
        };
        var onIssue = /\/sailing-roundup\/issues\//.test(location.pathname);
        if (!onIssue) {
            try {
                sessionStorage.setItem("dockside_roundup_comment", JSON.stringify(info));
            } catch (err) {}
        }
        if (typeof window.docksideOpenComment === "function") {
            window.docksideOpenComment(info);
            return;
        }
        window.__docksideCommentQueue = window.__docksideCommentQueue || [];
        window.__docksideCommentQueue.push(info);
        if (onIssue) return;
        var card = document.getElementById("dockside-landing");
        if (card) card.scrollIntoView({ block: "center" });
    }

    function paint(row, issue, payload) {
        row.textContent = "";
        row.setAttribute("data-issue-key", issue);
        var counts = (payload && payload.counts) || {};
        var mine = (payload && payload.mine) || [];
        KINDS.forEach(function (pair) {
            var button = document.createElement("button");
            button.type = "button";
            button.setAttribute("data-roundup-kind", pair[0]);
            var count = counts[pair[0]] || 0;
            button.textContent = countText(pair[1], count);
            if (mine.indexOf(pair[0]) >= 0) button.className = "is-mine";
            button.addEventListener("click", function (event) {
                event.preventDefault();
                stop(event);
                fetch("/api/dockside/roundup/react", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ issue_key: issue, kind: pair[0] })
                }).then(function (res) {
                    return res.json().catch(function () { return {}; });
                }).then(function (data) {
                    if (data && data.reactions) paintAll(issue, data.reactions);
                });
            });
            row.appendChild(button);
        });
        var comment = document.createElement("button");
        comment.type = "button";
        comment.setAttribute("data-roundup-comment", "1");
        comment.textContent = "Comment";
        comment.addEventListener("click", function (event) {
            event.preventDefault();
            stop(event);
            openDocksideComment(rowInfo(row));
        });
        row.appendChild(comment);
    }

    function paintAll(issue, payload) {
        cache[issue] = payload || cache[issue] || { counts: { up: 0, heart: 0, down: 0 }, mine: [] };
        Array.prototype.forEach.call(document.querySelectorAll('.roundup-reacts[data-issue-key="' + issue + '"]'), function (row) {
            paint(row, issue, cache[issue]);
        });
    }

    function makeRow(info, payload) {
        var row = document.createElement("div");
        row.className = "roundup-reacts";
        row.setAttribute("data-issue-key", info.key);
        row.setAttribute("data-issue-url", info.url || "");
        row.setAttribute("data-issue-headline", info.headline || "");
        // Bubble only — capture+stopImmediate would kill the button handlers.
        row.addEventListener("click", function (event) { event.stopPropagation(); });
        row.addEventListener("touchstart", function (event) { event.stopPropagation(); }, { passive: true });
        row.addEventListener("touchend", function (event) { event.stopPropagation(); }, { passive: true });
        paint(row, info.key, payload);
        return row;
    }

    function ensureStyle() {
        if (document.querySelector("link[data-roundup-reacts]")) return;
        var link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = "/css/roundup-reactions.css?v=dockside27";
        link.setAttribute("data-roundup-reacts", "1");
        document.head.appendChild(link);
    }

    function ensureDocksideAssets() {
        if (!document.querySelector("link[href*='dockside-chat.css']")) {
            var css = document.createElement("link");
            css.rel = "stylesheet";
            css.href = "/css/dockside-chat.css?v=dockside18";
            document.head.appendChild(css);
        }
        if (!document.querySelector("script[src*='dockside-chat.js']")) {
            var js = document.createElement("script");
            js.src = "/js/dockside-chat.js?v=dockside24";
            js.defer = true;
            document.head.appendChild(js);
        }
    }

    function activeSlide() {
        var slides = document.querySelectorAll(".landing-roundup-slide[data-issue-url]");
        var visible = null;
        Array.prototype.forEach.call(slides, function (slide) {
            if (slide.getAttribute("aria-hidden") === "false") visible = slide;
            else if (!visible && slide.style.visibility !== "hidden") visible = slide;
        });
        return visible || slides[0] || null;
    }

    function stripInSlideRows() {
        Array.prototype.forEach.call(document.querySelectorAll(".landing-roundup-slide .roundup-reacts"), function (row) {
            if (row.parentNode) row.parentNode.removeChild(row);
        });
    }

    function ensureActionsHost() {
        var card = document.getElementById("landing-top-card");
        var viewport = document.getElementById("landing-roundup-viewport");
        if (!card || !viewport) return null;
        var host = document.getElementById(ACTIONS_ID);
        if (host) return host;
        host = document.createElement("div");
        host.id = ACTIONS_ID;
        host.className = "landing-roundup-actions";
        host.setAttribute("aria-label", "Roundup reactions");
        if (viewport.nextSibling) card.insertBefore(host, viewport.nextSibling);
        else card.appendChild(host);
        return host;
    }

    function syncLandingBar(known) {
        stripInSlideRows();
        var host = ensureActionsHost();
        if (!host) return;
        var slide = activeSlide();
        if (!slide) return;
        var info = slideInfo(slide);
        if (!info.key) return;
        if (known && known[info.key]) cache[info.key] = known[info.key];
        if (!window.__docksideRoundupLeaders) window.__docksideRoundupLeaders = {};
        var tag = "@" + info.headline;
        window.__docksideRoundupLeaders[tag] = {
            key: info.key,
            url: info.url,
            headline: info.headline,
            tag: tag
        };
        var row = host.querySelector(".roundup-reacts");
        if (!row) {
            row = makeRow(info, cache[info.key]);
            host.appendChild(row);
            return;
        }
        row.setAttribute("data-issue-key", info.key);
        row.setAttribute("data-issue-url", info.url);
        row.setAttribute("data-issue-headline", info.headline);
        paint(row, info.key, cache[info.key]);
    }

    function registerLeaders() {
        Array.prototype.forEach.call(document.querySelectorAll(".landing-roundup-slide[data-issue-url]"), function (slide) {
            var info = slideInfo(slide);
            if (!info.key) return;
            if (!window.__docksideRoundupLeaders) window.__docksideRoundupLeaders = {};
            var tag = "@" + info.headline;
            window.__docksideRoundupLeaders[tag] = {
                key: info.key,
                url: info.url,
                headline: info.headline,
                tag: tag
            };
        });
    }

    function load(keys) {
        if (!keys.length) return Promise.resolve({});
        return fetch("/api/dockside/roundup/reactions?keys=" + encodeURIComponent(keys.join(",")), {
            credentials: "same-origin",
            cache: "no-store"
        }).then(function (res) {
            return res.json().catch(function () { return {}; });
        }).then(function (data) {
            return (data && data.issues) || {};
        }).catch(function () { return {}; });
    }

    function bootCards() {
        var track = document.getElementById("landing-roundup-track");
        if (!track) return;
        ensureStyle();
        var timer = null;
        function schedule() {
            window.clearTimeout(timer);
            timer = window.setTimeout(function () {
                var slides = document.querySelectorAll(".landing-roundup-slide[data-issue-url]");
                var keys = [];
                Array.prototype.forEach.call(slides, function (slide) {
                    var key = issueKey(slide.getAttribute("data-issue-url"));
                    if (key && keys.indexOf(key) < 0) keys.push(key);
                });
                registerLeaders();
                if (!keys.length) return;
                load(keys).then(function (known) {
                    Object.keys(known).forEach(function (key) { cache[key] = known[key]; });
                    syncLandingBar(known);
                });
            }, 40);
        }
        new MutationObserver(schedule).observe(track, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["aria-hidden", "style", "data-issue-url"]
        });
        var dots = document.getElementById("landing-roundup-dots");
        if (dots) {
            dots.addEventListener("click", function () {
                window.setTimeout(function () { syncLandingBar(); }, 0);
                window.setTimeout(function () { syncLandingBar(); }, 340);
            }, true);
        }
        schedule();
    }

    function mountIssueDockside(info) {
        if (document.getElementById("dockside-landing")) return;
        ensureDocksideAssets();
        var host = document.createElement("section");
        host.id = "dockside-landing";
        host.className = "dockside-landing";
        host.setAttribute("aria-label", "Dockside Chat");
        host.setAttribute("data-dockside-card", "1");
        host.setAttribute("data-roundup-key", info.key);
        host.setAttribute("data-roundup-url", info.url);
        host.setAttribute("data-roundup-headline", info.headline);
        host.innerHTML =
            '<div class="dockside-head">' +
            '<div class="dockside-brand">' +
            '<svg class="dockside-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
            '<path fill="#001f3f" d="M5 3.5h14a2.5 2.5 0 0 1 2.5 2.5v8.2a2.5 2.5 0 0 1-2.5 2.5H9.2L4.2 21v-4.3H5A2.5 2.5 0 0 1 2.5 14.2V6A2.5 2.5 0 0 1 5 3.5z"/>' +
            "</svg>" +
            '<div class="dockside-titles">' +
            '<h2 class="dockside-kicker">Dockside Chat</h2>' +
            '<p class="dockside-sub">Sailors on the dock</p>' +
            "</div></div>" +
            '<a class="dockside-viewall" href="/dockside.html">View all</a>' +
            "</div>" +
            '<div id="dockside-topic">' +
            '<div class="dockside-op" id="dockside-original"></div>' +
            '<div class="dockside-scroll" id="dockside-scroll" tabindex="0"></div>' +
            '<form class="dockside-compose" id="dockside-reply-form" action="/dockside.html" method="get">' +
            '<span class="dockside-avatar dockside-avatar--me" id="dockside-me-avatar" aria-hidden="true"></span>' +
            '<label class="dockside-sr" for="dockside-reply-body">Comment</label>' +
            '<input id="dockside-reply-body" type="text" maxlength="2000" placeholder="Write a comment" autocomplete="off">' +
            '<button type="submit" class="dockside-post">Post</button>' +
            "</form></div>" +
            '<div id="dockside-empty" class="dockside-invite" hidden></div>';
        var paper = document.querySelector("main.paper") || document.querySelector(".paper") || document.body;
        paper.appendChild(host);
        if (location.hash === "#dockside-comment") {
            try {
                history.replaceState(null, "", location.pathname + location.search);
            } catch (err) {}
        }
    }

    function bootIssue() {
        var key = issueKey(location.pathname + "/");
        if (!key) return;
        ensureStyle();
        var headlineNode = document.querySelector(".edition-headline, h2.edition-headline, .story-lead h2");
        var info = {
            key: key,
            url: location.pathname.replace(/\/?$/, "/"),
            headline: compactHeadline(headlineNode ? headlineNode.textContent : document.title, key)
        };
        var existing = document.querySelector('.roundup-reacts[data-issue-key="' + key + '"]');
        function place(row) {
            if (existing) return;
            var folio = document.querySelector(".folio");
            var paper = document.querySelector("main.paper") || document.querySelector(".paper");
            if (folio && folio.parentNode) folio.parentNode.insertBefore(row, folio.nextSibling);
            else if (paper) paper.insertBefore(row, paper.firstChild);
            else document.body.insertBefore(row, document.body.firstChild);
        }
        load([key]).then(function (known) {
            cache[key] = known[key] || cache[key];
            if (existing) {
                existing.setAttribute("data-issue-url", info.url);
                existing.setAttribute("data-issue-headline", info.headline);
                paint(existing, key, cache[key]);
            } else {
                place(makeRow(info, cache[key]));
            }
            mountIssueDockside(info);
        });
    }

    // Capture Comment only. Do not stop reaction clicks or their button handlers die.
    document.addEventListener("click", function (event) {
        var comment = event.target.closest && event.target.closest("button[data-roundup-comment='1']");
        if (!comment) return;
        var reactRow = comment.closest(".roundup-reacts");
        if (!reactRow) return;
        event.preventDefault();
        if (event.stopImmediatePropagation) event.stopImmediatePropagation();
        else event.stopPropagation();
        openDocksideComment(rowInfo(reactRow));
    }, true);

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            bootCards();
            bootIssue();
        });
    } else {
        bootCards();
        bootIssue();
    }
})();
