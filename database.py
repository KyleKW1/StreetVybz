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
