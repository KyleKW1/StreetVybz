# database.py
import json
import streamlit as st

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    from config import DB_CONFIG
except ImportError:
    DB_CONFIG = {}


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


def ensure_tables():
    conn = create_connection()
    if not conn:
        return

    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS vice_log (
            id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id     INT NOT NULL,
            vice        VARCHAR(32)  NOT NULL,
            logged_at   DATETIME     NOT NULL,
            created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            details     JSON,
            INDEX idx_vice_log_user (user_id),
            INDEX idx_vice_log_time (user_id, logged_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS quiz_results (
            id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id         INT NOT NULL,
            quiz_type       VARCHAR(32)  NOT NULL,
            completed_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            profile_name    VARCHAR(128),
            profile_meta    VARCHAR(255),
            dim_scores      JSON,
            recommendations JSON,
            total_pct       TINYINT UNSIGNED,
            result_name     VARCHAR(128),
            result_meta     VARCHAR(255),
            openness_pct    TINYINT UNSIGNED,
            total_pts       SMALLINT UNSIGNED,
            questions       LONGTEXT,
            answers         JSON,
            INDEX idx_quiz_user (user_id),
            INDEX idx_quiz_type (user_id, quiz_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS confessions (
            id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            code                VARCHAR(16) NOT NULL UNIQUE,
            sender_id           INT NOT NULL,
            recipient_id        INT          DEFAULT NULL,
            recipient_email     VARCHAR(255) DEFAULT NULL,
            sender_questions    JSON NOT NULL,
            recipient_answers   JSON,
            recipient_questions JSON,
            sender_answers      JSON,
            status              VARCHAR(16) NOT NULL DEFAULT 'sent',
            revealed_at         DATETIME    DEFAULT NULL,
            created_at          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_conf_sender    (sender_id),
            INDEX idx_conf_recipient (recipient_id),
            INDEX idx_conf_code      (code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS screenshot_alerts (
            id                      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            confession_code         VARCHAR(16),
            screenshotter_id        INT NOT NULL,
            screenshotter_username  VARCHAR(128) NOT NULL,
            other_username          VARCHAR(128) NOT NULL,
            dismissed               TINYINT(1) NOT NULL DEFAULT 0,
            created_at              DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_sa_other     (other_username),
            INDEX idx_sa_dismissed (other_username, dismissed)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ]

    try:
        cur = conn.cursor()
        for ddl in ddl_statements:
            cur.execute(ddl)
        conn.commit()

        # Add revealed_at to existing confessions table if missing
        try:
            cur.execute("ALTER TABLE confessions ADD COLUMN revealed_at DATETIME DEFAULT NULL")
            conn.commit()
        except Exception:
            pass  # column already exists — fine

        # Make recipient_id nullable for email-invite confessions
        try:
            cur.execute("ALTER TABLE confessions MODIFY COLUMN recipient_id INT DEFAULT NULL")
            conn.commit()
        except Exception:
            pass

        # Add recipient_email column if missing
        try:
            cur.execute("ALTER TABLE confessions ADD COLUMN recipient_email VARCHAR(255) DEFAULT NULL")
            conn.commit()
        except Exception:
            pass

        cur.close()
    except Exception as e:
        st.error(f"Schema bootstrap error: {e}")
    finally:
        conn.close()


# ─── USERS ────────────────────────────────────────────────────────────────────

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
        cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user_id,))
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
        cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_password_hash, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# ─── VICE LOG ─────────────────────────────────────────────────────────────────

def save_vice_entry(user_id: int, vice: str, logged_at, details: dict):
    conn = create_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO vice_log (user_id, vice, logged_at, details) VALUES (%s, %s, %s, %s)",
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
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, vice, logged_at, details FROM vice_log WHERE user_id = %s ORDER BY logged_at DESC",
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

def save_read_between_lines_result(user_id, profile_name, profile_meta, dim_scores,
                                    recommendations, total_pct, questions, answers) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO quiz_results
               (user_id, quiz_type, profile_name, profile_meta, dim_scores,
                recommendations, total_pct, questions, answers)
               VALUES (%s, 'read_between_lines', %s, %s, %s, %s, %s, %s, %s)""",
            (user_id, profile_name, profile_meta, json.dumps(dim_scores),
             json.dumps(recommendations), total_pct,
             json.dumps(questions, default=str), json.dumps(answers))
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error saving quiz result: {e}")
        return False
    finally:
        conn.close()


def save_what_would_you_do_result(user_id, result_name, result_meta,
                                   openness_pct, total_pts, questions, answers) -> bool:
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
            (user_id, result_name, result_meta, openness_pct, total_pts,
             json.dumps(questions, default=str), json.dumps(answers))
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error saving WWYD result: {e}")
        return False
    finally:
        conn.close()


# ─── CONFESSIONS ──────────────────────────────────────────────────────────────

def save_confession(sender_id: int, recipient_id: int, code: str, questions: list) -> bool:
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
        st.error(f"Error saving confession: {e}")
        return False
    finally:
        conn.close()


def save_confession_invite(sender_id: int, recipient_email: str, code: str, questions: list) -> bool:
    """Save a confession for a recipient who isn't on the app yet (email invite path)."""
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO confessions
               (code, sender_id, recipient_id, recipient_email, sender_questions, status)
               VALUES (%s, %s, NULL, %s, %s, 'sent')""",
            (code, sender_id, recipient_email, json.dumps(questions))
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error saving confession invite: {e}")
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
            """SELECT c.*,
                      s.username AS sender_username,
                      r.username AS recipient_username
               FROM confessions c
               JOIN users s ON s.id = c.sender_id
               LEFT JOIN users r ON r.id = c.recipient_id
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
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT c.*,
                      s.username AS sender_username,
                      r.username AS recipient_username
               FROM confessions c
               JOIN users s ON s.id = c.sender_id
               LEFT JOIN users r ON r.id = c.recipient_id
               WHERE c.recipient_id = %s
               ORDER BY c.created_at DESC""",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close()
        return [r for r in (_parse_confession_row(row) for row in rows) if r]
    except Exception as e:
        st.error(f"Error loading inbox: {e}")
        return []
    finally:
        conn.close()


def load_confessions_outbox(user_id: int) -> list:
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT c.*,
                      s.username AS sender_username,
                      r.username AS recipient_username
               FROM confessions c
               JOIN users s ON s.id = c.sender_id
               LEFT JOIN users r ON r.id = c.recipient_id
               WHERE c.sender_id = %s
               ORDER BY c.created_at DESC""",
            (user_id,)
        )
        rows = cur.fetchall()
        cur.close()
        return [r for r in (_parse_confession_row(row) for row in rows) if r]
    except Exception as e:
        st.error(f"Error loading outbox: {e}")
        return []
    finally:
        conn.close()


def confession_recipient_submit_questions(code: str, recipient_questions: list) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE confessions SET recipient_questions = %s, status = 'questioning'
               WHERE code = %s AND status = 'sent'""",
            (json.dumps(recipient_questions), code)
        )
        conn.commit()
        changed = cur.rowcount > 0
        cur.close()
        return changed
    except Exception as e:
        st.error(f"Error submitting questions: {e}")
        return False
    finally:
        conn.close()


def confession_recipient_answer(code: str, recipient_answers: list) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE confessions SET recipient_answers = %s, status = 'responded'
               WHERE code = %s AND status = 'questioning'""",
            (json.dumps(recipient_answers), code)
        )
        conn.commit()
        changed = cur.rowcount > 0
        cur.close()
        return changed
    except Exception as e:
        st.error(f"Error saving answers: {e}")
        return False
    finally:
        conn.close()


def confession_sender_answer(code: str, sender_answers: list) -> bool:
    """Final step — sets status=revealed and stamps revealed_at with current server time."""
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE confessions
               SET sender_answers = %s,
                   status         = 'revealed',
                   revealed_at    = NOW()
               WHERE code = %s AND status = 'responded'""",
            (json.dumps(sender_answers), code)
        )
        conn.commit()
        changed = cur.rowcount > 0
        cur.close()
        return changed
    except Exception as e:
        st.error(f"Error revealing confession: {e}")
        return False
    finally:
        conn.close()


def delete_confession(code: str) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM confessions WHERE code = %s", (code,))
        conn.commit()
        deleted = cur.rowcount > 0
        cur.close()
        return deleted
    except Exception as e:
        st.error(f"Error deleting confession: {e}")
        return False
    finally:
        conn.close()


def delete_expired_confessions() -> int:
    """
    Delete ALL revealed confessions where revealed_at is older than 60 seconds.
    Called at the top of confessions_page() on every load.
    Returns count of deleted rows.
    """
    conn = create_connection()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        cur.execute(
            """DELETE FROM confessions
               WHERE status = 'revealed'
                 AND revealed_at IS NOT NULL
                 AND revealed_at < DATE_SUB(NOW(), INTERVAL 60 SECOND)"""
        )
        conn.commit()
        count = cur.rowcount
        cur.close()
        return count
    except Exception as e:
        st.error(f"Error cleaning up confessions: {e}")
        return 0
    finally:
        conn.close()


def _parse_confession_row(row):
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


# ─── SCREENSHOT ALERTS ────────────────────────────────────────────────────────

def save_screenshot_alert(confession_code: str, screenshotter_id: int,
                           screenshotter_username: str, other_username: str) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO screenshot_alerts
               (confession_code, screenshotter_id, screenshotter_username, other_username)
               VALUES (%s, %s, %s, %s)""",
            (confession_code, screenshotter_id, screenshotter_username, other_username)
        )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error saving screenshot alert: {e}")
        return False
    finally:
        conn.close()


def load_screenshot_alerts(user_id: int) -> list:
    conn = create_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return []
        username = row["username"]
        cur.execute(
            """SELECT id, confession_code, screenshotter_username, created_at
               FROM screenshot_alerts
               WHERE other_username = %s AND dismissed = 0
               ORDER BY created_at DESC""",
            (username,)
        )
        alerts = cur.fetchall()
        cur.close()
        return alerts
    except Exception as e:
        st.error(f"Error loading screenshot alerts: {e}")
        return []
    finally:
        conn.close()


def dismiss_screenshot_alert(alert_id: int) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE screenshot_alerts SET dismissed = 1 WHERE id = %s", (alert_id,))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.error(f"Error dismissing alert: {e}")
        return False
    finally:
        conn.close()


def invalidate_user_sessions(user_id: int) -> None:
    pass
