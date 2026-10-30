(function () {
    if (window.__docksideBoot) return;
    window.__docksideBoot = true;

    var DRAFT_KEY = "dockside_draft";
    var SORT_KEY = "dockside_topic_sort";
    var me = { signed_in: false };
    window.__docksideCommentQueue = window.__docksideCommentQueue || [];
    if (typeof window.docksideOpenComment !== "function") {
        window.docksideOpenComment = function (info) {
            window.__docksideCommentQueue.push(info || null);
            // Do not jump the Roundup issue page while Dockside is still booting.
            if (/\/sailing-roundup\/issues\//.test(location.pathname)) return;
            var card = document.getElementById("dockside-landing");
            if (card) card.scrollIntoView({ block: "center" });
        };
    }

    function when(iso) {
        if (!iso) return "";
        try {
            return new Date(iso).toLocaleString("en-ZA", {
                timeZone: "Africa/Johannesburg",
                day: "numeric",
                month: "short",
                hour: "2-digit",
                minute: "2-digit"
            });
        } catch (err) {
            return "";
        }
    }

    function shortWhen(iso) {
        if (!iso) return "";
        var then = new Date(iso).getTime();
        if (!then) return "";
        var mins = Math.max(0, Math.round((Date.now() - then) / 60000));
        if (mins < 1) return "now";
        if (mins < 60) return mins + "m";
        var hours = Math.round(mins / 60);
        if (hours < 36) return hours + "h";
        var days = Math.round(hours / 24);
        if (days < 7) return days + "d";
        return when(iso);
    }

    function rememberDraftForAuth(draft) {
        try { sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft)); } catch (err) {}
        try {
            var url = new URL(window.location.href);
            url.searchParams.set("dockside_resume", "1");
            history.replaceState(null, "", url.pathname + url.search + url.hash);
        } catch (err2) {}
    }

    function takeResumeDraft() {
        var url;
        try { url = new URL(window.location.href); } catch (err) { return null; }
        if (url.searchParams.get("dockside_resume") !== "1") return null;
        var draft = readDraft();
        url.searchParams.delete("dockside_resume");
        var next = url.searchParams.toString();
        history.replaceState(null, "", url.pathname + (next ? "?" + next : "") + url.hash);
        return draft;
    }

    function goLogin(draft) {
        if (draft) rememberDraftForAuth(draft);
        if (typeof sailingHandleHeaderSignUp === "function") {
            sailingHandleHeaderSignUp();
            return;
        }
        var signUpBtn = document.getElementById("authSignUpBtn");
        if (signUpBtn) {
            signUpBtn.click();
            return;
        }
        var here = "";
        try { here = window.location.href || ""; } catch (err) {}
        try { sessionStorage.setItem("auth_returnTo", here); } catch (err2) {}
        window.location.href = (window.location.origin || "") + "/signup.html?signup=1&returnTo=" + encodeURIComponent(here);
    }

    function readDraft() {
        try {
            var raw = sessionStorage.getItem(DRAFT_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (err) {
            return null;
        }
    }

    function clearDraft() {
        try { sessionStorage.removeItem(DRAFT_KEY); } catch (err) {}
    }

    function guardComposer(inputs, keepValue) {
        var nodes = [];
        (inputs || []).forEach(function (input) {
            if (input && nodes.indexOf(input) < 0) nodes.push(input);
        });
        var generation = 0;
        function stop() { generation += 1; }
        nodes.forEach(function (input) {
            input.setAttribute("autocomplete", "off");
            input.setAttribute("autocorrect", "off");
            if (input.getAttribute("name")) input.removeAttribute("name");
            if (typeof keepValue !== "function") {
                input.readOnly = true;
                function unlock() { input.readOnly = false; }
                input.addEventListener("pointerdown", unlock);
                input.addEventListener("touchstart", unlock);
                input.addEventListener("focus", unlock);
            }
            input.addEventListener("keydown", function (event) {
                if (event.isTrusted) stop();
            });
            input.addEventListener("beforeinput", function (event) {
                if (event.isTrusted) stop();
            });
        });
        function write() {
            var gen = generation;
            [0, 60, 250, 800].forEach(function (ms) {
                window.setTimeout(function () {
                    if (gen !== generation) return;
                    nodes.forEach(function (input) {
                        var next = typeof keepValue === "function" ? (keepValue(input) || "") : "";
                        if (input.value !== next) input.value = next;
                    });
                }, ms);
            });
        }
        window.addEventListener("pageshow", write);
        write();
        return stop;
    }

    function api(path, options) {
        options = options || {};
        options.credentials = "same-origin";
        options.headers = options.headers || {};
        if (options.body && !options.headers["Content-Type"]) {
            options.headers["Content-Type"] = "application/json";
        }
        return fetch(path, options).then(function (res) {
            return res.json().catch(function () { return {}; }).then(function (data) {
                data._status = res.status;
                return data;
            });
        });
    }

    function presentAuthor(author) {
        if (!author) return author;
        var role = String(author.role || "").toLowerCase().replace(/[\s-]+/g, "_");
        var name = String(author.display_name || "").replace(/\s+/g, " ").trim().toLowerCase();
        var admin = author.is_super_admin || role === "super_admin" || role === "superadmin" || name === "kevin weaving" || name === "admin";
        if (!admin) return author;
        return {
            account_id: author.account_id,
            display_name: "Admin",
            avatar_text: "SA",
            profile_url: null,
            photo_url: "/favicon.ico"
        };
    }

    function authorNode(author, card) {
        author = presentAuthor(author);
        var name = (author && author.display_name) || "Sailor";
        var node;
        if (author && author.profile_url) {
            node = document.createElement("a");
            node.href = author.profile_url;
        } else {
            node = document.createElement("span");
        }
        node.textContent = name;
        if (card) node.className = "dockside-name";
        return node;
    }

    function initials(author) {
        author = presentAuthor(author);
        if (author && author.avatar_text) return String(author.avatar_text).slice(0, 2).toUpperCase();
        var name = ((author && author.display_name) || "").replace(/[^A-Za-z\s]/g, " ").trim();
        var parts = name.split(/\s+/).filter(Boolean);
        if (!parts.length) return "S";
        if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }

    function avatarNode(author) {
        author = presentAuthor(author);
        var wrap = document.createElement("span");
        wrap.className = "dockside-avatar";
        wrap.setAttribute("aria-hidden", "true");
        function paintInitials() {
            wrap.textContent = initials(author);
        }
        if (author && author.photo_url) {
            var img = document.createElement("img");
            img.alt = "";
            img.src = author.photo_url;
            img.addEventListener("error", function () {
                img.remove();
                paintInitials();
            });
            wrap.appendChild(img);
            return wrap;
        }
        paintInitials();
        return wrap;
    }

    function appendRoundupHeading(mount, bodyText) {
        var lead = leadingRoundupTag(bodyText || "");
        if (!lead || !lead.tag) return null;
        var head = document.createElement("a");
        head.className = "dockside-at-heading";
        head.href = (lead.info && lead.info.url) || "#";
        head.textContent = compactAtLabel((lead.info && lead.info.headline) || lead.tag.replace(/^@/, ""));
        head.title = lead.tag;
        mount.appendChild(head);
        return lead;
    }

    function cardPost(post, replies, onReply) {
        var wrap = document.createElement("article");
        wrap.className = "dockside-comment";
        var row = document.createElement("div");
        row.className = "dockside-person";
        row.appendChild(avatarNode(post.author));
        var text = document.createElement("div");
        var lead = appendRoundupHeading(text, post.body || "");
        var meta = document.createElement("div");
        meta.className = "dockside-meta";
        meta.appendChild(authorNode(post.author, true));
        var time = document.createElement("time");
        time.className = "dockside-time";
        time.dateTime = post.created_at || "";
        time.textContent = "· " + shortWhen(post.created_at);
        meta.appendChild(time);
        var body = document.createElement("p");
        body.className = "dockside-body";
        fillCommentBody(body, post.body || "", { skipLeadingTag: !!lead });
        text.appendChild(meta);
        text.appendChild(body);
        text.appendChild(actionRow(post, onReply ? replyButton(function () { onReply(post, wrap, true); }) : null));
        wrap.dataset.postId = String(post.post_id);
        row.appendChild(text);
        wrap.appendChild(row);
        (replies || []).forEach(function (reply) {
            var item = document.createElement("div");
            item.className = "dockside-reply";
            item.dataset.postId = String(reply.post_id);
            var replyRow = document.createElement("div");
            replyRow.className = "dockside-person";
            replyRow.appendChild(avatarNode(reply.author));
            var replyText = document.createElement("div");
            var replyMeta = document.createElement("div");
            replyMeta.className = "dockside-meta";
            replyMeta.appendChild(authorNode(reply.author, true));
            var replyTime = document.createElement("time");
            replyTime.className = "dockside-time";
            replyTime.dateTime = reply.created_at || "";
            replyTime.textContent = "· " + shortWhen(reply.created_at);
            replyMeta.appendChild(replyTime);
            var replyBody = document.createElement("p");
            replyBody.className = "dockside-body";
            fillCommentBody(replyBody, reply.body || "", { skipLeadingTag: true });
            replyText.appendChild(replyMeta);
            replyText.appendChild(replyBody);
            replyText.appendChild(actionRow(reply, onReply ? replyButton(function () { onReply(reply, item, false); }) : null));
            replyRow.appendChild(replyText);
            item.appendChild(replyRow);
            wrap.appendChild(item);
        });
        return wrap;
    }

    function commentAsName() {
        if (!me.signed_in) return "";
        var author = presentAuthor(me);
        return (author && author.display_name) || "sailor";
    }

    function guestsMayPost() {
        return !!(me.public_comments && me.public_comments.open);
    }

    function roundupLeaders() {
        if (!window.__docksideRoundupLeaders) window.__docksideRoundupLeaders = {};
        return window.__docksideRoundupLeaders;
    }

    function registerRoundupLeader(info) {
        if (!info || !info.key || !info.headline) return;
        var tag = "@" + String(info.headline).replace(/\s+/g, " ").trim();
        if (tag.length < 2) return;
        roundupLeaders()[tag] = {
            key: info.key,
            url: info.url || ("/sailing-roundup/issues/" + info.key + "/"),
            headline: String(info.headline).replace(/\s+/g, " ").trim(),
            tag: tag
        };
    }

    function compactAtLabel(headline) {
        var text = String(headline || "").replace(/\s+/g, " ").trim();
        if (text.length > 28) text = text.slice(0, 25).replace(/\s+\S*$/, "") + "…";
        return "@" + (text || "Roundup");
    }

    function leadingRoundupTag(text) {
        var raw = String(text || "");
        if (!raw || raw.charAt(0) !== "@") return null;
        var leaders = Object.keys(roundupLeaders()).sort(function (a, b) { return b.length - a.length; });
        var lower = raw.toLowerCase();
        for (var i = 0; i < leaders.length; i += 1) {
            var tag = leaders[i];
            if (lower.indexOf(tag.toLowerCase()) === 0) {
                var rest = raw.slice(tag.length).replace(/^[\s\-–—:]+/, "");
                return { tag: tag, rest: rest, info: roundupLeaders()[tag] };
            }
        }
        var match = raw.match(/^@([^\n]+?)(?:\s{2,}|\s(?=[A-Z0-9])|(?=\n)|$)/);
        if (!match) return null;
        // Fallback: first @… chunk before the poster’s sentence.
        var idx = raw.indexOf(" ");
        if (idx < 0) return { tag: raw.trim(), rest: "", info: null };
        // Prefer longest leader-like headline up to 72 chars.
        var guess = raw.slice(0, Math.min(raw.length, 80));
        var cut = guess.search(/\s{2,}|\s(?=[a-z])/);
        if (cut > 1) {
            return {
                tag: raw.slice(0, cut).trim(),
                rest: raw.slice(cut).replace(/^[\s\-–—:]+/, ""),
                info: null
            };
        }
        return {
            tag: raw.slice(0, idx).trim(),
            rest: raw.slice(idx).trim(),
            info: null
        };
    }

    function fillCommentBody(node, text, opts) {
        node.textContent = "";
        var raw = String(text || "");
        if (!raw) return;
        opts = opts || {};
        if (opts.skipLeadingTag) {
            var lead = leadingRoundupTag(raw);
            if (lead) raw = lead.rest;
            if (!raw) return;
        }
        var leaders = Object.keys(roundupLeaders()).sort(function (a, b) { return b.length - a.length; });
        if (!leaders.length) {
            node.textContent = raw;
            return;
        }
        var lower = raw.toLowerCase();
        var cursor = 0;
        while (cursor < raw.length) {
            var hit = null;
            var at = -1;
            leaders.forEach(function (tag) {
                var idx = lower.indexOf(tag.toLowerCase(), cursor);
                if (idx < 0) return;
                if (at < 0 || idx < at) {
                    at = idx;
                    hit = tag;
                }
            });
            if (at < 0 || !hit) {
                node.appendChild(document.createTextNode(raw.slice(cursor)));
                return;
            }
            if (at > cursor) node.appendChild(document.createTextNode(raw.slice(cursor, at)));
            var info = roundupLeaders()[hit];
            var link = document.createElement("a");
            link.className = "dockside-at-link";
            link.href = (info && info.url) || "#";
            link.textContent = compactAtLabel((info && info.headline) || hit.replace(/^@/, ""));
            link.title = hit;
            node.appendChild(link);
            cursor = at + hit.length;
        }
    }

    function mountPublicToggle(anchor) {
        if (!me.is_super_admin || !anchor || anchor.querySelector(".dockside-public-toggle")) return;
        var state = me.public_comments || {};
        var label = document.createElement("label");
        label.className = "dockside-public-toggle";
        label.title = "Opens comments and replies to everyone for 7 days. Adds another 7 days if fewer than 5 comments are posted. Turn off to require login again.";
        var input = document.createElement("input");
        input.type = "checkbox";
        input.checked = !!state.open;
        var text = document.createElement("span");
        function paintText() {
            if (state.open && state.until) {
                var when = "";
                try {
                    when = new Date(state.until).toLocaleDateString("en-ZA", {
                        timeZone: "Africa/Johannesburg",
                        day: "numeric",
                        month: "short"
                    });
                } catch (err) {}
                text.textContent = when ? ("Public until " + when) : "Public comments";
            } else {
                text.textContent = "Public comments";
            }
        }
        paintText();
        input.addEventListener("change", function () {
            var next = input.checked;
            api("/api/dockside/public-comments", {
                method: "POST",
                body: JSON.stringify({ open: next })
            }).then(function (data) {
                if (!data || data._status !== 200 || !data.public_comments) {
                    input.checked = !!state.open;
                    return;
                }
                state = data.public_comments;
                me.public_comments = state;
                input.checked = !!state.open;
                paintText();
            });
        });
        label.appendChild(input);
        label.appendChild(text);
        anchor.appendChild(label);
    }

    function reactionBar(post) {
        var bar = document.createElement("span");
        bar.className = "dockside-reacts";
        function paint() {
            bar.textContent = "";
            var counts = (post.reactions && post.reactions.counts) || {};
            var mine = (post.reactions && post.reactions.mine) || [];
            [["up", "👍"], ["heart", "❤️"], ["down", "👎"]].forEach(function (pair) {
                var button = document.createElement("button");
                button.type = "button";
                var count = counts[pair[0]] || 0;
                button.textContent = count ? (pair[1] + " " + count) : pair[1];
                if (mine.indexOf(pair[0]) >= 0) button.className = "is-mine";
                button.addEventListener("click", function () {
                    api("/api/dockside/posts/" + post.post_id + "/react", {
                        method: "POST",
                        body: JSON.stringify({ kind: pair[0] })
                    }).then(function (data) {
                        if (!data || data._status === 401) {
                            goLogin(null);
                            return;
                        }
                        if (data._status === 200 && data.reactions) {
                            post.reactions = data.reactions;
                            paint();
                        }
                    });
                });
                bar.appendChild(button);
            });
        }
        paint();
        return bar;
    }

    function actionRow(post, replyControl) {
        var actions = document.createElement("div");
        actions.className = "dockside-actions";
        actions.appendChild(reactionBar(post));
        if (replyControl) actions.appendChild(replyControl);
        return actions;
    }

    function replyButton(onClick) {
        var replyBtn = document.createElement("button");
        replyBtn.type = "button";
        replyBtn.className = "dockside-mini";
        replyBtn.textContent = "Reply";
        replyBtn.addEventListener("click", function (event) {
            event.preventDefault();
            onClick();
        });
        return replyBtn;
    }

    function postNode(post, replies, onReply, full) {
        var wrap = document.createElement("div");
        wrap.className = "dockside-comment";
        var meta = document.createElement("div");
        meta.className = "dockside-meta";
        meta.appendChild(authorNode(post.author, false));
        var time = document.createElement("time");
        time.dateTime = post.created_at || "";
        time.textContent = when(post.created_at);
        meta.appendChild(time);
        if (onReply) {
            var replyBtn = document.createElement("button");
            replyBtn.type = "button";
            replyBtn.className = "dockside-mini";
            replyBtn.textContent = "Reply";
            replyBtn.addEventListener("click", function () { onReply(post); });
            meta.appendChild(replyBtn);
        }
        if (full && me.signed_in && post.author && post.author.account_id !== me.account_id) {
            var reportBtn = document.createElement("button");
            reportBtn.type = "button";
            reportBtn.className = "dockside-mini";
            reportBtn.textContent = "Report";
            reportBtn.addEventListener("click", function () {
                var reason = window.prompt("Why are you reporting this comment?");
                if (!reason) return;
                api("/api/dockside/reports", {
                    method: "POST",
                    body: JSON.stringify({ post_id: post.post_id, reason: reason })
                }).then(function (data) {
                    reportBtn.textContent = data._status === 200 ? "Reported" : (data.detail || "Report failed");
                });
            });
            meta.appendChild(reportBtn);
        }
        if (full && me.is_super_admin) {
            var hideBtn = document.createElement("button");
            hideBtn.type = "button";
            hideBtn.className = "dockside-mini";
            hideBtn.textContent = "Hide";
            hideBtn.addEventListener("click", function () {
                api("/api/dockside/moderate", {
                    method: "POST",
                    body: JSON.stringify({ post_id: post.post_id, action: "hide" })
                }).then(function () { wrap.remove(); });
            });
            meta.appendChild(hideBtn);
        }
        var body = document.createElement("p");
        body.className = "dockside-body";
        body.textContent = post.body || "";
        wrap.appendChild(meta);
        wrap.appendChild(body);
        (replies || []).forEach(function (reply) {
            var item = document.createElement("div");
            item.className = "dockside-reply";
            var replyMeta = document.createElement("div");
            replyMeta.className = "dockside-meta";
            replyMeta.appendChild(authorNode(reply.author, false));
            var replyTime = document.createElement("time");
            replyTime.dateTime = reply.created_at || "";
            replyTime.textContent = when(reply.created_at);
            replyMeta.appendChild(replyTime);
            var replyBody = document.createElement("p");
            replyBody.className = "dockside-body";
            replyBody.textContent = reply.body || "";
            item.appendChild(replyMeta);
            item.appendChild(replyBody);
            wrap.appendChild(item);
        });
        return wrap;
    }

    function renderPosts(posts, mount, onReply, full, card) {
        mount.textContent = "";
        var byParent = {};
        (posts || []).forEach(function (post) {
            var key = post.parent_post_id || 0;
            if (!byParent[key]) byParent[key] = [];
            byParent[key].push(post);
        });
        var comments = byParent[0] || [];
        if (!comments.length) {
            var empty = document.createElement("p");
            empty.className = "dockside-empty";
            empty.textContent = "No comments yet.";
            mount.appendChild(empty);
            return;
        }
        comments.forEach(function (comment) {
            mount.appendChild(card
                ? cardPost(comment, byParent[comment.post_id] || [], onReply)
                : postNode(comment, byParent[comment.post_id] || [], onReply, full));
        });
        mount.scrollTop = mount.scrollHeight;
    }

    function fitDocksideCard(root) {
        var row = document.getElementById("landing-top-row");
        if (!row || !root) return;
        var wide = window.matchMedia("(min-width: 1024px), (max-width: 1023px) and (orientation: landscape)").matches;
        if (!wide) {
            row.style.removeProperty("--dockside-space");
            return;
        }
        row.style.setProperty("--dockside-space", (root.offsetHeight + 28) + "px");
    }

    function bootLanding() {
        var root = document.getElementById("dockside-landing");
        var topicBox = document.getElementById("dockside-topic");
        var subjectEl = document.getElementById("dockside-subject");
        var originalEl = document.getElementById("dockside-original");
        var scroll = document.getElementById("dockside-scroll");
        var form = document.getElementById("dockside-reply-form");
        var field = document.getElementById("dockside-reply-body");
        var emptyBox = document.getElementById("dockside-empty");
        var startOpen = document.getElementById("dockside-start-open");
        var startForm = document.getElementById("dockside-start-form");
        var startSubject = document.getElementById("dockside-start-subject");
        var startBody = document.getElementById("dockside-start-body");
        var meAvatar = document.getElementById("dockside-me-avatar");
        if (!root || !topicBox || !originalEl || !scroll) return;
        var topicId = null;
        var postsById = {};
        var pendingCommentFocus = false;
        var roundupContext = null;
        var pendingMirror = null;
        var resumedDraft = takeResumeDraft();
        var stopLandingGuard = function () {};
        if (!resumedDraft) {
            clearDraft();
            stopLandingGuard = guardComposer([field, startBody]);
        } else {
            stopLandingGuard = guardComposer([field, startBody], function (input) {
                if (resumedDraft.kind === "topic" && input === startBody) return resumedDraft.body || "";
                if (resumedDraft.kind === "comment" && !resumedDraft.parent_post_id && input === field) return resumedDraft.body || "";
                return "";
            });
        }

        function fit() {
            fitDocksideCard(root);
        }

        function paintMe() {
            if (!meAvatar) return;
            meAvatar.textContent = "";
            if (!me.signed_in) return;
            var author = presentAuthor(me);
            if (author && author.photo_url) {
                var img = document.createElement("img");
                img.alt = "";
                img.src = author.photo_url;
                img.addEventListener("error", function () {
                    img.remove();
                    meAvatar.textContent = initials(author);
                });
                meAvatar.appendChild(img);
                return;
            }
            meAvatar.textContent = initials(author);
            setCommentPlaceholder();
        }

        function meFace() {
            var face = document.createElement("span");
            face.className = "dockside-avatar dockside-avatar--me";
            face.setAttribute("aria-hidden", "true");
            if (!me.signed_in) return face;
            var author = presentAuthor(me);
            if (author && author.photo_url) {
                var img = document.createElement("img");
                img.alt = "";
                img.src = author.photo_url;
                img.addEventListener("error", function () {
                    img.remove();
                    face.textContent = initials(author);
                });
                face.appendChild(img);
                return face;
            }
            face.textContent = initials(author);
            return face;
        }

        function setCommentPlaceholder() {
            if (!field) return;
            var name = commentAsName();
            field.placeholder = name ? ("Comment as " + name) : "Write a comment";
        }

        function revealInline(hold) {
            if (!scroll || !hold || !scroll.contains(hold)) return;
            showLatestTwo(scroll);
            var viewTop = scroll.getBoundingClientRect().top;
            var box = hold.getBoundingClientRect();
            var overflow = box.bottom - (viewTop + scroll.clientHeight);
            if (overflow > 0) scroll.style.maxHeight = (scroll.clientHeight + overflow + 6) + "px";
            var nextTop = hold.getBoundingClientRect().top;
            if (nextTop < viewTop) scroll.scrollTop += nextTop - viewTop - 4;
        }

        function openInline(post, mount, indented) {
            if (!mount) return;
            var existing = root.querySelector(".dockside-inline-hold");
            if (existing && existing.dataset.forPost === String(post.post_id)) {
                existing.remove();
                showLatestTwo(scroll);
                fit();
                return;
            }
            if (existing) existing.remove();
            var shown = presentAuthor(post.author);
            var hold = document.createElement("div");
            hold.className = "dockside-inline-hold" + (indented ? " is-under-comment" : "");
            hold.dataset.forPost = String(post.post_id);
            var inline = document.createElement("form");
            inline.className = "dockside-inline-reply";
            inline.action = "/dockside.html";
            inline.method = "get";
            var input = document.createElement("input");
            input.type = "text";
            input.maxLength = 2000;
            input.placeholder = "Reply to " + ((shown && shown.display_name) || "sailor");
            input.setAttribute("aria-label", input.placeholder);
            input.autocomplete = "off";
            var button = document.createElement("button");
            button.type = "submit";
            button.className = "dockside-post";
            button.textContent = "Post";
            inline.appendChild(meFace());
            inline.appendChild(input);
            inline.appendChild(button);
            hold.appendChild(inline);
            mount.appendChild(hold);
            inline.addEventListener("submit", function (event) {
                event.preventDefault();
                sendComment((input.value || "").trim(), post.post_id, hold);
            });
            input.focus();
            revealInline(hold);
            fit();
            return input;
        }

        function showStart(open) {
            if (startOpen) startOpen.hidden = !!open;
            if (startForm) startForm.hidden = !open;
            fit();
        }

        function noteError(mount, message) {
            if (!mount) return;
            var old = mount.querySelector(".dockside-error");
            if (old) old.remove();
            var err = document.createElement("p");
            err.className = "dockside-error";
            err.textContent = message;
            mount.appendChild(err);
        }

        function splitThread(posts) {
            var list = (posts || []).slice().sort(function (a, b) {
                var at = String(a.created_at || "");
                var bt = String(b.created_at || "");
                if (at < bt) return -1;
                if (at > bt) return 1;
                return (a.post_id || 0) - (b.post_id || 0);
            });
            var byId = {};
            list.forEach(function (post) { byId[post.post_id] = post; });
            var originalPost = null;
            list.forEach(function (post) {
                if (!originalPost && !post.parent_post_id) originalPost = post;
            });
            function displayRoot(post) {
                var cur = post;
                var guard = 0;
                while (cur && cur.parent_post_id && guard < 6) {
                    guard += 1;
                    var parent = byId[cur.parent_post_id];
                    if (!parent) break;
                    if (originalPost && parent.post_id === originalPost.post_id) return cur;
                    if (!parent.parent_post_id) return parent;
                    cur = parent;
                }
                return cur;
            }
            var roots = [];
            var replies = {};
            list.forEach(function (post) {
                if (originalPost && post.post_id === originalPost.post_id) return;
                var rootPost = displayRoot(post);
                if (!rootPost) return;
                if (rootPost.post_id === post.post_id) {
                    roots.push(post);
                    return;
                }
                if (!replies[rootPost.post_id]) replies[rootPost.post_id] = [];
                replies[rootPost.post_id].push(post);
            });
            return { originalPost: originalPost, roots: roots, replies: replies };
        }

        function paintTopic(topic) {
            topicId = topic.topic_id;
            if (emptyBox) emptyBox.hidden = true;
            topicBox.hidden = false;
            if (form) form.hidden = false;
            if (subjectEl) subjectEl.hidden = true;
            setCommentPlaceholder();
            var parts = splitThread(topic.posts);
            originalEl.textContent = "";
            scroll.textContent = "";
            postsById = {};
            (topic.posts || []).forEach(function (post) { postsById[post.post_id] = post; });
            if (parts.originalPost) originalEl.appendChild(cardPost(parts.originalPost, [], openInline));
            parts.roots.forEach(function (comment) {
                scroll.appendChild(cardPost(comment, parts.replies[comment.post_id] || [], openInline));
            });
            showLatestTwo(scroll);
            paintMe();
            fit();
            if (pendingMirror && pendingMirror.headline) {
                lockRoundupChip(pendingMirror);
            }
            if (pendingCommentFocus) {
                pendingCommentFocus = false;
                if (!me.signed_in && !guestsMayPost()) {
                    goLogin(null);
                    return;
                }
                if (root) root.scrollIntoView({ block: "center" });
                if (field) field.focus();
            }
        }

        function showLatestTwo(scroll) {
            var nodes = scroll.querySelectorAll(":scope > .dockside-comment");
            scroll.style.maxHeight = "";
            if (!nodes.length) return;
            if (nodes.length <= 2) {
                scroll.scrollTop = 0;
                return;
            }
            var start = nodes[nodes.length - 2];
            var last = nodes[nodes.length - 1];
            var height = last.getBoundingClientRect().bottom - start.getBoundingClientRect().top;
            scroll.style.maxHeight = Math.ceil(height + 4) + "px";
            scroll.scrollTop = start.getBoundingClientRect().top - scroll.getBoundingClientRect().top + scroll.scrollTop;
        }

        function showEmpty(message) {
            topicId = null;
            topicBox.hidden = true;
            if (form) form.hidden = true;
            if (emptyBox) emptyBox.hidden = false;
            var line = emptyBox ? emptyBox.querySelector("p") : null;
            if (line) line.textContent = message || "No discussion yet.";
            showStart(false);
            fit();
        }

        function showRoundupLink(info) {
            // Legacy big heading above compose created empty @ threads — remove it.
            var link = topicBox.querySelector(".dockside-roundup-link");
            if (link) link.remove();
            if (info && info.key) lockRoundupChip(info);
            else if (!info) clearRoundupChip();
        }

        function ensureComposeField() {
            if (!form || !field) return null;
            var wrap = form.querySelector(".dockside-compose-field");
            if (!wrap) {
                wrap = document.createElement("div");
                wrap.className = "dockside-compose-field";
                field.parentNode.insertBefore(wrap, field);
                wrap.appendChild(field);
            }
            var chip = wrap.querySelector(".dockside-at-chip");
            if (!chip) {
                chip = document.createElement("a");
                chip.className = "dockside-at-chip";
                chip.hidden = true;
                chip.tabIndex = -1;
                chip.addEventListener("click", function (event) {
                    // Matching tag only — open Roundup, never edit/remove from compose.
                    event.stopPropagation();
                });
                wrap.insertBefore(chip, field);
            }
            return chip;
        }

        function lockRoundupChip(info) {
            if (!info || !info.key || !info.headline) return;
            registerRoundupLeader(info);
            pendingMirror = {
                key: info.key,
                url: info.url || ("/sailing-roundup/issues/" + info.key + "/"),
                headline: String(info.headline || "").replace(/\s+/g, " ").trim()
            };
            var chip = ensureComposeField();
            if (!chip || !field) return;
            chip.hidden = false;
            chip.href = pendingMirror.url;
            chip.textContent = compactAtLabel(pendingMirror.headline);
            chip.title = "@" + pendingMirror.headline;
            // Poster can only type after the locked matching tag.
            var typed = (field.value || "").trim();
            Object.keys(roundupLeaders()).forEach(function (known) {
                if (typed.toLowerCase().indexOf(known.toLowerCase()) === 0) {
                    typed = typed.slice(known.length).trim();
                }
            });
            field.value = typed;
            field.placeholder = "Write a comment";
            form.classList.add("has-roundup-chip");
            stopLandingGuard();
            stopLandingGuard = guardComposer([field, startBody], function (input) {
                return input === field ? field.value : "";
            });
        }

        function clearRoundupChip() {
            pendingMirror = null;
            var chip = form && form.querySelector(".dockside-at-chip");
            if (chip) {
                chip.hidden = true;
                chip.removeAttribute("href");
                chip.textContent = "";
                chip.removeAttribute("title");
            }
            if (form) form.classList.remove("has-roundup-chip");
        }

        function findRoundupRoot(info) {
            if (!info || !info.key) return null;
            var tag = "@" + String(info.headline || "").replace(/\s+/g, " ").trim();
            var found = null;
            Object.keys(postsById).forEach(function (id) {
                var post = postsById[id];
                if (!post || post.parent_post_id) return;
                var body = String(post.body || "");
                var hit = leadingRoundupTag(body);
                var sameTag = hit && hit.tag && tag && hit.tag.toLowerCase() === tag.toLowerCase();
                var sameKey = hit && hit.info && hit.info.key === info.key;
                if (!sameTag && !sameKey && body.toLowerCase().indexOf(tag.toLowerCase()) !== 0) return;
                if (!found || String(post.created_at || "") < String(found.created_at || "")) found = post;
            });
            return found;
        }

        function typedCommentOnly() {
            return ((field && field.value) || "").trim();
        }

        function buildRoundupBody(info, typed, asReply) {
            var text = String(typed || "").trim();
            if (!text) return "";
            if (asReply) return text;
            return "@" + String(info.headline || "").replace(/\s+/g, " ").trim() + " " + text;
        }

        function showRoundupEmpty() {
            if (emptyBox) emptyBox.hidden = true;
            topicBox.hidden = false;
            if (form) form.hidden = false;
            if (subjectEl) subjectEl.hidden = true;
            originalEl.textContent = "";
            scroll.textContent = "";
            var note = document.createElement("p");
            note.className = "dockside-empty";
            note.textContent = "No comments yet.";
            scroll.appendChild(note);
            setCommentPlaceholder();
            paintMe();
            fit();
        }

        function loadRoundup(info, opts) {
            if (!info || !info.key) return;
            opts = opts || {};
            roundupContext = info;
            registerRoundupLeader(info);
            var orphan = topicBox.querySelector(".dockside-roundup-link");
            if (orphan) orphan.remove();
            if (emptyBox) emptyBox.hidden = true;
            topicBox.hidden = false;
            if (form) form.hidden = false;
            api("/api/dockside/roundup/" + encodeURIComponent(info.key) + "/chat?headline=" + encodeURIComponent(info.headline || "")).then(function (data) {
                if (!data || data._status !== 200) {
                    noteError(scroll, (data && data.detail) || "Comments could not be loaded");
                    return;
                }
                roundupContext = {
                    key: data.issue_key || info.key,
                    url: data.url || info.url,
                    headline: data.headline || info.headline
                };
                registerRoundupLeader(roundupContext);
                if (data.topic) paintTopic(data.topic);
                else {
                    topicId = null;
                    showRoundupEmpty();
                }
                if (opts.scroll) {
                    if (root) root.scrollIntoView({ block: "center" });
                    if (field) field.focus();
                }
                fit();
            });
        }

        paintMe();
        var fixedKey = root.getAttribute("data-roundup-key") || "";
        if (fixedKey) {
            loadRoundup({
                key: fixedKey,
                url: root.getAttribute("data-roundup-url") || "",
                headline: root.getAttribute("data-roundup-headline") || ""
            }, { scroll: false });
        } else if (resumedDraft && resumedDraft.kind === "roundup" && resumedDraft.issue_key) {
            loadRoundup({
                key: resumedDraft.issue_key,
                url: resumedDraft.url || "",
                headline: resumedDraft.headline || ""
            }, { scroll: true });
            if (field) field.value = resumedDraft.body || "";
        } else api("/api/dockside/current").then(function (data) {
            if (!data || data._status !== 200) {
                showEmpty("Dockside Chat is unavailable.");
                if (startOpen) startOpen.hidden = true;
                return;
            }
            if (!data.topic) {
                showEmpty("No discussion yet.");
                if (resumedDraft && resumedDraft.kind === "topic") {
                    if (startSubject) startSubject.value = resumedDraft.subject || "";
                    if (startBody) startBody.value = resumedDraft.body || "";
                    showStart(true);
                }
                return;
            }
            paintTopic(data.topic);
            var commentDraft = resumedDraft;
            if (commentDraft && commentDraft.kind === "comment" && (!commentDraft.topic_id || commentDraft.topic_id === topicId)) {
                if (commentDraft.parent_post_id) {
                    var mount = root.querySelector('[data-post-id="' + commentDraft.parent_post_id + '"]');
                    var target = postsById[commentDraft.parent_post_id];
                    if (mount && target) {
                        var input = openInline(target, mount, mount.classList.contains("dockside-comment"));
                        if (input) {
                            input.value = commentDraft.body || "";
                            guardComposer([input], function () { return commentDraft.body || ""; });
                        }
                    }
                } else if (field) {
                    field.value = commentDraft.body || "";
                }
            }
        }).catch(function () {
            showEmpty("Dockside Chat is unavailable.");
            if (startOpen) startOpen.hidden = true;
        });

        if (startOpen) {
            startOpen.addEventListener("click", function () {
                showStart(true);
                if (startSubject) startSubject.focus();
            });
        }
        if (startForm) {
            startForm.addEventListener("submit", function (event) {
                event.preventDefault();
                var body = ((startBody && startBody.value) || "").trim();
                if (!body) {
                    noteError(startForm, "Write the first post.");
                    return;
                }
                var draft = { kind: "topic", body: body };
                if (!me.signed_in) {
                    goLogin(draft);
                    return;
                }
                api("/api/dockside/topics", {
                    method: "POST",
                    body: JSON.stringify({ body: body })
                }).then(function (data) {
                    if (data._status === 401) {
                        goLogin(draft);
                        return;
                    }
                    if (!data || data._status !== 200 || !data.topic_id) {
                        noteError(startForm, (data && data.detail) || "Discussion was not saved");
                        return;
                    }
                    clearDraft();
                    resumedDraft = null;
                    stopLandingGuard();
                    if (field) field.value = "";
                    if (startBody) startBody.value = "";
                    stopLandingGuard = guardComposer([field, startBody]);
                    paintTopic(data);
                });
            });
        }
            function mirrorFromBody(body, parent) {
            var hit = pendingMirror;
            if (hit && hit.key && body.indexOf("@" + (hit.headline || "")) >= 0) return hit;
            var leaders = roundupLeaders();
            var tags = Object.keys(leaders).sort(function (a, b) { return b.length - a.length; });
            for (var i = 0; i < tags.length; i += 1) {
                if (body.indexOf(tags[i]) >= 0) return leaders[tags[i]];
            }
            if (parent && parent.body) {
                for (var j = 0; j < tags.length; j += 1) {
                    if (String(parent.body).indexOf(tags[j]) >= 0) return leaders[tags[j]];
                }
            }
            return null;
        }

        function sendComment(body, parent, errorMount, mirrorInfo) {
            if (!body) return;
            if (roundupContext && roundupContext.key && fixedKey) {
                var roundupDraft = {
                    kind: "roundup",
                    issue_key: roundupContext.key,
                    headline: roundupContext.headline || "",
                    url: roundupContext.url || "",
                    parent_post_id: parent || null,
                    body: body
                };
                if (!me.signed_in && !guestsMayPost()) {
                    goLogin(roundupDraft);
                    return;
                }
                api("/api/dockside/roundup/" + encodeURIComponent(roundupContext.key) + "/posts", {
                    method: "POST",
                    body: JSON.stringify({
                        body: body,
                        parent_post_id: parent || null,
                        headline: roundupContext.headline || ""
                    })
                }).then(function (data) {
                    if (data._status === 401) {
                        goLogin(roundupDraft);
                        return;
                    }
                    if (!data || data._status !== 200 || !data.topic) {
                        noteError(errorMount || scroll, (data && data.detail) || "Comment was not saved");
                        return;
                    }
                    clearDraft();
                    resumedDraft = null;
                    stopLandingGuard();
                    if (field) {
                        field.value = "";
                        field.placeholder = "Write a comment";
                    }
                    stopLandingGuard = guardComposer([field, startBody]);
                    paintTopic(data.topic);
                });
                return;
            }
            if (!topicId) return;
            var parentPost = parent ? postsById[parent] : null;
            var mirror = mirrorInfo || mirrorFromBody(body, parentPost);
            if (mirror && mirror.key && !parent) {
                var existingRoot = findRoundupRoot(mirror);
                if (existingRoot) parent = existingRoot.post_id;
            }
            var draft = {
                kind: "comment",
                topic_id: topicId,
                parent_post_id: parent || null,
                body: body,
                issue_key: mirror && mirror.key,
                headline: mirror && mirror.headline
            };
            if (!me.signed_in && !guestsMayPost()) {
                goLogin(draft);
                return;
            }
            var payload = { body: body, parent_post_id: parent || null };
            if (mirror && mirror.key) {
                payload.issue_key = mirror.key;
                payload.headline = mirror.headline || "";
            }
            api("/api/dockside/topics/" + topicId + "/posts", {
                method: "POST",
                body: JSON.stringify(payload)
            }).then(function (data) {
                if (data._status === 401) {
                    goLogin(draft);
                    return;
                }
                if (!data || data._status !== 200 || !data.topic) {
                    noteError(errorMount || scroll, (data && data.detail) || "Comment was not saved");
                    return;
                }
                clearDraft();
                resumedDraft = null;
                clearRoundupChip();
                stopLandingGuard();
                if (field) {
                    field.value = "";
                    field.placeholder = "Write a comment";
                }
                stopLandingGuard = guardComposer([field, startBody]);
                paintTopic(data.topic);
            });
        }

        if (form && field) {
            form.addEventListener("submit", function (event) {
                event.preventDefault();
                var typed = typedCommentOnly();
                var mirror = pendingMirror;
                if (mirror && mirror.key) {
                    if (!typed) {
                        noteError(scroll, "Write a comment after @");
                        if (field) field.focus();
                        return;
                    }
                    var root = findRoundupRoot(mirror);
                    var parentId = root ? root.post_id : null;
                    var body = buildRoundupBody(mirror, typed, !!parentId);
                    sendComment(body, parentId, scroll, mirror);
                    return;
                }
                if (!typed) return;
                sendComment(typed, null, scroll);
            });
        }
        mountPublicToggle(root.querySelector(".dockside-titles"));
        function openLandingLeader(info) {
            if (!info || !info.key) return;
            lockRoundupChip(info);
            if (emptyBox) emptyBox.hidden = true;
            topicBox.hidden = false;
            if (form) form.hidden = false;
            var orphan = topicBox.querySelector(".dockside-roundup-link");
            if (orphan) orphan.remove();
            if (!topicId) {
                api("/api/dockside/current").then(function (data) {
                    if (data && data.topic) paintTopic(data.topic);
                });
            }
            try {
                var top = root.getBoundingClientRect().top + window.pageYOffset - 12;
                window.scrollTo(0, Math.max(0, top));
            } catch (errScroll) {
                if (root) root.scrollIntoView({ block: "start" });
            }
            if (field) {
                field.focus({ preventScroll: true });
            }
            fit();
        }

        function goToIssueChat() {
            if (!root) return;
            try {
                var top = root.getBoundingClientRect().top + window.pageYOffset - 12;
                window.scrollTo(0, Math.max(0, top));
            } catch (err) {
                root.scrollIntoView({ block: "start" });
            }
            if (field) {
                field.focus({ preventScroll: true });
            }
        }

        window.docksideOpenComment = function (info) {
            // Roundup issue page: Comment goes to this page's chat only when clicked.
            if (fixedKey) {
                goToIssueChat();
                return;
            }
            if (info && info.key) {
                openLandingLeader(info);
                return;
            }
            if (form && form.hidden) {
                pendingCommentFocus = true;
                if (root) root.scrollIntoView({ block: "center" });
                return;
            }
            if (root) root.scrollIntoView({ block: "center" });
            if (field) field.focus();
        };

        function flushCommentQueue() {
            var queued = (window.__docksideCommentQueue || []).splice(0);
            var stored = null;
            try {
                stored = sessionStorage.getItem("dockside_roundup_comment");
                if (stored) sessionStorage.removeItem("dockside_roundup_comment");
            } catch (errStore) {}
            if (stored) {
                try { queued.push(JSON.parse(stored)); } catch (errParse) {}
            }
            // Never auto-open/focus chat when landing on a Roundup URL.
            if (fixedKey) return;
            queued.forEach(function (info) {
                if (info && info.key) openLandingLeader(info);
            });
        }
        flushCommentQueue();
        if (!fixedKey) {
            window.setTimeout(flushCommentQueue, 300);
            window.setTimeout(flushCommentQueue, 1200);
        }

        if (location.hash === "#dockside-comment" || location.hash === "#dockside-landing") {
            try {
                history.replaceState(null, "", location.pathname + location.search);
            } catch (err) {}
            // Hash must not auto-jump the Roundup issue page either.
            if (!fixedKey) pendingCommentFocus = true;
        }
        window.addEventListener("resize", fit);
        window.addEventListener("load", fit);
        window.requestAnimationFrame(function () { window.requestAnimationFrame(fit); });
    }

    function params() {
        return new URLSearchParams(location.search);
    }

    function rememberSort(sort, dir) {
        try { localStorage.setItem(SORT_KEY, sort + ":" + dir); } catch (err) {}
    }

    function savedSort() {
        try {
            var raw = localStorage.getItem(SORT_KEY) || "";
            var bits = raw.split(":");
            if (bits.length === 2) return { sort: bits[0], dir: bits[1] };
        } catch (err) {}
        return null;
    }

    function bootPage() {
        var page = document.getElementById("dockside-page");
        if (!page) return;
        var search = params();
        var stored = savedSort();
        var sort = search.get("sort") || (stored && stored.sort) || "updated";
        var dir = search.get("dir") || (stored && stored.dir) || "desc";
        var q = "";
        var topic = search.get("topic") || "";
        var searchInput = document.getElementById("dockside-search");
        var feed = document.getElementById("dockside-feed");
        var newForm = document.getElementById("dockside-new-topic");
        var newBody = document.getElementById("dockside-new-body");
        var newError = document.getElementById("dockside-new-error");
        var notes = document.getElementById("dockside-notes");
        var pageAvatar = document.getElementById("dockside-page-avatar");
        if (!feed || !newForm || !newBody) return;
        var resumedDraft = takeResumeDraft();
        try {
            var clean = new URL(window.location.href);
            if (clean.searchParams.has("q")) {
                clean.searchParams.delete("q");
                var cleaned = clean.searchParams.toString();
                history.replaceState(null, "", clean.pathname + (cleaned ? "?" + cleaned : "") + clean.hash);
            }
        } catch (err) {}
        var stopPageGuard = function () {};
        if (!resumedDraft) clearDraft();
        stopPageGuard = guardComposer([newBody], resumedDraft && resumedDraft.kind === "topic"
            ? function () { return resumedDraft.body || ""; }
            : null);

        function paintPageAvatar() {
            if (!pageAvatar) return;
            pageAvatar.textContent = "";
            if (!me.signed_in) return;
            var author = presentAuthor(me);
            if (author && author.photo_url) {
                var img = document.createElement("img");
                img.alt = "";
                img.src = author.photo_url;
                img.addEventListener("error", function () {
                    img.remove();
                    pageAvatar.textContent = initials(author);
                });
                pageAvatar.appendChild(img);
                return;
            }
            pageAvatar.textContent = initials(author);
        }

        function pageFace() {
            var face = document.createElement("span");
            face.className = "dockside-avatar dockside-avatar--me";
            face.setAttribute("aria-hidden", "true");
            if (!me.signed_in) return face;
            var author = presentAuthor(me);
            if (author && author.photo_url) {
                var img = document.createElement("img");
                img.alt = "";
                img.src = author.photo_url;
                face.appendChild(img);
                return face;
            }
            face.textContent = initials(author);
            return face;
        }

        function pageParts(posts) {
            var list = (posts || []).slice().sort(function (a, b) {
                var at = String(a.created_at || "");
                var bt = String(b.created_at || "");
                if (at < bt) return -1;
                if (at > bt) return 1;
                return (a.post_id || 0) - (b.post_id || 0);
            });
            var byId = {};
            list.forEach(function (post) { byId[post.post_id] = post; });
            var originalPost = null;
            list.forEach(function (post) {
                if (!originalPost && !post.parent_post_id) originalPost = post;
            });
            function displayRoot(post) {
                var cur = post;
                var guard = 0;
                while (cur && cur.parent_post_id && guard < 6) {
                    guard += 1;
                    var parent = byId[cur.parent_post_id];
                    if (!parent) break;
                    if (originalPost && parent.post_id === originalPost.post_id) return cur;
                    if (!parent.parent_post_id) return parent;
                    cur = parent;
                }
                return cur;
            }
            var roots = [];
            var replies = {};
            var seen = {};
            list.forEach(function (post) {
                if (seen[post.post_id]) return;
                seen[post.post_id] = true;
                if (originalPost && post.post_id === originalPost.post_id) return;
                var rootPost = displayRoot(post);
                if (!rootPost) return;
                if (rootPost.post_id === post.post_id) {
                    roots.push(post);
                    return;
                }
                if (!replies[rootPost.post_id]) replies[rootPost.post_id] = [];
                replies[rootPost.post_id].push(post);
            });
            return { originalPost: originalPost, roots: roots, replies: replies };
        }

        function loadNotes() {
            if (!me.signed_in || !notes) return;
            api("/api/dockside/notifications").then(function (data) {
                notes.textContent = "";
                (data.notifications || []).forEach(function (item) {
                    var row = document.createElement("div");
                    row.className = "dockside-note";
                    var text = document.createElement("span");
                    text.textContent = (item.actor_name || "A sailor") + " added a " + item.kind + " on " + (item.subject || "a topic");
                    var link = document.createElement("a");
                    link.href = "/dockside.html?topic=" + encodeURIComponent(item.topic_id);
                    link.textContent = "Open";
                    row.appendChild(text);
                    row.appendChild(link);
                    notes.appendChild(row);
                });
            });
        }

        function openInline(topicId, post, mount) {
            if (!mount) return null;
            var existing = page.querySelector(".dockside-inline-hold");
            if (existing && existing.dataset.forPost === String(post.post_id)) {
                existing.remove();
                return null;
            }
            if (existing) existing.remove();
            var shown = presentAuthor(post.author);
            var hold = document.createElement("div");
            hold.className = "dockside-inline-hold";
            hold.dataset.forPost = String(post.post_id);
            var inline = document.createElement("form");
            inline.className = "dockside-inline-reply";
            inline.action = "/dockside.html";
            inline.method = "get";
            var input = document.createElement("input");
            input.type = "text";
            input.maxLength = 2000;
            input.placeholder = "Reply to " + ((shown && shown.display_name) || "sailor");
            input.setAttribute("aria-label", input.placeholder);
            input.autocomplete = "off";
            var button = document.createElement("button");
            button.type = "submit";
            button.className = "dockside-post";
            button.textContent = "Post";
            inline.appendChild(pageFace());
            inline.appendChild(input);
            inline.appendChild(button);
            hold.appendChild(inline);
            mount.appendChild(hold);
            inline.addEventListener("submit", function (event) {
                event.preventDefault();
                sendReply(topicId, post.post_id, (input.value || "").trim(), hold);
            });
            input.focus();
            return input;
        }

        function sendReply(topicId, parentId, body, hold) {
            if (!body || !topicId) return;
            var draft = { kind: "comment", topic_id: Number(topicId), parent_post_id: parentId, body: body };
            if (!me.signed_in && !guestsMayPost()) {
                goLogin(draft);
                return;
            }
            api("/api/dockside/topics/" + encodeURIComponent(topicId) + "/posts", {
                method: "POST",
                body: JSON.stringify({ body: body, parent_post_id: parentId })
            }).then(function (data) {
                if (data._status === 401) {
                    goLogin(draft);
                    return;
                }
                if (!data || data._status !== 200) {
                    var err = document.createElement("p");
                    err.className = "dockside-error";
                    err.textContent = (data && data.detail) || "Comment was not saved";
                    hold.appendChild(err);
                    return;
                }
                clearDraft();
                resumedDraft = null;
                loadFeed();
                loadNotes();
            });
        }

        function renderTopic(detail) {
            var block = document.createElement("section");
            block.className = "dockside-topic";
            block.id = "dockside-topic-" + detail.topic_id;
            var parts = pageParts(detail.posts);
            function onReply(post, mount) {
                openInline(detail.topic_id, post, mount);
            }
            if (parts.originalPost) block.appendChild(cardPost(parts.originalPost, [], onReply));
            parts.roots.forEach(function (comment) {
                block.appendChild(cardPost(comment, parts.replies[comment.post_id] || [], onReply));
            });
            if (me.signed_in) {
                var tools = document.createElement("div");
                tools.className = "dockside-tools";
                var mute = document.createElement("button");
                mute.type = "button";
                mute.className = "dockside-mini";
                var muted = detail.following && detail.following.muted;
                mute.textContent = muted ? "Unmute" : "Mute";
                mute.addEventListener("click", function () {
                    var next = mute.textContent !== "Unmute";
                    api("/api/dockside/topics/" + encodeURIComponent(detail.topic_id) + "/follow", {
                        method: "POST",
                        body: JSON.stringify({ muted: next })
                    }).then(function (data) {
                        if (data._status === 401) {
                            goLogin(null);
                            return;
                        }
                        mute.textContent = data.muted ? "Unmute" : "Mute";
                    });
                });
                tools.appendChild(mute);
                block.appendChild(tools);
            }
            return block;
        }

        function loadFeed() {
            var path = "/api/dockside/topics?sort=" + encodeURIComponent(sort) + "&dir=" + encodeURIComponent(dir);
            if (q) path += "&q=" + encodeURIComponent(q);
            api(path).then(function (data) {
                feed.textContent = "";
                if (!data || data._status !== 200) {
                    var failed = document.createElement("p");
                    failed.className = "dockside-error";
                    failed.textContent = (data && data.detail) || "Posts could not be loaded";
                    feed.appendChild(failed);
                    return;
                }
                var rows = data.topics || [];
                if (!rows.length) {
                    var empty = document.createElement("p");
                    empty.className = "dockside-empty";
                    empty.textContent = q ? "No posts match that search." : "No posts yet.";
                    feed.appendChild(empty);
                    return;
                }
                Promise.all(rows.map(function (row) {
                    return api("/api/dockside/topics/" + encodeURIComponent(row.topic_id));
                })).then(function (details) {
                    feed.textContent = "";
                    details.forEach(function (detail) {
                        if (!detail || detail._status === 404 || !detail.topic_id) return;
                        feed.appendChild(renderTopic(detail));
                    });
                    if (!feed.children.length) {
                        var missing = document.createElement("p");
                        missing.className = "dockside-empty";
                        missing.textContent = "No posts yet.";
                        feed.appendChild(missing);
                        return;
                    }
                    if (topic) {
                        var focus = document.getElementById("dockside-topic-" + topic);
                        if (focus) focus.scrollIntoView({ block: "start" });
                    }
                    restoreDraft();
                }).catch(function () {
                    feed.textContent = "";
                    var failed = document.createElement("p");
                    failed.className = "dockside-error";
                    failed.textContent = "Posts could not be loaded";
                    feed.appendChild(failed);
                });
            });
        }

        var searchForm = document.getElementById("dockside-search-form");
        if (searchForm && searchInput) {
            searchForm.addEventListener("submit", function (event) {
                event.preventDefault();
                q = (searchInput.value || "").trim();
                loadFeed();
            });
            searchInput.addEventListener("input", function () {
                q = (searchInput.value || "").trim();
                if (q.length === 1) return;
                loadFeed();
            });
        }

        newForm.addEventListener("submit", function (event) {
            event.preventDefault();
            if (newError) newError.textContent = "";
            var body = (newBody.value || "").trim();
            if (!body) {
                if (newError) newError.textContent = "Write a post.";
                return;
            }
            var draft = { kind: "topic", body: body };
            if (!me.signed_in && !guestsMayPost()) {
                goLogin(draft);
                return;
            }
            if (!me.signed_in) {
                api("/api/dockside/current").then(function (current) {
                    var topicId = current && current.topic && current.topic.topic_id;
                    if (!topicId) {
                        if (newError) newError.textContent = "Sign in to start a discussion.";
                        return;
                    }
                    api("/api/dockside/topics/" + encodeURIComponent(topicId) + "/posts", {
                        method: "POST",
                        body: JSON.stringify({ body: body })
                    }).then(function (data) {
                        if (data._status === 401) {
                            goLogin(draft);
                            return;
                        }
                        if (!data || data._status !== 200) {
                            if (newError) newError.textContent = (data && data.detail) || "Comment was not saved";
                            return;
                        }
                        clearDraft();
                        resumedDraft = null;
                        stopPageGuard();
                        newBody.value = "";
                        stopPageGuard = guardComposer([newBody]);
                        loadFeed();
                    });
                });
                return;
            }
            api("/api/dockside/topics", {
                method: "POST",
                body: JSON.stringify({ body: body })
            }).then(function (data) {
                if (data._status === 401) {
                    goLogin(draft);
                    return;
                }
                if (data._status !== 200) {
                    if (newError) newError.textContent = data.detail || "Post was not saved";
                    return;
                }
                clearDraft();
                resumedDraft = null;
                stopPageGuard();
                newBody.value = "";
                stopPageGuard = guardComposer([newBody]);
                loadFeed();
                loadNotes();
            });
        });

        var draftApplied = false;
        function restoreDraft() {
            var draft = resumedDraft;
            if (draftApplied || !draft) return;
            draftApplied = true;
            if (draft.kind === "topic") {
                newBody.value = draft.body || "";
                stopPageGuard();
                stopPageGuard = guardComposer([newBody], function () { return draft.body || ""; });
                return;
            }
            if (draft.kind !== "comment" || !draft.topic_id || !draft.parent_post_id) return;
            var mount = feed.querySelector('#dockside-topic-' + draft.topic_id + ' [data-post-id="' + draft.parent_post_id + '"]');
            if (!mount) return;
            var posts = mount.closest(".dockside-topic");
            if (!posts) return;
            var nameNode = mount.querySelector(".dockside-name");
            var input = openInline(draft.topic_id, {
                post_id: draft.parent_post_id,
                author: { display_name: nameNode ? nameNode.textContent : "sailor" }
            }, mount);
            if (input) {
                input.value = draft.body || "";
                guardComposer([input], function () { return draft.body || ""; });
            }
        }

        paintPageAvatar();
        mountPublicToggle(page.querySelector(".dockside-page-bar"));
        loadFeed();
        loadNotes();
    }

    function bootBell() {
        var bell = document.getElementById("dev1-avatar-bell-btn");
        if (!bell || bell.dataset.docksideBound) return;
        bell.dataset.docksideBound = "1";
        var panel = document.createElement("div");
        panel.id = "dockside-notify-panel";
        panel.hidden = true;
        document.body.appendChild(panel);
        var badge = bell.querySelector(".sa-avatar-bell-badge");

        function paint(data) {
            var unread = data && data.unread ? data.unread : 0;
            if (badge) {
                badge.textContent = unread > 9 ? "9+" : String(unread);
                badge.style.display = unread ? "block" : "none";
            }
            panel.textContent = "";
            var items = (data && data.notifications) || [];
            if (!items.length) {
                var empty = document.createElement("p");
                empty.className = "dockside-empty";
                empty.textContent = "No notifications.";
                panel.appendChild(empty);
                return;
            }
            items.forEach(function (item) {
                var link = document.createElement("a");
                link.className = "dockside-note";
                link.href = "/dockside.html?topic=" + encodeURIComponent(item.topic_id);
                link.textContent = (item.actor_name || "A sailor") + " added a " + item.kind + " on " + (item.subject || "a topic");
                panel.appendChild(link);
            });
        }

        function refresh() {
            if (!me.signed_in) return;
            api("/api/dockside/notifications").then(function (data) {
                if (data._status === 200) paint(data);
            });
        }

        bell.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            if (!me.signed_in) {
                goLogin(null);
                return;
            }
            panel.hidden = !panel.hidden;
            if (!panel.hidden) {
                api("/api/dockside/notifications/read", {
                    method: "POST",
                    body: JSON.stringify({ all: true })
                }).then(refresh);
            }
        });
        refresh();
        window.setInterval(refresh, 60000);
    }

    api("/api/dockside/me").then(function (data) {
        if (data && data._status === 200) me = data;
        bootLanding();
        bootPage();
        bootBell();
    }).catch(function () {
        bootLanding();
        bootPage();
        bootBell();
    });
})();
