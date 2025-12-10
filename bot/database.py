import sqlite3
from typing import List, Optional
from datetime import datetime

from .config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               owner_id INTEGER NOT NULL,
               phone TEXT NOT NULL,
               session_string TEXT NOT NULL,
               username TEXT,
               first_name TEXT,
               device TEXT,
               created_at TEXT,
               active INTEGER DEFAULT 1
        )"""
    )
    conn.commit()
    conn.close()


def add_session(
    owner_id: int,
    phone: str,
    session_string: str,
    username: Optional[str],
    first_name: Optional[str],
    device: Optional[str] = "SessionBot",
) -> int:
    conn = get_connection()
    cur = conn.cursor()
    created_at = datetime.utcnow().isoformat(timespec="seconds")
    cur.execute(
        "INSERT INTO sessions (owner_id, phone, session_string, username, first_name, device, created_at, active)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
        (owner_id, phone, session_string, username, first_name, device, created_at),
    )
    conn.commit()
    session_id = cur.lastrowid
    conn.close()
    return int(session_id)


def get_sessions_for_owner(owner_id: int) -> List[sqlite3.Row]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM sessions WHERE owner_id = ? ORDER BY id DESC",
        (owner_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_session_by_id(session_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cur.fetchone()
    conn.close()
    return row


def set_session_active(session_id: int, active: bool) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE sessions SET active = ? WHERE id = ?",
        (1 if active else 0, session_id),
    )
    conn.commit()
    conn.close()


def delete_session(session_id: int) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


def count_active_sessions(owner_id: Optional[int] = None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    if owner_id is None:
        cur.execute("SELECT COUNT(*) FROM sessions WHERE active = 1")
    else:
        cur.execute(
            "SELECT COUNT(*) FROM sessions WHERE owner_id = ? AND active = 1",
            (owner_id,),
        )
    (count,) = cur.fetchone()
    conn.close()
    return int(count)


def get_all_sessions() -> List[sqlite3.Row]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sessions ORDER BY owner_id, id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows
