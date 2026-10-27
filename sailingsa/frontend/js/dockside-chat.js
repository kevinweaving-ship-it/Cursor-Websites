(function () {
    if (window.__docksideBoot) return;
    window.__docksideBoot = true;

    var DRAFT_KEY = "dockside_draft";
    var SORT_KEY = "dockside_topic_sort";
    var me = { signed_in: false };

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

    function goLogin(draft) {
        if (draft) {
            try { sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft)); } catch (err) {}
        }
        try { sessionStorage.setItem("auth_returnTo", window.location.href); } catch (err) {}
        var headerBtn = document.getElementById("blank69HubSignInOnly");
        if (headerBtn) {
            headerBtn.click();
            return;
        }
        window.location.href = (window.location.origin || "") + "/login.html";
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

    function authorNode(author, card) {
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
        var name = ((author && author.display_name) || "").replace(/[^A-Za-z\s]/g, " ").trim();
        var parts = name.split(/\s+/).filter(Boolean);
        if (!parts.length) return "S";
        if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }

    function avatarNode(author) {
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

    function cardPost(post, replies, onReply) {
        var wrap = document.createElement("article");
        wrap.className = "dockside-comment";
        var row = document.createElement("div");
        row.className = "dockside-person";
        row.appendChild(avatarNode(post.author));
        var text = document.createElement("div");
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
        body.textContent = post.body || "";
        text.appendChild(meta);
        text.appendChild(body);
        if (onReply) {
            var replyBtn = document.createElement("button");
            replyBtn.type = "button";
            replyBtn.className = "dockside-mini";
            replyBtn.textContent = "Reply";
            replyBtn.addEventListener("click", function () { onReply(post); });
            text.appendChild(replyBtn);
        }
        row.appendChild(text);
        wrap.appendChild(row);
        (replies || []).forEach(function (reply) {
            var item = document.createElement("div");
            item.className = "dockside-reply";
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
            replyBody.textContent = reply.body || "";
            replyText.appendChild(replyMeta);
            replyText.appendChild(replyBody);
            replyRow.appendChild(replyText);
            item.appendChild(replyRow);
            wrap.appendChild(item);
        });
        return wrap;
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
        row.style.setProperty("--dockside-space", (root.offsetHeight + 12) + "px");
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
        var parentId = null;

        function fit() {
            fitDocksideCard(root);
        }

        function paintMe() {
            if (!meAvatar) return;
            meAvatar.textContent = "";
            if (!me.signed_in) return;
            var author = me;
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
        }

        function setTarget(post) {
            parentId = post ? post.post_id : null;
            if (!field) return;
            var name = post && post.author && post.author.display_name;
            field.placeholder = name ? ("Reply to " + name) : "Write a comment";
            field.focus();
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
            subjectEl.textContent = topic.subject || "";
            var parts = splitThread(topic.posts);
            originalEl.textContent = "";
            scroll.textContent = "";
            if (parts.originalPost) originalEl.appendChild(cardPost(parts.originalPost, [], setTarget));
            parts.roots.forEach(function (comment) {
                scroll.appendChild(cardPost(comment, parts.replies[comment.post_id] || [], setTarget));
            });
            showLatestTwo(scroll);
            paintMe();
            fit();
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

        paintMe();
        api("/api/dockside/current").then(function (data) {
            if (!data || data._status !== 200) {
                showEmpty("Dockside Chat is unavailable.");
                if (startOpen) startOpen.hidden = true;
                return;
            }
            if (!data.topic) {
                showEmpty("No discussion yet.");
                var draft = readDraft();
                if (draft && draft.kind === "topic") {
                    if (startSubject) startSubject.value = draft.subject || "";
                    if (startBody) startBody.value = draft.body || "";
                    showStart(true);
                }
                return;
            }
            paintTopic(data.topic);
            var commentDraft = readDraft();
            if (commentDraft && commentDraft.kind === "comment" && field && (!commentDraft.topic_id || commentDraft.topic_id === topicId)) {
                field.value = commentDraft.body || "";
                parentId = commentDraft.parent_post_id || null;
                if (parentId) field.placeholder = "Reply";
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
                var subject = ((startSubject && startSubject.value) || "").trim();
                var body = ((startBody && startBody.value) || "").trim();
                if (subject.length < 3 || !body) {
                    noteError(startForm, subject.length < 3 ? "Subject needs at least 3 characters." : "Write the first post.");
                    return;
                }
                var draft = { kind: "topic", subject: subject, body: body };
                if (!me.signed_in) {
                    goLogin(draft);
                    return;
                }
                api("/api/dockside/topics", {
                    method: "POST",
                    body: JSON.stringify({ subject: subject, body: body })
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
                    paintTopic(data);
                });
            });
        }
        if (form && field) {
            form.addEventListener("submit", function (event) {
                event.preventDefault();
                var body = (field.value || "").trim();
                if (!body || !topicId) return;
                var draft = { kind: "comment", topic_id: topicId, parent_post_id: parentId, body: body };
                if (!me.signed_in) {
                    goLogin(draft);
                    return;
                }
                api("/api/dockside/topics/" + topicId + "/posts", {
                    method: "POST",
                    body: JSON.stringify({ body: body, parent_post_id: parentId })
                }).then(function (data) {
                    if (data._status === 401) {
                        goLogin(draft);
                        return;
                    }
                    if (!data || data._status !== 200 || !data.topic) {
                        noteError(scroll, (data && data.detail) || "Comment was not saved");
                        return;
                    }
                    clearDraft();
                    field.value = "";
                    parentId = null;
                    field.placeholder = "Write a comment";
                    paintTopic(data.topic);
                });
            });
        }
        window.addEventListener("resize", fit);
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
        var q = search.get("q") || "";
        var topic = search.get("topic") || "";
        var searchInput = document.getElementById("dockside-search");
        var list = document.getElementById("dockside-topic-list");
        var thread = document.getElementById("dockside-thread");
        var threadSubject = document.getElementById("dockside-thread-subject");
        var threadPosts = document.getElementById("dockside-thread-posts");
        var threadForm = document.getElementById("dockside-thread-form");
        var threadBody = document.getElementById("dockside-thread-body");
        var muteBtn = document.getElementById("dockside-mute");
        var newForm = document.getElementById("dockside-new-topic");
        var newSubject = document.getElementById("dockside-new-subject");
        var newBody = document.getElementById("dockside-new-body");
        var newError = document.getElementById("dockside-new-error");
        var notes = document.getElementById("dockside-notes");
        var meLine = document.getElementById("dockside-me");
        var parentId = null;
        if (searchInput) searchInput.value = q;

        function writeUrl() {
            var next = new URLSearchParams();
            if (q) next.set("q", q);
            if (sort) next.set("sort", sort);
            if (dir) next.set("dir", dir);
            if (topic) next.set("topic", topic);
            history.replaceState(null, "", location.pathname + (next.toString() ? "?" + next.toString() : ""));
        }

        function paintSort() {
            document.querySelectorAll(".dockside-sort button").forEach(function (button) {
                button.classList.toggle("is-active", button.getAttribute("data-sort") === sort);
            });
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

        function loadList() {
            var path = "/api/dockside/topics?sort=" + encodeURIComponent(sort) + "&dir=" + encodeURIComponent(dir);
            if (q) path += "&q=" + encodeURIComponent(q);
            api(path).then(function (data) {
                list.textContent = "";
                if (!data || data._status !== 200) {
                    var failed = document.createElement("p");
                    failed.className = "dockside-error";
                    failed.textContent = (data && data.detail) || "Topics could not be loaded";
                    list.appendChild(failed);
                    return;
                }
                var rows = data.topics || [];
                if (!rows.length) {
                    var empty = document.createElement("p");
                    empty.className = "dockside-empty";
                    empty.textContent = q ? "No topics match that search." : "No topics yet.";
                    list.appendChild(empty);
                    return;
                }
                rows.forEach(function (row) {
                    var button = document.createElement("button");
                    button.type = "button";
                    button.className = "dockside-topic-row";
                    var label = document.createElement("span");
                    label.textContent = row.subject || "";
                    var meta = document.createElement("small");
                    meta.textContent = String(row.comment_count || 0) + " · " + when(row.updated_at);
                    button.appendChild(label);
                    button.appendChild(meta);
                    button.addEventListener("click", function () {
                        topic = String(row.topic_id);
                        writeUrl();
                        loadThread();
                    });
                    list.appendChild(button);
                });
            });
        }

        function loadThread() {
            if (!topic) {
                thread.hidden = true;
                return;
            }
            api("/api/dockside/topics/" + encodeURIComponent(topic)).then(function (data) {
                if (data._status === 404 || !data.topic_id) {
                    thread.hidden = true;
                    return;
                }
                thread.hidden = false;
                threadSubject.textContent = data.subject || "";
                var muted = data.following && data.following.muted;
                muteBtn.hidden = !me.signed_in;
                muteBtn.textContent = muted ? "Unmute" : "Mute";
                muteBtn.dataset.muted = muted ? "1" : "0";
                renderPosts(data.posts, threadPosts, function (post) {
                    parentId = post.post_id;
                    threadBody.placeholder = "Reply";
                    threadBody.focus();
                }, true);
                thread.scrollIntoView({ block: "nearest" });
            });
        }

        document.querySelectorAll(".dockside-sort button").forEach(function (button) {
            button.addEventListener("click", function () {
                var next = button.getAttribute("data-sort");
                if (sort === next) dir = dir === "asc" ? "desc" : "asc";
                else {
                    sort = next;
                    dir = next === "subject" ? "asc" : "desc";
                }
                rememberSort(sort, dir);
                paintSort();
                writeUrl();
                loadList();
            });
        });

        document.getElementById("dockside-search-form").addEventListener("submit", function (event) {
            event.preventDefault();
            q = (searchInput.value || "").trim();
            writeUrl();
            loadList();
        });
        searchInput.addEventListener("input", function () {
            q = (searchInput.value || "").trim();
            if (q.length === 1) return;
            writeUrl();
            loadList();
        });

        muteBtn.addEventListener("click", function () {
            if (!me.signed_in) {
                goLogin(null);
                return;
            }
            var muted = muteBtn.dataset.muted !== "1";
            api("/api/dockside/topics/" + encodeURIComponent(topic) + "/follow", {
                method: "POST",
                body: JSON.stringify({ muted: muted })
            }).then(function (data) {
                if (data._status === 401) {
                    goLogin(null);
                    return;
                }
                muteBtn.dataset.muted = data.muted ? "1" : "0";
                muteBtn.textContent = data.muted ? "Unmute" : "Mute";
            });
        });

        threadForm.addEventListener("submit", function (event) {
            event.preventDefault();
            var body = (threadBody.value || "").trim();
            if (!body || !topic) return;
            var draft = { kind: "comment", topic_id: Number(topic), parent_post_id: parentId, body: body };
            if (!me.signed_in) {
                goLogin(draft);
                return;
            }
            api("/api/dockside/topics/" + encodeURIComponent(topic) + "/posts", {
                method: "POST",
                body: JSON.stringify({ body: body, parent_post_id: parentId })
            }).then(function (data) {
                if (data._status === 401) {
                    goLogin(draft);
                    return;
                }
                if (data._status !== 200) {
                    newError.textContent = data.detail || "Comment was not saved";
                    return;
                }
                clearDraft();
                threadBody.value = "";
                parentId = null;
                threadBody.placeholder = "Write a comment";
                loadThread();
                loadList();
                loadNotes();
            });
        });

        newForm.addEventListener("submit", function (event) {
            event.preventDefault();
            newError.textContent = "";
            var subject = (newSubject.value || "").trim();
            var body = (newBody.value || "").trim();
            var draft = { kind: "topic", subject: subject, body: body };
            if (!me.signed_in) {
                goLogin(draft);
                return;
            }
            api("/api/dockside/topics", {
                method: "POST",
                body: JSON.stringify({ subject: subject, body: body })
            }).then(function (data) {
                if (data._status === 401) {
                    goLogin(draft);
                    return;
                }
                if (data._status !== 200) {
                    newError.textContent = data.detail || "Topic was not saved";
                    return;
                }
                clearDraft();
                newSubject.value = "";
                newBody.value = "";
                topic = String(data.topic_id);
                writeUrl();
                loadList();
                loadThread();
            });
        });

        var draft = readDraft();
        if (draft && draft.kind === "topic") {
            newSubject.value = draft.subject || "";
            newBody.value = draft.body || "";
        }
        if (draft && draft.kind === "comment" && draft.topic_id) {
            topic = topic || String(draft.topic_id);
            threadBody.value = draft.body || "";
            parentId = draft.parent_post_id || null;
        }
        if (meLine) {
            meLine.textContent = me.signed_in
                ? ("Signed in as " + (me.display_name || me.sas_id || "sailor"))
                : "Sign in to start a topic or reply. Your draft is kept.";
        }
        paintSort();
        writeUrl();
        loadList();
        loadThread();
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
