"""
social_db.py — Storage for meeting people: profiles, swipes, matches,
blind Q&A, chat, blocks/reports and Tonight check-ins.

Uses the shared connection pool from database.py.
"""

import json
from datetime import datetime, timedelta

from database import create_connection

PROFILE_FIELDS = (
    "birthdate", "gender", "show_me", "intent", "bio", "weed", "drink", "party",
    "city", "location_mode", "lat", "lon", "max_km", "age_min", "age_max", "hidden",
)
REQUIRED_FIELDS = ("birthdate", "intent", "city", "weed", "drink", "party")

_DDL = [
    """CREATE TABLE IF NOT EXISTS profiles (
        user_id       INT PRIMARY KEY,
        birthdate     DATE,
        gender        VARCHAR(20),
        show_me       VARCHAR(20)  DEFAULT 'Everyone',
        intent        VARCHAR(10),
        bio           VARCHAR(300),
        weed          TINYINT,
        drink         TINYINT,
        party         TINYINT,
        city          VARCHAR(100),
        location_mode VARCHAR(8)   DEFAULT 'city',
        lat           DOUBLE,
        lon           DOUBLE,
        max_km        SMALLINT     DEFAULT 25,
        age_min       TINYINT UNSIGNED DEFAULT 18,
        age_max       TINYINT UNSIGNED DEFAULT 99,
        hidden        TINYINT(1)   NOT NULL DEFAULT 0,
        updated_at    DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_profiles_city (city)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS swipes (
        swiper_id  INT NOT NULL,
        target_id  INT NOT NULL,
        liked      TINYINT(1) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (swiper_id, target_id),
        INDEX idx_swipes_target (target_id, liked)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS matches (
        id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        user_a      INT NOT NULL,
        user_b      INT NOT NULL,
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        a_questions JSON, b_questions JSON,
        a_answers   JSON, b_answers   JSON,
        UNIQUE KEY uq_match_pair (user_a, user_b),
        INDEX idx_match_b (user_b)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS messages (
        id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        match_id   BIGINT UNSIGNED NOT NULL,
        sender_id  INT NOT NULL,
        body       VARCHAR(1000) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_messages_match (match_id, id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS blocks (
        blocker_id INT NOT NULL,
        blocked_id INT NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (blocker_id, blocked_id),
        INDEX idx_blocks_blocked (blocked_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS reports (
        id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        reporter_id INT NOT NULL,
        reported_id INT NOT NULL,
        reason      VARCHAR(64) NOT NULL,
        details     VARCHAR(1000),
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_reports_reported (reported_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS checkins (
        user_id    INT NOT NULL,
        night      DATE NOT NULL,
        spot       VARCHAR(255) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, night),
        INDEX idx_checkins_night (night, spot)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]


# ─── PLUMBING ─────────────────────────────────────────────────────────────────

def _run(fn, default=None):
    """Open a connection, run fn(conn), always close. Any error → default."""
    conn = create_connection()
    if not conn:
        return default
    try:
        return fn(conn)
    except Exception as e:
        print(f"[social_db] {getattr(fn, '__name__', 'query')}: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return default
    finally:
        conn.close()


def _fetchall(sql, params=(), default=None):
    def q(conn):
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    return _run(q, [] if default is None else default)


def _fetchone(sql, params=()):
    rows = _fetchall(sql, params)
    return rows[0] if rows else None


def _write(sql, params=()):
    """Execute one write. Returns rowcount (≥0) on success, None on failure."""
    def q(conn):
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        n = cur.rowcount
        cur.close()
        return n
    return _run(q, None)


def _json(v, default=None):
    if v is None:
        return default
    if isinstance(v, (list, dict)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return default


def ensure_social_tables() -> bool:
    def q(conn):
        cur = conn.cursor()
        for ddl in _DDL:
            cur.execute(ddl)
        conn.commit()
        cur.close()
        return True
    return bool(_run(q, False))


def tonight() -> str:
    """The current 'night' — a night out runs until 6am the next morning."""
    return (datetime.now() - timedelta(hours=6)).date().isoformat()


# ─── PROFILES ─────────────────────────────────────────────────────────────────

def get_profile(user_id: int) -> dict | None:
    return _fetchone(
        """SELECT p.*, u.username FROM profiles p JOIN users u ON u.id = p.user_id
           WHERE p.user_id = %s""", (user_id,))


def profile_complete(profile: dict | None) -> bool:
    return bool(profile) and all(profile.get(f) is not None and profile.get(f) != ""
                                 for f in REQUIRED_FIELDS)


def save_profile(user_id: int, fields: dict) -> bool:
    fields = {k: v for k, v in fields.items() if k in PROFILE_FIELDS}
    if not fields:
        return True
    cols = ", ".join(fields)
    marks = ", ".join(["%s"] * len(fields))
    updates = ", ".join(f"{k} = VALUES({k})" for k in fields)
    return _write(
        f"INSERT INTO profiles (user_id, {cols}) VALUES (%s, {marks}) "
        f"ON DUPLICATE KEY UPDATE {updates}",
        (user_id, *fields.values()),
    ) is not None


# ─── DISCOVER ────────────────────────────────────────────────────────────────

def load_candidate_pool(user_id: int, limit: int = 500) -> list:
    """Visible profiles this user hasn't swiped on and has no block with."""
    rows = _fetchall(
        """SELECT p.*, u.username FROM profiles p
           JOIN users u ON u.id = p.user_id
           WHERE p.user_id <> %s AND p.hidden = 0
             AND p.birthdate IS NOT NULL AND p.intent IS NOT NULL AND p.city IS NOT NULL
             AND p.weed IS NOT NULL AND p.drink IS NOT NULL AND p.party IS NOT NULL
             AND NOT EXISTS (SELECT 1 FROM swipes s
                             WHERE s.swiper_id = %s AND s.target_id = p.user_id)
             AND NOT EXISTS (SELECT 1 FROM blocks b
                             WHERE (b.blocker_id = %s AND b.blocked_id = p.user_id)
                                OR (b.blocker_id = p.user_id AND b.blocked_id = %s))
           ORDER BY p.updated_at DESC
           LIMIT %s""",
        (user_id, user_id, user_id, user_id, limit),
    )
    quiz = load_quiz_summaries([r["user_id"] for r in rows])
    for r in rows:
        r["quiz"] = quiz.get(r["user_id"])
    return rows


def load_quiz_summaries(user_ids: list) -> dict:
    """Latest Read Between The Lines result per user, reduced to what matching uses."""
    if not user_ids:
        return {}
    marks = ", ".join(["%s"] * len(user_ids))
    rows = _fetchall(
        f"""SELECT q.user_id, q.result_name, q.openness_pct, q.dim_scores
            FROM quiz_results q
            JOIN (SELECT user_id, MAX(id) AS max_id FROM quiz_results
                  WHERE quiz_type LIKE 'rbtl_v4_%%' AND user_id IN ({marks})
                  GROUP BY user_id) latest ON latest.max_id = q.id""",
        tuple(user_ids),
    )
    out = {}
    for r in rows:
        dims = _json(r.get("dim_scores"), {}) or {}
        raw = dims.get("hd_signals") or ""
        signals = [] if raw in ("", "none") else [s.split(":")[0].strip() for s in raw.split(",") if s.strip()]
        out[r["user_id"]] = {
            "result": r.get("result_name") or None,
            "openness": r.get("openness_pct"),
            "signals": signals,
            "categories": dims.get("selected") or [],
        }
    return out


def record_swipe(user_id: int, target_id: int, liked: bool) -> int | None:
    """Save a like/pass. Returns the match id when this like makes it mutual."""
    def q(conn):
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO swipes (swiper_id, target_id, liked) VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE liked = VALUES(liked), created_at = NOW()""",
            (user_id, target_id, int(liked)),
        )
        match_id = None
        if liked:
            cur.execute("SELECT 1 FROM swipes WHERE swiper_id = %s AND target_id = %s AND liked = 1",
                        (target_id, user_id))
            if cur.fetchone():
                a, b = sorted((user_id, target_id))
                cur.execute("INSERT IGNORE INTO matches (user_a, user_b) VALUES (%s, %s)", (a, b))
                cur.execute("SELECT id FROM matches WHERE user_a = %s AND user_b = %s", (a, b))
                row = cur.fetchone()
                match_id = row[0] if row else None
        conn.commit()
        cur.close()
        return match_id
    return _run(q, None)


def reset_passes(user_id: int) -> bool:
    """Give passed profiles another chance to appear in Discover."""
    return _write("DELETE FROM swipes WHERE swiper_id = %s AND liked = 0", (user_id,)) is not None


# ─── MATCHES + BLIND Q&A ─────────────────────────────────────────────────────

def _side(row: dict, user_id: int) -> tuple[str, str]:
    return ("a", "b") if row["user_a"] == user_id else ("b", "a")


def qa_stage(row: dict, user_id: int) -> str:
    """Where this user is in the blind Q&A for a match.

    write → wait_questions → answer → wait_answers → open (chat unlocked)
    """
    me, them = _side(row, user_id)
    if not _json(row.get(f"{me}_questions")):
        return "write"
    if not _json(row.get(f"{them}_questions")):
        return "wait_questions"
    if not _json(row.get(f"{me}_answers")):
        return "answer"
    if not _json(row.get(f"{them}_answers")):
        return "wait_answers"
    return "open"


def match_view(row: dict, user_id: int) -> dict:
    """A match row from this user's point of view."""
    me, them = _side(row, user_id)
    return {
        "id":              row["id"],
        "other_id":        row[f"user_{them}"],
        "other_name":      row.get("other_name", ""),
        "created_at":      row.get("created_at"),
        "stage":           qa_stage(row, user_id),
        "my_questions":    _json(row.get(f"{me}_questions"), []),
        "their_questions": _json(row.get(f"{them}_questions"), []),
        "my_answers":      _json(row.get(f"{me}_answers"), []),
        "their_answers":   _json(row.get(f"{them}_answers"), []),
        "last_message":    row.get("last_message"),
        "last_at":         row.get("last_at"),
        "last_sender":     row.get("last_sender"),
    }


def load_matches(user_id: int) -> list:
    rows = _fetchall(
        """SELECT m.*, u.username AS other_name,
                  lm.body AS last_message, lm.created_at AS last_at, lm.sender_id AS last_sender
           FROM matches m
           JOIN users u ON u.id = IF(m.user_a = %s, m.user_b, m.user_a)
           LEFT JOIN messages lm ON lm.id = (SELECT MAX(id) FROM messages WHERE match_id = m.id)
           WHERE m.user_a = %s OR m.user_b = %s
           ORDER BY COALESCE(lm.created_at, m.created_at) DESC""",
        (user_id, user_id, user_id),
    )
    return [match_view(r, user_id) for r in rows]


def get_match(match_id: int, user_id: int) -> dict | None:
    """A single match — only if this user is part of it."""
    row = _fetchone(
        """SELECT m.*, u.username AS other_name FROM matches m
           JOIN users u ON u.id = IF(m.user_a = %s, m.user_b, m.user_a)
           WHERE m.id = %s AND (m.user_a = %s OR m.user_b = %s)""",
        (user_id, match_id, user_id, user_id),
    )
    return match_view(row, user_id) if row else None


def has_match(user_id: int) -> bool:
    return bool(_fetchone("SELECT 1 AS x FROM matches WHERE user_a = %s OR user_b = %s LIMIT 1",
                          (user_id, user_id)))


def _save_qa(match_id: int, user_id: int, kind: str, items: list) -> bool:
    """Write my questions/answers once — they can't be changed after."""
    col_a, col_b = f"a_{kind}", f"b_{kind}"
    n = _write(
        f"""UPDATE matches SET
              {col_a} = IF(user_a = %s AND {col_a} IS NULL, %s, {col_a}),
              {col_b} = IF(user_b = %s AND {col_b} IS NULL, %s, {col_b})
            WHERE id = %s AND (user_a = %s OR user_b = %s)""",
        (user_id, json.dumps(items), user_id, json.dumps(items), match_id, user_id, user_id),
    )
    return bool(n)


def save_questions(match_id: int, user_id: int, questions: list) -> bool:
    return _save_qa(match_id, user_id, "questions", questions)


def save_answers(match_id: int, user_id: int, answers: list) -> bool:
    m = get_match(match_id, user_id)
    if not m or m["stage"] != "answer":
        return False
    return _save_qa(match_id, user_id, "answers", answers)


def unmatch(match_id: int, user_id: int) -> bool:
    m = get_match(match_id, user_id)
    if not m:
        return False
    _write("DELETE FROM messages WHERE match_id = %s", (match_id,))
    return bool(_write("DELETE FROM matches WHERE id = %s", (match_id,)))


# ─── CHAT ────────────────────────────────────────────────────────────────────

def load_messages(match_id: int, user_id: int, limit: int = 100) -> list:
    rows = _fetchall(
        """SELECT msg.id, msg.sender_id, msg.body, msg.created_at FROM messages msg
           JOIN matches m ON m.id = msg.match_id
           WHERE msg.match_id = %s AND (m.user_a = %s OR m.user_b = %s)
           ORDER BY msg.id DESC LIMIT %s""",
        (match_id, user_id, user_id, limit),
    )
    return list(reversed(rows))


def send_message(match_id: int, user_id: int, body: str) -> bool:
    body = (body or "").strip()[:1000]
    m = get_match(match_id, user_id)
    if not body or not m or m["stage"] != "open":
        return False
    return bool(_write("INSERT INTO messages (match_id, sender_id, body) VALUES (%s, %s, %s)",
                       (match_id, user_id, body)))


# ─── SAFETY ──────────────────────────────────────────────────────────────────

def block_user(user_id: int, target_id: int) -> bool:
    """Block someone: they vanish from each other's Discover and any match ends."""
    ok = _write("INSERT IGNORE INTO blocks (blocker_id, blocked_id) VALUES (%s, %s)",
                (user_id, target_id)) is not None
    a, b = sorted((user_id, target_id))
    row = _fetchone("SELECT id FROM matches WHERE user_a = %s AND user_b = %s", (a, b))
    if row:
        _write("DELETE FROM messages WHERE match_id = %s", (row["id"],))
        _write("DELETE FROM matches WHERE id = %s", (row["id"],))
    return ok


def unblock_user(user_id: int, target_id: int) -> bool:
    return _write("DELETE FROM blocks WHERE blocker_id = %s AND blocked_id = %s",
                  (user_id, target_id)) is not None


def load_blocked(user_id: int) -> list:
    return _fetchall(
        """SELECT b.blocked_id AS user_id, u.username FROM blocks b
           JOIN users u ON u.id = b.blocked_id WHERE b.blocker_id = %s
           ORDER BY b.created_at DESC""", (user_id,))


def report_user(user_id: int, target_id: int, reason: str, details: str = "") -> bool:
    return _write(
        "INSERT INTO reports (reporter_id, reported_id, reason, details) VALUES (%s, %s, %s, %s)",
        (user_id, target_id, reason[:64], (details or "")[:1000]),
    ) is not None


# ─── TONIGHT ─────────────────────────────────────────────────────────────────

def check_in(user_id: int, spot: str) -> bool:
    return _write(
        """INSERT INTO checkins (user_id, night, spot) VALUES (%s, %s, %s)
           ON DUPLICATE KEY UPDATE spot = VALUES(spot), created_at = NOW()""",
        (user_id, tonight(), spot[:255]),
    ) is not None


def clear_check_in(user_id: int) -> bool:
    return _write("DELETE FROM checkins WHERE user_id = %s AND night = %s",
                  (user_id, tonight())) is not None


def my_check_in(user_id: int) -> str | None:
    row = _fetchone("SELECT spot FROM checkins WHERE user_id = %s AND night = %s",
                    (user_id, tonight()))
    return row["spot"] if row else None


def tonight_by_spot(user_id: int) -> dict:
    """{spot: {"count": everyone going, "matches": [names of my matches going]}}"""
    rows = _fetchall(
        """SELECT c.spot, c.user_id, u.username,
                  EXISTS (SELECT 1 FROM matches m
                          WHERE (m.user_a = %s AND m.user_b = c.user_id)
                             OR (m.user_b = %s AND m.user_a = c.user_id)) AS is_match
           FROM checkins c JOIN users u ON u.id = c.user_id
           WHERE c.night = %s""",
        (user_id, user_id, tonight()),
    )
    out = {}
    for r in rows:
        spot = out.setdefault(r["spot"], {"count": 0, "matches": []})
        spot["count"] += 1
        if r["is_match"]:
            spot["matches"].append(r["username"])
    return out


# ─── ACCOUNT ─────────────────────────────────────────────────────────────────

def export_social_data(user_id: int) -> dict:
    profile = get_profile(user_id) or {}
    return {
        "profile": {k: str(v) if v is not None else None for k, v in profile.items()},
        "matches": [{k: str(v) for k, v in m.items()} for m in load_matches(user_id)],
    }


def delete_social_data(user_id: int) -> None:
    rows = _fetchall("SELECT id FROM matches WHERE user_a = %s OR user_b = %s", (user_id, user_id))
    for r in rows:
        _write("DELETE FROM messages WHERE match_id = %s", (r["id"],))
    for sql in (
        "DELETE FROM matches  WHERE user_a = %s OR user_b = %s",
        "DELETE FROM swipes   WHERE swiper_id = %s OR target_id = %s",
        "DELETE FROM blocks   WHERE blocker_id = %s OR blocked_id = %s",
    ):
        _write(sql, (user_id, user_id))
    _write("DELETE FROM checkins WHERE user_id = %s", (user_id,))
    _write("DELETE FROM profiles WHERE user_id = %s", (user_id,))
