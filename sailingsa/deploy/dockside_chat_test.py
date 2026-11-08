"""Rollback test for Dockside Chat. Leaves the empty tables, no visible comments."""
import os
import sys

import psycopg2
import psycopg2.extras

sys.path.insert(0, os.environ["DOCKSIDE_SRC"])
from sailingsa.backend.dockside_chat import (  # noqa: E402
    DocksideError,
    add_post,
    apply_schema,
    create_topic,
    current_topic,
    get_topic,
    list_notifications,
    list_topics,
    moderate,
    report_post,
    set_muted,
)

A = {"account_id": 19, "sas_id": "27159", "role": "sailor", "is_super_admin": False}
B = {"account_id": 20, "sas_id": "27159", "role": "sailor", "is_super_admin": False}
ADMIN = {"account_id": 1, "sas_id": "27160", "role": "super_admin", "is_super_admin": True}


def main() -> None:
    dsn = os.environ["DB_URL"]
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    apply_schema(conn)
    conn.close()

    conn = psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        try:
            create_topic(conn, None, "Too short", "body text")
            raise SystemExit("guest post was accepted")
        except DocksideError as exc:
            assert exc.status == 401, exc.detail
        try:
            create_topic(conn, A, None, " ")
            raise SystemExit("empty comment accepted")
        except DocksideError as exc:
            assert exc.status == 400, exc.detail
        conn.rollback()

        created = create_topic(conn, A, None, "Who is on the line")
        topic_id = created["topic_id"]
        first_id = created["posts"][0]["post_id"]
        notes = list_notifications(conn, A)
        assert notes["unread"] == 0, notes

        add_post(conn, A, topic_id, "Second comment", None)
        assert list_notifications(conn, A)["unread"] == 0

        replied = add_post(conn, B, topic_id, "I am on the line", first_id)
        assert replied["notified"] == 1, replied
        notes = list_notifications(conn, A)
        assert notes["unread"] == 1, notes
        assert notes["notifications"][0]["kind"] == "reply"
        assert notes["notifications"][0]["actor_name"]
        assert list_notifications(conn, B)["unread"] == 0

        set_muted(conn, A, topic_id, True)
        again = add_post(conn, B, topic_id, "Still here", None)
        assert again["notified"] == 0, again
        assert list_notifications(conn, A)["unread"] == 1

        found = list_topics(conn, "line", "subject", "asc")
        assert any(row["topic_id"] == topic_id for row in found["topics"]), found
        assert current_topic(conn)["topic"]["topic_id"] == topic_id

        reply_id = replied["post_id"]
        report_post(conn, A, reply_id, "Test report only")
        try:
            moderate(conn, A, reply_id, None, "hide")
            raise SystemExit("sailor was allowed to hide")
        except DocksideError as exc:
            assert exc.status == 403, exc.detail
        moderate(conn, ADMIN, reply_id, None, "hide")
        bodies = [post["body"] for post in get_topic(conn, topic_id)["posts"]]
        assert "I am on the line" not in bodies, bodies
        assert "Who is on the line" in bodies
        print("DOCKSIDE_TEST_OK")
    finally:
        conn.rollback()
        conn.close()

    check = psycopg2.connect(dsn)
    cur = check.cursor()
    cur.execute("SELECT COUNT(*) FROM public.dockside_topics")
    count = cur.fetchone()[0]
    cur.close()
    check.close()
    if count != 0:
        raise SystemExit(f"test rows left behind: {count}")
    print("DOCKSIDE_TEST_EMPTY")


if __name__ == "__main__":
    main()
