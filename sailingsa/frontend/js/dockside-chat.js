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

    function goLogin(draft) {
        if (draft) {
            try { sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft)); } catch (err) {}
        }
        var ret = (location.pathname || "/") + (location.search || "") + (location.hash || "");
        location.href = "/login.html?returnTo=" + encodeURIComponent(ret);
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

    function authorNode(author) {
        var name = (author && author.display_name) || "Sailor";
        if (author && author.profile_url) {
            var link = document.createElement("a");
            link.href = author.profile_url;
            link.textContent = name;
            return link;
        }
        var span = document.createElement("span");
        span.textContent = name;
        return span;
    }

    function postNode(post, replies, onReply, full) {
        var wrap = document.createElement("div");
        wrap.className = "dockside-comment";
        var meta = document.createElement("div");
        meta.className = "dockside-meta";
        meta.appendChild(authorNode(post.author));
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
            replyMeta.appendChild(authorNode(reply.author));
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

    function renderPosts(posts, mount, onReply, full) {
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
            mount.appendChild(postNode(comment, byParent[comment.post_id] || [], onReply, full));
        });
        mount.scrollTop = mount.scrollHeight;
    }

    function bootLanding() {
        var root = document.getElementById("dockside-landing");
        if (!root) return;
        var subjectEl = document.getElementById("dockside-subject");
        var scroll = document.getElementById("dockside-scroll");
        var form = document.getElementById("dockside-reply-form");
        var field = document.getElementById("dockside-reply-body");
        var topicId = null;
        var parentId = null;

        function setTarget(post) {
            parentId = post ? post.post_id : null;
            if (field) {
                field.placeholder = post ? "Reply" : "Comment on this topic";
                field.focus();
            }
        }

        api("/api/dockside/current").then(function (data) {
            if (!data || data._status !== 200) {
                subjectEl.textContent = "Dockside Chat is unavailable";
                return;
            }
            var topic = data.topic;
            if (!topic) {
                subjectEl.textContent = "No discussion yet";
                scroll.textContent = "";
                var empty = document.createElement("p");
                empty.className = "dockside-empty";
                empty.textContent = "No comments yet.";
                scroll.appendChild(empty);
                if (form) form.hidden = true;
                return;
            }
            topicId = topic.topic_id;
            subjectEl.textContent = topic.subject || "";
            renderPosts(topic.posts, scroll, setTarget, false);
            var draft = readDraft();
            if (draft && draft.kind === "comment" && field && (!draft.topic_id || draft.topic_id === topicId)) {
                field.value = draft.body || "";
                parentId = draft.parent_post_id || null;
            }
        }).catch(function () {
            subjectEl.textContent = "Dockside Chat is unavailable";
        });

        if (!form) return;
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            var body = (field.value || "").trim();
            if (!body) return;
            var draft = { kind: "comment", topic_id: topicId, parent_post_id: parentId, body: body };
            if (!me.signed_in) {
                goLogin(draft);
                return;
            }
            if (!topicId) {
                location.href = "/dockside.html#new";
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
                if (data._status !== 200) {
                    var err = document.createElement("p");
                    err.className = "dockside-error";
                    err.textContent = data.detail || "Comment was not saved";
                    scroll.appendChild(err);
                    return;
                }
                clearDraft();
                field.value = "";
                parentId = null;
                field.placeholder = "Comment on this topic";
                if (data.topic) renderPosts(data.topic.posts, scroll, setTarget, false);
            });
        });
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
