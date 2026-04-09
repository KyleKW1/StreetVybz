# database.py — hardened version with vice log + quiz result storage
"""
All DB functions in one place. Uses ssl_disabled=True for Streamlit Cloud.
If any individual query fails it returns a safe default rather than crashing.

Tables managed here:
  users            — existing
  password_resets  — existing
  vice_log         — NEW: per-user vice session entries
  quiz_results     — NEW: Read Between The Lines / What Would You Do results
"""

import json
import streamlit as st

try:
    import mysql.connector
    from mysql.connector import Error
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    from config import DB_CONFIG
except ImportError:
    DB_CONFIG = {}


# ─── CONNECTION ───────────────────────────────────────────────────────────────

def create_connection():
    if not MYSQL_AVAILABLE:
        return None
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG.get('host', ''),
            port=int(DB_CONFIG.get('port', 3306)),
            user=DB_CONFIG.get('user', ''),
            password=DB_CONFIG.get('password', ''),
            database=DB_CONFIG.get('database', ''),
            connection_timeout=30,
            autocommit=False,
            ssl_disabled=True,
        )
        return conn
    except Exception as e:
        st.error(f"DB connection error: {e}")
        return None


# ─── SCHEMA BOOTSTRAP ─────────────────────────────────────────────────────────

def ensure_tables():
    """
    Create the new tables if they don't already exist.
    Call this once at app startup (in main() after authentication succeeds).
    """
    conn = create_connection()
    if not conn:
        return

    ddl_statements = [
        # ── vice_log ──────────────────────────────────────────────────────────
        """
        CREATE TABLE IF NOT EXISTS vice_log (
            id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id     INT NOT NULL,
            vice        VARCHAR(32)  NOT NULL,          -- weed / alcohol / sex / other
            logged_at   DATETIME     NOT NULL,           -- when the session happened
            created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            details     JSON,                            -- vice-specific fields dict
            INDEX idx_vice_log_user  (user_id),
            INDEX idx_vice_log_time  (user_id, logged_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,

        # ── quiz_results ──────────────────────────────────────────────────────
        """
        CREATE TABLE IF NOT EXISTS quiz_results (
            id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id         INT NOT NULL,
            quiz_type       VARCHAR(32)  NOT NULL,       -- 'read_between_lines' | 'what_would_you_do'
            completed_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

            -- Read Between The Lines (desire profile)
            profile_name    VARCHAR(128),
            profile_meta    VARCHAR(255),
            dim_scores      JSON,                        -- {control:%, sensory:%, ...}
            recommendations JSON,                        -- list of rec strings
            total_pct       TINYINT UNSIGNED,

            -- What Would You Do (openness index)
            result_name     VARCHAR(128),
            result_meta     VARCHAR(255),
            openness_pct    TINYINT UNSIGNED,
            total_pts       SMALLINT UNSIGNED,

            -- Raw answers for deep analysis
            questions       LONGTEXT,                    -- JSON array of question objects
            answers         JSON,                        -- list of answer indices

            INDEX idx_quiz_user (user_id),
            INDEX idx_quiz_type (user_id, quiz_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
      """
      CREATE TABLE IF NOT EXISTS confessions (
          id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          code                VARCHAR(16) NOT NULL UNIQUE,
          sender_id           INT NOT NULL,
          recipient_id        INT NOT NULL,
          sender_questions    JSON NOT NULL,
          recipient_answers   JSON,
          recipient_questions JSON,
          sender_answers      JSON,
          status              VARCHAR(16) NOT NULL DEFAULT 'sent',
          created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          INDEX idx_conf_sender    (sender_id),
          INDEX idx_conf_recipient (recipient_id),
          INDEX idx_conf_code      (code)
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
      """,
    ]

    try:
        cur = conn.cursor()
        for ddl in ddl_statements:
            cur.execute(ddl)
        conn.commit()
        cur.close()
    except Exception as e:
        st.error(f"Schema bootstrap error: {e}")
    finally:
        conn.close()


# ─── USERS (existing) ─────────────────────────────────────────────────────────

def get_user_by_username(username: str):
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        return user
    except Exception as e:
        st.error(f"Error fetching user: {e}")
        return None
    finally:
        conn.close()


def get_user_by_email(email: str):
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        return user
    except Exception as e:
        st.error(f"Error fetching user: {e}")
        return None
    finally:
        conn.close()


def create_user(username: str, email: str, password_hash: str):
    conn = create_connection()
    if not conn:
        return False, "Database connection failed"
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, password_hash)
        )
        conn.commit()
        cur.close()
        return True, "Registration successful!"
    except mysql.connector.IntegrityError:
        return False, "Username or email already exists."
    except Exception as e:
        return False, f"Registration error: {e}"
    finally:
        conn.close()


def update_last_login(user_id: int) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
            (user_id,)
        )
        conn.commit()
        cur.close()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def update_user_password(user_id: int, new_password_hash: str) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (new_password_hash, user_id)
        )
        conn.commit()
        cur.close()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# ─── VICE LOG ─────────────────────────────────────────────────────────────────

def save_vice_entry(user_id: int, vice: str, logged_at, details: dict) -> int | None:
    """
    Insert a new vice log entry.
    Returns the new row id, or None on failure.
    """
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO vice_log (user_id, vice, logged_at, details)
               VALUES (%s, %s, %s, %s)""",
            (user_id, vice, logged_at, json.dumps(details, default=str))
        )
        conn.commit()
        new_id = cur.lastrowid
        cur.close()
        return new_id
    except Exception as e:
        st.error(f"Error saving vice entry: {e}")
        return None
    finally:
        conn.close()


def load_vice_log(user_id: int) -> list:
    """
    Load all vice log entries for a user, newest first.
    Returns a list of dicts compatible with the session_state vice_log format:
      [{"id", "vice", "timestamp", "data"}, ...]
    """
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT id, vice, logged_at, details
               FROM vice_log
               WHERE user_id = %s
               ORDER BY logged_at DESC""",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close()

        entries = []
        for row in rows:
            details = row["details"]
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except Exception:
                    details = {}
            entries.append({
                "id":        row["id"],
                "vice":      row["vice"],
                "timestamp": row["logged_at"].isoformat() if hasattr(row["logged_at"], "isoformat") else str(row["logged_at"]),
                "data":      details or {},
            })
        return entries
    except Exception as e:
        st.error(f"Error loading vice log: {e}")
        return []
    finally:
        conn.close()


def delete_vice_log(user_id: int) -> bool:
    """Delete all vice log entries for a user (used by 'Clear all history')."""
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM vice_log WHERE user_id = %s", (user_id,))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error deleting vice log: {e}")
        return False
    finally:
        conn.close()


# ─── QUIZ RESULTS ─────────────────────────────────────────────────────────────

def save_read_between_lines_result(
    user_id:         int,
    profile_name:    str,
    profile_meta:    str,
    dim_scores:      dict,       # {dim_key: pct, ...}
    recommendations: list,       # [str, ...]
    total_pct:       int,
    questions:       list,       # full question objects
    answers:         list,       # answer indices
) -> bool:
    """Save a completed 'Read Between The Lines' quiz result."""
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO quiz_results
               (user_id, quiz_type, profile_name, profile_meta,
                dim_scores, recommendations, total_pct, questions, answers)
               VALUES (%s, 'read_between_lines', %s, %s, %s, %s, %s, %s, %s)""",
            (
                user_id,
                profile_name,
                profile_meta,
                json.dumps(dim_scores),
                json.dumps(recommendations),
                total_pct,
                json.dumps(questions, default=str),
                json.dumps(answers),
            )
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error saving quiz result: {e}")
        return False
    finally:
        conn.close()


def save_what_would_you_do_result(
    user_id:      int,
    result_name:  str,
    result_meta:  str,
    openness_pct: int,
    total_pts:    int,
    questions:    list,
    answers:      list,
) -> bool:
    """Save a completed 'What Would You Do?' quiz result."""
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO quiz_results
               (user_id, quiz_type, result_name, result_meta,
                openness_pct, total_pts, questions, answers)
               VALUES (%s, 'what_would_you_do', %s, %s, %s, %s, %s, %s)""",
            (
                user_id,
                result_name,
                result_meta,
                openness_pct,
                total_pts,
                json.dumps(questions, default=str),
                json.dumps(answers),
            )
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error saving WWYD result: {e}")
        return False
    finally:
        conn.close()


def load_quiz_history(user_id: int, quiz_type: str | None = None) -> list:
    """
    Load past quiz results for a user.
    quiz_type: 'read_between_lines' | 'what_would_you_do' | None (all)
    """
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        if quiz_type:
            cur.execute(
                """SELECT * FROM quiz_results
                   WHERE user_id = %s AND quiz_type = %s
                   ORDER BY completed_at DESC""",
                (user_id, quiz_type)
            )
        else:
            cur.execute(
                """SELECT * FROM quiz_results
                   WHERE user_id = %s
                   ORDER BY completed_at DESC""",
                (user_id,)
            )
        rows = cur.fetchall()
        cur.close()

        # Parse JSON columns
        json_cols = ("dim_scores", "recommendations", "answers")
        for row in rows:
            for col in json_cols:
                if row.get(col) and isinstance(row[col], str):
                    try:
                        row[col] = json.loads(row[col])
                    except Exception:
                        pass
            # questions can be very large — parse only if needed
            if row.get("questions") and isinstance(row["questions"], str):
                try:
                    row["questions"] = json.loads(row["questions"])
                except Exception:
                    row["questions"] = []

        return rows
    except Exception as e:
        st.error(f"Error loading quiz history: {e}")
        return []
    finally:
        conn.close()

# ─────────────────────────────────────────────────────────────────────────────
# Paste all of this into database.py
# Also add the DDL string below to the ddl_statements list in ensure_tables()
# ─────────────────────────────────────────────────────────────────────────────

# ── DDL (add to ensure_tables ddl_statements list) ───────────────────────────
"""
CREATE TABLE IF NOT EXISTS confessions (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code                VARCHAR(16)  NOT NULL UNIQUE,
    sender_id           INT          NOT NULL,
    recipient_id        INT          NOT NULL,

    sender_questions    JSON         NOT NULL,          -- what sender asks recipient

    recipient_questions JSON         DEFAULT NULL,      -- what recipient asks sender (submitted blind)
    recipient_answers   JSON         DEFAULT NULL,      -- recipient's answers to sender_questions
    sender_answers      JSON         DEFAULT NULL,      -- sender's answers to recipient_questions

    -- sent        : waiting for recipient to write their questions (blind)
    -- questioning : recipient wrote questions; now answering sender's
    -- responded   : recipient answered sender's questions; waiting for sender
    -- revealed    : sender answered; full exchange visible to both
    status              VARCHAR(16)  NOT NULL DEFAULT 'sent',

    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_conf_sender    (sender_id),
    INDEX idx_conf_recipient (recipient_id),
    INDEX idx_conf_code      (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
""",


# ── FUNCTIONS (paste into database.py) ───────────────────────────────────────

import json   # already imported at top of database.py — just shown for clarity


def save_confession(sender_id: int, recipient_id: int, code: str, questions: list) -> bool:
    """Create a new confession exchange. status='sent'."""
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO confessions (code, sender_id, recipient_id, sender_questions, status)
               VALUES (%s, %s, %s, %s, 'sent')""",
            (code, sender_id, recipient_id, json.dumps(questions))
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        import streamlit as st; st.error(f"Error saving confession: {e}")
        return False
    finally:
        conn.close()


def get_confession_by_code(code: str):
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT c.*, s.username AS sender_username, r.username AS recipient_username
               FROM confessions c
               JOIN users s ON s.id = c.sender_id
               JOIN users r ON r.id = c.recipient_id
               WHERE c.code = %s""",
            (code,)
        )
        row = cur.fetchone()
        cur.close()
        return _parse_confession_row(row)
    except Exception:
        return None
    finally:
        conn.close()


def load_confessions_inbox(user_id: int) -> list:
    """Confessions where this user is the RECIPIENT, newest first."""
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT c.*, s.username AS sender_username, r.username AS recipient_username
               FROM confessions c
               JOIN users s ON s.id = c.sender_id
               JOIN users r ON r.id = c.recipient_id
               WHERE c.recipient_id = %s
               ORDER BY c.created_at DESC""",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close()
        return [_parse_confession_row(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def load_confessions_outbox(user_id: int) -> list:
    """Confessions where this user is the SENDER, newest first."""
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT c.*, s.username AS sender_username, r.username AS recipient_username
               FROM confessions c
               JOIN users s ON s.id = c.sender_id
               JOIN users r ON r.id = c.recipient_id
               WHERE c.sender_id = %s
               ORDER BY c.created_at DESC""",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close()
        return [_parse_confession_row(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def confession_recipient_submit_questions(code: str, recipient_questions: list) -> bool:
    """
    STEP 1 (recipient): submit their questions blind, without having seen sender's.
    Transition: sent → questioning
    """
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE confessions
               SET recipient_questions = %s,
                   status              = 'questioning'
               WHERE code = %s AND status = 'sent'""",
            (json.dumps(recipient_questions), code)
        )
        conn.commit()
        changed = cur.rowcount > 0
        cur.close()
        return changed
    except Exception as e:
        import streamlit as st; st.error(f"Error submitting questions: {e}")
        return False
    finally:
        conn.close()


def confession_recipient_answer(code: str, recipient_answers: list) -> bool:
    """
    STEP 2 (recipient): answer the sender's now-visible questions.
    Transition: questioning → responded
    """
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE confessions
               SET recipient_answers = %s,
                   status            = 'responded'
               WHERE code = %s AND status = 'questioning'""",
            (json.dumps(recipient_answers), code)
        )
        conn.commit()
        changed = cur.rowcount > 0
        cur.close()
        return changed
    except Exception as e:
        import streamlit as st; st.error(f"Error saving answers: {e}")
        return False
    finally:
        conn.close()


def confession_sender_answer(code: str, sender_answers: list) -> bool:
    """
    FINAL STEP (sender): answer recipient's questions.
    Transition: responded → revealed  (both sides unlock simultaneously)
    """
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE confessions
               SET sender_answers = %s,
                   status         = 'revealed'
               WHERE code = %s AND status = 'responded'""",
            (json.dumps(sender_answers), code)
        )
        conn.commit()
        changed = cur.rowcount > 0
        cur.close()
        return changed
    except Exception as e:
        import streamlit as st; st.error(f"Error revealing confession: {e}")
        return False
    finally:
        conn.close()


def _parse_confession_row(row):
    """Parse all JSON columns in a confession DB row."""
    if not row:
        return None
    for col in ("sender_questions", "recipient_questions", "recipient_answers", "sender_answers"):
        val = row.get(col)
        if val and isinstance(val, str):
            try:
                row[col] = json.loads(val)
            except Exception:
                row[col] = []
        elif val is None:
            row[col] = []
    return row



# ── 1. Delete a confession by code ────────────────────────────────────────────
def delete_confession(code: str) -> bool:
    """
    Hard-delete the confession row (and any related answers/questions) by code.
    Screenshot alert rows are in a SEPARATE table and are NOT deleted here —
    they survive so the victim can still see the notification.
    """
    # Example (adapt to your ORM / raw SQL):
    # db.execute("DELETE FROM confessions WHERE code = %s", (code,))
    # db.commit()
    raise NotImplementedError("Implement this in your database.py")
 
 
# ── 2. Invalidate all sessions for a user (force logout) ─────────────────────
def invalidate_user_sessions(user_id: int) -> None:
    """
    Delete / expire all session tokens for the given user so they can't
    silently stay logged in after a screenshot.
    If you use Streamlit's built-in session state only (no server-side tokens),
    this is a no-op — the client-side _force_logout() already clears state.
    """
    # Example:
    # db.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
    # db.commit()
    pass

"""
database_additions.py
─────────────────────
Add these functions to your existing database.py.

They support:
  1. Hard-deleting a confession after the 60-second revealed timer expires
  2. Saving / loading / dismissing screenshot reports (separate table,
     survives confession deletion)

Required new DB table:

  CREATE TABLE screenshot_alerts (
      id                        SERIAL PRIMARY KEY,
      confession_code           TEXT,
      reporter_id               INTEGER,
      reporter_username         TEXT NOT NULL,   -- person who pressed Report
      accused_username          TEXT NOT NULL,   -- person allegedly screenshotting
      alert_recipient_username  TEXT NOT NULL,   -- person who SEES the alert
      dismissed                 BOOLEAN DEFAULT FALSE,
      created_at                TIMESTAMPTZ DEFAULT NOW()
  );
"""


# ── 1. Hard-delete a confession ───────────────────────────────────────────────
def delete_confession(code: str) -> bool:
    """
    Delete the confession row and any child rows (answers, questions) by code.
    Screenshot alert rows live in a separate table and are NOT deleted here —
    they must survive so the victim continues to see the notification.

    Example (adapt to your ORM / raw SQL):
        cur.execute("DELETE FROM confessions WHERE code = %s", (code,))
        conn.commit()
        return True
    """
    raise NotImplementedError("Implement in database.py")


# ── 2. Save a screenshot alert ────────────────────────────────────────────────
def save_screenshot_alert(
    confession_code: str,
    reporter_id: int,
    reporter_username: str,
    accused_username: str,
    alert_recipient_username: str,
) -> bool:
    """
    Insert a row into screenshot_alerts.

    reporter_username        — person who pressed the Report button
    accused_username         — person being reported (allegedly took the screenshot)
    alert_recipient_username — person who will see the alert banner
                               (usually the accused's exchange partner, i.e. the reporter)

    Returns True on success.

    Example:
        cur.execute(
            \"\"\"INSERT INTO screenshot_alerts
               (confession_code, reporter_id, reporter_username,
                accused_username, alert_recipient_username)
               VALUES (%s, %s, %s, %s, %s)\"\"\",
            (confession_code, reporter_id, reporter_username,
             accused_username, alert_recipient_username)
        )
        conn.commit()
        return True
    """
    raise NotImplementedError("Implement in database.py")


# ── 3. Load screenshot alerts for a user ─────────────────────────────────────
def load_screenshot_alerts(user_id: int) -> list:
    """
    Return all non-dismissed screenshot_alerts rows where
    alert_recipient_username matches this user's username.

    (Match on username, or add an alert_recipient_id column if you prefer.)

    Returns list of dicts, e.g.:
      [
        {
          "id": 1,
          "reporter_username": "alice",
          "accused_username":  "bob",
          "created_at":        datetime(...),
          "dismissed":         False,
        },
        ...
      ]

    Example:
        username = get_username_by_id(user_id)
        rows = cur.execute(
            \"\"\"SELECT id, reporter_username, accused_username, created_at
               FROM screenshot_alerts
               WHERE alert_recipient_username = %s
                 AND dismissed = FALSE
               ORDER BY created_at DESC\"\"\",
            (username,)
        ).fetchall()
        return [dict(r) for r in rows]
    """
    raise NotImplementedError("Implement in database.py")


# ── 4. Dismiss a screenshot alert ─────────────────────────────────────────────
def dismiss_screenshot_alert(alert_id: int) -> bool:
    """
    Mark the alert as dismissed so it stops appearing in the banner.

    Example:
        cur.execute(
            "UPDATE screenshot_alerts SET dismissed=TRUE WHERE id=%s",
            (alert_id,)
        )
        conn.commit()
        return True
    """
    raise NotImplementedError("Implement in database.py")
