(function () {
    if (window.__roundupReacts) return;
    window.__roundupReacts = true;

    var KINDS = [["up", "👍"], ["heart", "❤️"], ["down", "👎"]];

    function issueKey(url) {
        var match = String(url || "").match(/\/issues\/(\d{4}-\d{2}-\d{2})(?:\/|#|\?|$)/);
        return match ? match[1] : "";
    }

    function countText(emoji, count) {
        return count ? (emoji + " " + count) : emoji;
    }

    function stop(event) {
        event.stopPropagation();
    }

    function paint(row, issue, payload) {
        row.textContent = "";
        var counts = (payload && payload.counts) || {};
        var mine = (payload && payload.mine) || [];
        KINDS.forEach(function (pair) {
            var button = document.createElement("button");
            button.type = "button";
            var count = counts[pair[0]] || 0;
            button.textContent = countText(pair[1], count);
            if (mine.indexOf(pair[0]) >= 0) button.className = "is-mine";
            button.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                fetch("/api/dockside/roundup/react", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ issue_key: issue, kind: pair[0] })
                }).then(function (res) {
                    return res.json().catch(function () { return {}; });
                }).then(function (data) {
                    if (data && data.reactions) paint(row, issue, data.reactions);
                });
            });
            row.appendChild(button);
        });
        var comment = document.createElement("button");
        comment.type = "button";
        comment.textContent = "Comment";
        comment.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            if (typeof window.docksideOpenComment === "function") {
                window.docksideOpenComment();
                return;
            }
            window.location.assign("/#dockside-comment");
        });
        row.appendChild(comment);
    }

    function makeRow(issue, payload) {
        var row = document.createElement("div");
        row.className = "roundup-reacts";
        row.addEventListener("click", stop);
        row.addEventListener("touchstart", stop, { passive: true });
        row.addEventListener("touchend", stop, { passive: true });
        paint(row, issue, payload);
        return row;
    }

    function ensureStyle() {
        if (document.querySelector("link[data-roundup-reacts]")) return;
        var link = document.createElement("link");
        link.rel = "stylesheet";
        link.href = "/css/roundup-reactions.css?v=dockside21";
        link.setAttribute("data-roundup-reacts", "1");
        document.head.appendChild(link);
    }

    function syncCards(known) {
        var slides = document.querySelectorAll(".landing-roundup-slide[data-issue-url]");
        Array.prototype.forEach.call(slides, function (slide) {
            var key = issueKey(slide.getAttribute("data-issue-url"));
            if (!key) return;
            var existing = slide.querySelector(".roundup-reacts");
            if (existing) return;
            slide.appendChild(makeRow(key, known[key]));
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
                    if (slide.querySelector(".roundup-reacts")) return;
                    var key = issueKey(slide.getAttribute("data-issue-url"));
                    if (key && keys.indexOf(key) < 0) keys.push(key);
                });
                if (!keys.length) return;
                load(keys).then(function (known) { syncCards(known); });
            }, 40);
        }
        new MutationObserver(schedule).observe(track, { childList: true, subtree: true });
        schedule();
    }

    function bootIssue() {
        var key = issueKey(location.pathname + "/");
        if (!key || document.querySelector(".roundup-reacts")) return;
        var folio = document.querySelector(".folio");
        var paper = document.querySelector(".paper");
        if (!folio && !paper) return;
        ensureStyle();
        load([key]).then(function (known) {
            if (document.querySelector(".roundup-reacts")) return;
            var row = makeRow(key, known[key]);
            if (folio && folio.parentNode) folio.parentNode.insertBefore(row, folio.nextSibling);
            else paper.insertBefore(row, paper.firstChild);
        });
    }

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
