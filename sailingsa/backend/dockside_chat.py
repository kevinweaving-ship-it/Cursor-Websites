"""Dockside Chat: topics, comments, replies, follows, notifications, reports.

Routes are registered onto the live FastAPI app. All writes require a valid
session cookie. Hidden rows are omitted from public reads.
"""
from __future__ import annotations

import re
import threading
from datetime import datetime, timezone

import psycopg2.extras
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

_SCHEMA_LOCK = threading.Lock()
_SCHEMA_READY = False
_TAG_RE = re.compile(r"<[^>]*>")
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_SORTS = {
    ("updated", "desc"): "t.updated_at DESC, t.topic_id DESC",
    ("updated", "asc"): "t.updated_at ASC, t.topic_id ASC",
    ("subject", "asc"): "t.subject ASC, t.topic_id ASC",
    ("subject", "desc"): "t.subject DESC, t.topic_id DESC",
    ("comments", "desc"): "comment_count DESC, t.updated_at DESC",
    ("comments", "asc"): "comment_count ASC, t.updated_at ASC",
}


class DocksideError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _clean_subject(value) -> str:
    if not isinstance(value, str):
        raise DocksideError(400, "Subject is required")
    text = _TAG_RE.sub("", value.replace("\x00", ""))
    text = re.sub(r"\s+", " ", text).strip()
    if any(ord(ch) < 32 for ch in text):
        raise DocksideError(400, "Subject contains invalid characters")
    if len(text) < 3 or len(text) > 120:
        raise DocksideError(400, "Subject must be 3 to 120 characters")
    return text


def _clean_body(value) -> str:
    if not isinstance(value, str):
        raise DocksideError(400, "Comment is required")
    text = _TAG_RE.sub("", value.replace("\x00", ""))
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in text):
        raise DocksideError(400, "Comment contains invalid characters")
    if not text or len(text) > 2000:
        raise DocksideError(400, "Comment must be 1 to 2000 characters")
    return text


def _clean_reason(value) -> str:
    if not isinstance(value, str):
        raise DocksideError(400, "A reason is required")
    text = _TAG_RE.sub("", value.replace("\x00", ""))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 3 or len(text) > 500:
        raise DocksideError(400, "Reason must be 3 to 500 characters")
    return text


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _profile_url(slug):
    if slug and _SLUG_RE.match(str(slug)):
        return "/sailor/" + str(slug)
    return None


def _photo_url(path):
    if not path:
        return None
    text = str(path).strip()
    if not text or ".." in text or text.startswith("/api/club-logo/"):
        return None
    if text.startswith("https://sailingsa.co.za/"):
        return text
    if text.startswith("/") and "://" not in text:
        return text
    if re.match(r"^[A-Za-z0-9_./-]+$", text):
        return "/" + text.lstrip("/")
    return None


def _role_key(role) -> str:
    return str(role or "").strip().lower().replace(" ", "_").replace("-", "_")


def _is_public_admin(role) -> bool:
    return _role_key(role) in ("super_admin", "superadmin")


def _hide_personal_name(name, role) -> bool:
    folded = re.sub(r"\s+", " ", str(name or "")).strip().lower()
    return _is_public_admin(role) or folded == "kevin weaving"


def _author(row) -> dict:
    account_id = row.get("created_by") or row.get("account_id")
    if _hide_personal_name(row.get("display_name"), row.get("role")):
        return {
            "account_id": account_id,
            "sas_id": None,
            "display_name": "Admin",
            "avatar_text": "SA",
            "profile_url": None,
            "photo_url": None,
        }
    name = (row.get("display_name") or row.get("sas_id") or "").strip()
    photo = _photo_url(row.get("profile_picture_path")) or _photo_url(row.get("profile_photo_path"))
    return {
        "account_id": account_id,
        "sas_id": row.get("sas_id"),
        "display_name": name,
        "profile_url": _profile_url(row.get("slug")),
        "photo_url": photo,
    }


def apply_schema(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.dockside_topics (
            topic_id bigserial PRIMARY KEY,
            subject text NOT NULL,
            created_by bigint NOT NULL REFERENCES public.user_accounts(account_id),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            status text NOT NULL DEFAULT 'open',
            CONSTRAINT dockside_topics_status_chk CHECK (status IN ('open', 'hidden')),
            CONSTRAINT dockside_topics_subject_chk CHECK (char_length(subject) BETWEEN 3 AND 120)
        );
        CREATE TABLE IF NOT EXISTS public.dockside_posts (
            post_id bigserial PRIMARY KEY,
            topic_id bigint NOT NULL REFERENCES public.dockside_topics(topic_id) ON DELETE CASCADE,
            parent_post_id bigint REFERENCES public.dockside_posts(post_id) ON DELETE CASCADE,
            body text NOT NULL,
            created_by bigint NOT NULL REFERENCES public.user_accounts(account_id),
            created_at timestamptz NOT NULL DEFAULT now(),
            status text NOT NULL DEFAULT 'visible',
            CONSTRAINT dockside_posts_status_chk CHECK (status IN ('visible', 'hidden')),
            CONSTRAINT dockside_posts_body_chk CHECK (char_length(body) BETWEEN 1 AND 2000)
        );
        CREATE INDEX IF NOT EXISTS dockside_posts_topic_idx
            ON public.dockside_posts (topic_id, created_at);
        CREATE TABLE IF NOT EXISTS public.dockside_follows (
            topic_id bigint NOT NULL REFERENCES public.dockside_topics(topic_id) ON DELETE CASCADE,
            account_id bigint NOT NULL REFERENCES public.user_accounts(account_id) ON DELETE CASCADE,
            muted boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (topic_id, account_id)
        );
        CREATE TABLE IF NOT EXISTS public.dockside_notifications (
            notification_id bigserial PRIMARY KEY,
            account_id bigint NOT NULL REFERENCES public.user_accounts(account_id) ON DELETE CASCADE,
            topic_id bigint NOT NULL,
            post_id bigint NOT NULL,
            actor_account_id bigint NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            read_at timestamptz,
            UNIQUE (account_id, post_id)
        );
        CREATE INDEX IF NOT EXISTS dockside_notif_unread_idx
            ON public.dockside_notifications (account_id) WHERE read_at IS NULL;
        CREATE TABLE IF NOT EXISTS public.dockside_reports (
            report_id bigserial PRIMARY KEY,
            post_id bigint NOT NULL REFERENCES public.dockside_posts(post_id) ON DELETE CASCADE,
            reporter_account_id bigint NOT NULL REFERENCES public.user_accounts(account_id),
            reason text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            status text NOT NULL DEFAULT 'open',
            CONSTRAINT dockside_reports_reason_chk CHECK (char_length(reason) BETWEEN 3 AND 500),
            CONSTRAINT dockside_reports_status_chk CHECK (status IN ('open', 'closed'))
        );
        CREATE TABLE IF NOT EXISTS public.dockside_reactions (
            post_id bigint NOT NULL REFERENCES public.dockside_posts(post_id) ON DELETE CASCADE,
            account_id bigint NOT NULL REFERENCES public.user_accounts(account_id) ON DELETE CASCADE,
            kind text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (post_id, account_id, kind),
            CONSTRAINT dockside_reactions_kind_chk CHECK (kind IN ('up', 'heart', 'down'))
        );
        CREATE INDEX IF NOT EXISTS dockside_topics_updated_idx
            ON public.dockside_topics (updated_at DESC) WHERE status = 'open';
        DELETE FROM public.dockside_notifications n
        WHERE NOT EXISTS (
            SELECT 1 FROM public.dockside_posts p WHERE p.post_id = n.post_id
        );
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'dockside_notifications_post_fk'
            ) THEN
                ALTER TABLE public.dockside_notifications
                    ADD CONSTRAINT dockside_notifications_post_fk
                    FOREIGN KEY (post_id) REFERENCES public.dockside_posts(post_id) ON DELETE CASCADE;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'dockside_notifications_topic_fk'
            ) THEN
                ALTER TABLE public.dockside_notifications
                    ADD CONSTRAINT dockside_notifications_topic_fk
                    FOREIGN KEY (topic_id) REFERENCES public.dockside_topics(topic_id) ON DELETE CASCADE;
            END IF;
        END $$;
        """
    )
    cur.close()


def ensure_schema(conn) -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        apply_schema(conn)
        conn.commit()
        _SCHEMA_READY = True


def _cur(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def session_account(conn, token: str):
    if not token:
        return None
    cur = _cur(conn)
    cur.execute(
        """
        SELECT s.account_id, s.sas_id, ua.role,
               COALESCE(
                   NULLIF(TRIM(ua.full_name), ''),
                   NULLIF(TRIM(CONCAT_WS(' ', sp.first_name, sp.last_name)), ''),
                   NULLIF(TRIM(sp.full_name), ''),
                   s.sas_id
               ) AS display_name,
               NULLIF(TRIM(sp.ssl_profile_slug), '') AS slug
        FROM public.user_sessions s
        JOIN public.user_accounts ua ON ua.account_id = s.account_id
        LEFT JOIN LATERAL (
            SELECT first_name, last_name, full_name, ssl_profile_slug
            FROM public.sas_id_personal
            WHERE sa_sailing_id = s.sas_id
            ORDER BY id NULLS LAST
            LIMIT 1
        ) sp ON true
        WHERE s.session_id = %s
          AND s.expires_at > NOW()
          AND COALESCE(s.is_active, true) IS TRUE
          AND COALESCE(ua.is_active, true) IS TRUE
        """,
        (token,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    role = _role_key(row.get("role"))
    admin = _hide_personal_name(row.get("display_name"), role)
    return {
        "account_id": int(row["account_id"]),
        "sas_id": None if admin else row.get("sas_id"),
        "role": role,
        "display_name": "Admin" if admin else (row.get("display_name") or row.get("sas_id") or "").strip(),
        "avatar_text": "SA" if admin else None,
        "profile_url": None if admin else _profile_url(row.get("slug")),
        "is_super_admin": admin,
    }


def _require(account):
    if not account:
        raise DocksideError(401, "Sign in required")
    return account


def _rate_limit(cur, account_id: int) -> None:
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM public.dockside_posts
        WHERE created_by = %s AND created_at > NOW() - INTERVAL '5 minutes'
        """,
        (account_id,),
    )
    if int(cur.fetchone()["n"]) >= 8:
        raise DocksideError(429, "Too many comments. Wait a few minutes and try again.")


def _follow(cur, topic_id: int, account_id: int, muted: bool) -> None:
    cur.execute(
        """
        INSERT INTO public.dockside_follows (topic_id, account_id, muted)
        VALUES (%s, %s, %s)
        ON CONFLICT (topic_id, account_id)
        DO UPDATE SET muted = EXCLUDED.muted
        """,
        (topic_id, account_id, muted),
    )


def _notify(cur, topic_id: int, post_id: int, actor_id: int) -> int:
    cur.execute(
        """
        INSERT INTO public.dockside_notifications
            (account_id, topic_id, post_id, actor_account_id)
        SELECT f.account_id, %s, %s, %s
        FROM public.dockside_follows f
        WHERE f.topic_id = %s
          AND f.muted IS FALSE
          AND f.account_id <> %s
        ON CONFLICT (account_id, post_id) DO NOTHING
        """,
        (topic_id, post_id, actor_id, topic_id, actor_id),
    )
    return cur.rowcount


def _touch_topic(cur, topic_id: int) -> None:
    cur.execute(
        "UPDATE public.dockside_topics SET updated_at = NOW() WHERE topic_id = %s",
        (topic_id,),
    )


def _open_topic(cur, topic_id: int):
    cur.execute(
        """
        SELECT topic_id, subject, status, created_by, created_at, updated_at
        FROM public.dockside_topics
        WHERE topic_id = %s
        """,
        (topic_id,),
    )
    row = cur.fetchone()
    if not row or row["status"] != "open":
        raise DocksideError(404, "Topic not found")
    return row


def _empty_reactions():
    return {"counts": {"up": 0, "heart": 0, "down": 0}, "mine": []}


def _attach_reactions(cur, posts, account_id):
    ids = [post["post_id"] for post in posts]
    counts = {}
    mine = {}
    if ids:
        cur.execute(
            """
            SELECT post_id, kind, COUNT(*) AS n
            FROM public.dockside_reactions
            WHERE post_id = ANY(%s)
            GROUP BY post_id, kind
            """,
            (ids,),
        )
        for row in cur.fetchall():
            bucket = counts.setdefault(row["post_id"], {"up": 0, "heart": 0, "down": 0})
            bucket[row["kind"]] = int(row["n"])
        if account_id:
            cur.execute(
                """
                SELECT post_id, kind
                FROM public.dockside_reactions
                WHERE account_id = %s AND post_id = ANY(%s)
                """,
                (account_id, ids),
            )
            for row in cur.fetchall():
                mine.setdefault(row["post_id"], []).append(row["kind"])
    for post in posts:
        base = {"up": 0, "heart": 0, "down": 0}
        base.update(counts.get(post["post_id"], {}))
        post["reactions"] = {"counts": base, "mine": mine.get(post["post_id"], [])}
    return posts


def _posts(cur, topic_id: int, account_id=None):
    cur.execute(
        """
        SELECT p.post_id, p.parent_post_id, p.body, p.created_at, p.created_by,
               ua.sas_id, ua.role, ua.profile_picture_path,
               COALESCE(
                   NULLIF(TRIM(ua.full_name), ''),
                   NULLIF(TRIM(CONCAT_WS(' ', sp.first_name, sp.last_name)), ''),
                   NULLIF(TRIM(sp.full_name), ''),
                   ua.sas_id
               ) AS display_name,
               NULLIF(TRIM(sp.ssl_profile_slug), '') AS slug,
               sp.profile_photo_path
        FROM public.dockside_posts p
        JOIN public.user_accounts ua ON ua.account_id = p.created_by
        LEFT JOIN LATERAL (
            SELECT first_name, last_name, full_name, ssl_profile_slug, profile_photo_path
            FROM public.sas_id_personal
            WHERE sa_sailing_id = ua.sas_id
            ORDER BY id NULLS LAST
            LIMIT 1
        ) sp ON true
        WHERE p.topic_id = %s AND p.status = 'visible'
        ORDER BY p.created_at ASC, p.post_id ASC
        LIMIT 200
        """,
        (topic_id,),
    )
    rows = cur.fetchall()
    out = []
    for row in rows:
        out.append(
            {
                "post_id": row["post_id"],
                "parent_post_id": row["parent_post_id"],
                "body": row["body"],
                "created_at": _iso(row["created_at"]),
                "author": _author(row),
                "reactions": _empty_reactions(),
            }
        )
    return _attach_reactions(cur, out, account_id)


def _topic_json(row, posts, following=None):
    return {
        "topic_id": row["topic_id"],
        "subject": row["subject"],
        "created_at": _iso(row["created_at"]),
        "updated_at": _iso(row["updated_at"]),
        "posts": posts,
        "following": following,
    }


def _stored_subject(body: str) -> str:
    text = re.sub(r"\s+", " ", body).strip()
    if len(text) > 120:
        text = text[:117].rstrip() + "..."
    if len(text) < 3:
        text = (text + "...")[:3]
    return text


def create_topic(conn, account, subject, body) -> dict:
    account = _require(account)
    body = _clean_body(body)
    subject = _stored_subject(body)
    cur = _cur(conn)
    _rate_limit(cur, account["account_id"])
    cur.execute(
        """
        INSERT INTO public.dockside_topics (subject, created_by)
        VALUES (%s, %s)
        RETURNING topic_id, subject, status, created_by, created_at, updated_at
        """,
        (subject, account["account_id"]),
    )
    topic = cur.fetchone()
    cur.execute(
        """
        INSERT INTO public.dockside_posts (topic_id, body, created_by)
        VALUES (%s, %s, %s)
        RETURNING post_id
        """,
        (topic["topic_id"], body, account["account_id"]),
    )
    post_id = cur.fetchone()["post_id"]
    _follow(cur, topic["topic_id"], account["account_id"], False)
    _notify(cur, topic["topic_id"], post_id, account["account_id"])
    cur.close()
    return _topic_json(topic, _posts(_cur(conn), topic["topic_id"], account["account_id"]), {"muted": False})


def add_post(conn, account, topic_id: int, body, parent_post_id) -> dict:
    account = _require(account)
    body = _clean_body(body)
    cur = _cur(conn)
    topic = _open_topic(cur, topic_id)
    _rate_limit(cur, account["account_id"])
    parent_id = None
    if parent_post_id not in (None, "", 0, "0"):
        try:
            parent_id = int(parent_post_id)
        except (TypeError, ValueError):
            raise DocksideError(400, "Reply target is invalid")
        cur.execute(
            """
            SELECT post_id, parent_post_id, status
            FROM public.dockside_posts
            WHERE post_id = %s AND topic_id = %s
            """,
            (parent_id, topic_id),
        )
        parent = cur.fetchone()
        if not parent or parent["status"] != "visible":
            raise DocksideError(400, "Reply target is not on this topic")
        guard = 0
        while parent and parent["parent_post_id"]:
            guard += 1
            if guard > 5:
                raise DocksideError(400, "Reply target is invalid")
            cur.execute(
                """
                SELECT post_id, parent_post_id, status
                FROM public.dockside_posts
                WHERE post_id = %s AND topic_id = %s
                """,
                (parent["parent_post_id"], topic_id),
            )
            parent = cur.fetchone()
        if not parent or parent["status"] != "visible":
            raise DocksideError(400, "Reply target is not on this topic")
        parent_id = parent["post_id"]
    cur.execute(
        """
        INSERT INTO public.dockside_posts (topic_id, parent_post_id, body, created_by)
        VALUES (%s, %s, %s, %s)
        RETURNING post_id
        """,
        (topic_id, parent_id, body, account["account_id"]),
    )
    post_id = cur.fetchone()["post_id"]
    _follow(cur, topic_id, account["account_id"], False)
    notified = _notify(cur, topic_id, post_id, account["account_id"])
    _touch_topic(cur, topic_id)
    cur.close()
    fresh = _open_topic(_cur(conn), topic_id)
    return {
        "post_id": post_id,
        "notified": notified,
        "topic": _topic_json(fresh, _posts(_cur(conn), topic_id, account["account_id"])),
    }


def list_topics(conn, q: str, sort: str, direction: str, limit: int = 50) -> dict:
    sort_key = (sort or "updated", direction or "desc")
    if sort_key not in _SORTS:
        sort_key = ("updated", "desc")
    query = (q or "").strip()
    if query and len(query) < 2:
        raise DocksideError(400, "Search needs at least 2 characters")
    pattern = _like(query) if query else None
    cur = _cur(conn)
    cur.execute(
        f"""
        SELECT t.topic_id, t.subject, t.created_at, t.updated_at,
               (
                   SELECT p.body
                   FROM public.dockside_posts p
                   WHERE p.topic_id = t.topic_id
                     AND p.status = 'visible'
                     AND p.parent_post_id IS NULL
                   ORDER BY p.created_at ASC, p.post_id ASC
                   LIMIT 1
               ) AS opening,
               (
                   SELECT COUNT(*)
                   FROM public.dockside_posts p
                   WHERE p.topic_id = t.topic_id
                     AND p.status = 'visible'
                     AND p.parent_post_id IS NULL
               ) AS comment_count
        FROM public.dockside_topics t
        WHERE t.status = 'open'
          AND (
                %s IS NULL
                OR t.subject ILIKE %s ESCAPE '\\'
                OR EXISTS (
                    SELECT 1 FROM public.dockside_posts p
                    WHERE p.topic_id = t.topic_id
                      AND p.status = 'visible'
                      AND p.body ILIKE %s ESCAPE '\\'
                )
          )
        ORDER BY {_SORTS[sort_key]}
        LIMIT %s
        """,
        (pattern, pattern, pattern, max(1, min(int(limit), 50))),
    )
    rows = cur.fetchall()
    cur.close()
    return {
        "topics": [
            {
                "topic_id": row["topic_id"],
                "subject": row["subject"],
                "opening": (row.get("opening") or "")[:160],
                "created_at": _iso(row["created_at"]),
                "updated_at": _iso(row["updated_at"]),
                "comment_count": int(row["comment_count"]),
            }
            for row in rows
        ],
        "sort": sort_key[0],
        "dir": sort_key[1],
        "q": query,
    }


def get_topic(conn, topic_id: int, account=None) -> dict:
    cur = _cur(conn)
    topic = _open_topic(cur, topic_id)
    following = None
    if account:
        cur.execute(
            """
            SELECT muted FROM public.dockside_follows
            WHERE topic_id = %s AND account_id = %s
            """,
            (topic_id, account["account_id"]),
        )
        row = cur.fetchone()
        if row:
            following = {"muted": bool(row["muted"])}
    posts = _posts(cur, topic_id, account["account_id"] if account else None)
    cur.close()
    return _topic_json(topic, posts, following)


def current_topic(conn, account=None) -> dict:
    cur = _cur(conn)
    cur.execute(
        """
        SELECT topic_id, subject, status, created_by, created_at, updated_at
        FROM public.dockside_topics
        WHERE status = 'open'
        ORDER BY updated_at DESC, topic_id DESC
        LIMIT 1
        """
    )
    topic = cur.fetchone()
    if not topic:
        cur.close()
        return {"topic": None}
    viewer = account["account_id"] if account else None
    payload = _topic_json(topic, _posts(cur, topic["topic_id"], viewer))
    cur.close()
    return {"topic": payload}


def set_muted(conn, account, topic_id: int, muted: bool) -> dict:
    account = _require(account)
    cur = _cur(conn)
    _open_topic(cur, topic_id)
    _follow(cur, topic_id, account["account_id"], bool(muted))
    cur.close()
    return {"topic_id": topic_id, "muted": bool(muted)}


def list_notifications(conn, account, limit: int = 30) -> dict:
    account = _require(account)
    cur = _cur(conn)
    cur.execute(
        """
        SELECT n.notification_id, n.topic_id, n.post_id, n.created_at, n.read_at,
               t.subject, p.parent_post_id,
               ua.role AS actor_role,
               COALESCE(
                   NULLIF(TRIM(ua.full_name), ''),
                   NULLIF(TRIM(CONCAT_WS(' ', sp.first_name, sp.last_name)), ''),
                   NULLIF(TRIM(sp.full_name), ''),
                   ua.sas_id
               ) AS actor_name
        FROM public.dockside_notifications n
        JOIN public.dockside_topics t ON t.topic_id = n.topic_id AND t.status = 'open'
        JOIN public.dockside_posts p ON p.post_id = n.post_id AND p.status = 'visible'
        JOIN public.user_accounts ua ON ua.account_id = n.actor_account_id
        LEFT JOIN LATERAL (
            SELECT first_name, last_name, full_name
            FROM public.sas_id_personal
            WHERE sa_sailing_id = ua.sas_id
            ORDER BY id NULLS LAST
            LIMIT 1
        ) sp ON true
        WHERE n.account_id = %s
        ORDER BY n.created_at DESC
        LIMIT %s
        """,
        (account["account_id"], max(1, min(int(limit), 50))),
    )
    rows = cur.fetchall()
    cur.execute(
        """
        SELECT COUNT(*) AS n
        FROM public.dockside_notifications n
        JOIN public.dockside_posts p ON p.post_id = n.post_id AND p.status = 'visible'
        WHERE n.account_id = %s AND n.read_at IS NULL
        """,
        (account["account_id"],),
    )
    unread = int(cur.fetchone()["n"])
    cur.close()
    return {
        "unread": unread,
        "notifications": [
            {
                "notification_id": row["notification_id"],
                "topic_id": row["topic_id"],
                "post_id": row["post_id"],
                "subject": row["subject"],
                "actor_name": "Admin" if _hide_personal_name(row.get("actor_name"), row.get("actor_role")) else (row.get("actor_name") or "").strip(),
                "kind": "reply" if row["parent_post_id"] else "comment",
                "created_at": _iso(row["created_at"]),
                "read": row["read_at"] is not None,
            }
            for row in rows
        ],
    }


def mark_read(conn, account, ids, mark_all: bool) -> dict:
    account = _require(account)
    cur = _cur(conn)
    if mark_all:
        cur.execute(
            """
            UPDATE public.dockside_notifications
            SET read_at = NOW()
            WHERE account_id = %s AND read_at IS NULL
            """,
            (account["account_id"],),
        )
    else:
        clean = []
        for item in ids or []:
            try:
                clean.append(int(item))
            except (TypeError, ValueError):
                continue
        if clean:
            cur.execute(
                """
                UPDATE public.dockside_notifications
                SET read_at = NOW()
                WHERE account_id = %s AND notification_id = ANY(%s) AND read_at IS NULL
                """,
                (account["account_id"], clean),
            )
    cur.close()
    return {"ok": True}


def report_post(conn, account, post_id: int, reason: str) -> dict:
    account = _require(account)
    reason = _clean_reason(reason)
    cur = _cur(conn)
    cur.execute(
        """
        SELECT post_id, created_by, status
        FROM public.dockside_posts
        WHERE post_id = %s
        """,
        (post_id,),
    )
    post = cur.fetchone()
    if not post or post["status"] != "visible":
        raise DocksideError(404, "Comment not found")
    if int(post["created_by"]) == int(account["account_id"]):
        raise DocksideError(400, "You cannot report your own comment")
    cur.execute(
        """
        INSERT INTO public.dockside_reports (post_id, reporter_account_id, reason)
        VALUES (%s, %s, %s)
        RETURNING report_id
        """,
        (post_id, account["account_id"], reason),
    )
    report_id = cur.fetchone()["report_id"]
    cur.close()
    return {"report_id": report_id, "status": "open"}


def list_reports(conn, account) -> dict:
    account = _require(account)
    if not account.get("is_super_admin"):
        raise DocksideError(403, "Super admin required")
    cur = _cur(conn)
    cur.execute(
        """
        SELECT r.report_id, r.post_id, r.reason, r.created_at, r.status,
               p.topic_id, p.body, p.status AS post_status
        FROM public.dockside_reports r
        JOIN public.dockside_posts p ON p.post_id = r.post_id
        WHERE r.status = 'open'
        ORDER BY r.created_at DESC
        LIMIT 100
        """
    )
    rows = cur.fetchall()
    cur.close()
    return {
        "reports": [
            {
                "report_id": row["report_id"],
                "post_id": row["post_id"],
                "topic_id": row["topic_id"],
                "reason": row["reason"],
                "body": row["body"],
                "post_status": row["post_status"],
                "created_at": _iso(row["created_at"]),
            }
            for row in rows
        ]
    }


def moderate(conn, account, post_id, topic_id, action: str) -> dict:
    account = _require(account)
    if not account.get("is_super_admin"):
        raise DocksideError(403, "Super admin required")
    if action not in ("hide", "restore"):
        raise DocksideError(400, "Action must be hide or restore")
    status = "hidden" if action == "hide" else "visible"
    topic_status = "hidden" if action == "hide" else "open"
    cur = _cur(conn)
    if post_id:
        cur.execute(
            "UPDATE public.dockside_posts SET status = %s WHERE post_id = %s RETURNING post_id",
            (status if action == "hide" else "visible", int(post_id)),
        )
        if not cur.fetchone():
            raise DocksideError(404, "Comment not found")
        if action == "hide":
            cur.execute(
                "UPDATE public.dockside_reports SET status = 'closed' WHERE post_id = %s AND status = 'open'",
                (int(post_id),),
            )
    elif topic_id:
        cur.execute(
            "UPDATE public.dockside_topics SET status = %s WHERE topic_id = %s RETURNING topic_id",
            (topic_status, int(topic_id)),
        )
        if not cur.fetchone():
            raise DocksideError(404, "Topic not found")
    else:
        raise DocksideError(400, "A comment or topic is required")
    cur.close()
    return {"ok": True, "action": action}


def set_reaction(conn, account, post_id: int, kind: str) -> dict:
    account = _require(account)
    if kind not in ("up", "heart", "down"):
        raise DocksideError(400, "Reaction is invalid")
    cur = _cur(conn)
    cur.execute(
        """
        SELECT post_id FROM public.dockside_posts
        WHERE post_id = %s AND status = 'visible'
        """,
        (int(post_id),),
    )
    if not cur.fetchone():
        raise DocksideError(404, "Comment not found")
    cur.execute(
        """
        SELECT kind FROM public.dockside_reactions
        WHERE post_id = %s AND account_id = %s AND kind = %s
        """,
        (int(post_id), account["account_id"], kind),
    )
    if cur.fetchone():
        cur.execute(
            """
            DELETE FROM public.dockside_reactions
            WHERE post_id = %s AND account_id = %s AND kind = %s
            """,
            (int(post_id), account["account_id"], kind),
        )
    else:
        cur.execute(
            """
            INSERT INTO public.dockside_reactions (post_id, account_id, kind)
            VALUES (%s, %s, %s)
            """,
            (int(post_id), account["account_id"], kind),
        )
    reactions = _attach_reactions(cur, [{"post_id": int(post_id)}], account["account_id"])[0]["reactions"]
    cur.close()
    return {"post_id": int(post_id), "reactions": reactions}


def _json_body(payload):
    if not isinstance(payload, dict):
        raise DocksideError(400, "Expected a JSON object")
    return payload


def _token(request: Request) -> str:
    return (request.cookies.get("session") or "").strip()


def register_dockside_routes(app, get_db_connection, return_db_connection, is_super_admin=None):
    """Attach /api/dockside routes. is_super_admin is unused; role comes from the session row."""
    del is_super_admin

    def _run(handler):
        conn = get_db_connection()
        try:
            ensure_schema(conn)
            result = handler(conn)
            conn.commit()
            return result
        except DocksideError as exc:
            try:
                conn.rollback()
            except Exception:
                pass
            return JSONResponse({"detail": exc.detail}, status_code=exc.status)
        except HTTPException:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            print("[dockside] request failed", flush=True)
            raise
        finally:
            return_db_connection(conn)

    @app.get("/api/dockside/me")
    def dockside_me(request: Request):
        def handler(conn):
            account = session_account(conn, _token(request))
            if not account:
                return {"signed_in": False}
            return {
                "signed_in": True,
                "account_id": account["account_id"],
                "sas_id": account["sas_id"],
                "display_name": account["display_name"],
                "avatar_text": account.get("avatar_text"),
                "role": account["role"],
                "profile_url": account["profile_url"],
                "is_super_admin": account["is_super_admin"],
            }

        return _run(handler)

    @app.get("/api/dockside/current")
    def dockside_current(request: Request):
        def handler(conn):
            return current_topic(conn, session_account(conn, _token(request)))

        return _run(handler)

    @app.get("/api/dockside/topics")
    def dockside_topics(request: Request):
        q = request.query_params.get("q") or ""
        sort = request.query_params.get("sort") or "updated"
        direction = request.query_params.get("dir") or "desc"

        def handler(conn):
            return list_topics(conn, q, sort, direction)

        return _run(handler)

    @app.get("/api/dockside/topics/{topic_id}")
    def dockside_topic(topic_id: int, request: Request):
        def handler(conn):
            return get_topic(conn, topic_id, session_account(conn, _token(request)))

        return _run(handler)

    @app.post("/api/dockside/topics")
    async def dockside_create_topic(request: Request):
        payload = _json_body(await request.json())

        def handler(conn):
            account = session_account(conn, _token(request))
            return create_topic(conn, account, payload.get("subject"), payload.get("body"))

        return _run(handler)

    @app.post("/api/dockside/topics/{topic_id}/posts")
    async def dockside_add_post(topic_id: int, request: Request):
        payload = _json_body(await request.json())

        def handler(conn):
            account = session_account(conn, _token(request))
            return add_post(
                conn,
                account,
                topic_id,
                payload.get("body"),
                payload.get("parent_post_id"),
            )

        return _run(handler)

    @app.post("/api/dockside/posts/{post_id}/react")
    async def dockside_react(post_id: int, request: Request):
        payload = _json_body(await request.json())

        def handler(conn):
            return set_reaction(
                conn,
                session_account(conn, _token(request)),
                post_id,
                payload.get("kind"),
            )

        return _run(handler)

    @app.post("/api/dockside/topics/{topic_id}/follow")
    async def dockside_follow(topic_id: int, request: Request):
        payload = _json_body(await request.json())
        muted = bool(payload.get("muted"))

        def handler(conn):
            return set_muted(conn, session_account(conn, _token(request)), topic_id, muted)

        return _run(handler)

    @app.get("/api/dockside/notifications")
    def dockside_notifications(request: Request):
        def handler(conn):
            return list_notifications(conn, session_account(conn, _token(request)))

        return _run(handler)

    @app.post("/api/dockside/notifications/read")
    async def dockside_read(request: Request):
        payload = _json_body(await request.json())

        def handler(conn):
            return mark_read(
                conn,
                session_account(conn, _token(request)),
                payload.get("notification_ids"),
                bool(payload.get("all")),
            )

        return _run(handler)

    @app.post("/api/dockside/reports")
    async def dockside_report(request: Request):
        payload = _json_body(await request.json())

        def handler(conn):
            try:
                post_id = int(payload.get("post_id"))
            except (TypeError, ValueError):
                raise DocksideError(400, "A comment is required")
            return report_post(
                conn,
                session_account(conn, _token(request)),
                post_id,
                payload.get("reason"),
            )

        return _run(handler)

    @app.get("/api/dockside/reports")
    def dockside_reports(request: Request):
        def handler(conn):
            return list_reports(conn, session_account(conn, _token(request)))

        return _run(handler)

    @app.post("/api/dockside/moderate")
    async def dockside_moderate(request: Request):
        payload = _json_body(await request.json())

        def handler(conn):
            return moderate(
                conn,
                session_account(conn, _token(request)),
                payload.get("post_id"),
                payload.get("topic_id"),
                str(payload.get("action") or ""),
            )

        return _run(handler)
