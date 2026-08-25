"""
Lightweight SQLite layer for interview history.
Kept intentionally simple (no ORM) since this is a single-file Streamlit app,
not a full multi-page application with auth.
"""

import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager

DB_PATH = "viva_panel_history.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                question_count INTEGER NOT NULL,
                hr_avg REAL NOT NULL,
                technical_avg REAL NOT NULL,
                mentor_avg REAL NOT NULL,
                overall_avg REAL NOT NULL,
                records_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


def save_interview(role: str, records: list[dict], persona_avgs: dict) -> int:
    """
    records: the full list of per-question dicts (question/answer/evaluations/posture_note)
    persona_avgs: {"HR Manager": 7.2, "Technical Panelist": 6.8, "Mentor": 7.5}
    """
    overall_avg = sum(persona_avgs.values()) / len(persona_avgs)
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO interviews
                (role, question_count, hr_avg, technical_avg, mentor_avg, overall_avg, records_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                role,
                len(records),
                persona_avgs.get("HR Manager", 0),
                persona_avgs.get("Technical Panelist", 0),
                persona_avgs.get("Mentor", 0),
                overall_avg,
                json.dumps(records),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return cursor.lastrowid


def get_all_interviews() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, role, question_count, hr_avg, technical_avg, mentor_avg, overall_avg, created_at "
            "FROM interviews ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_interview_detail(interview_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM interviews WHERE id = ?", (interview_id,)
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["records"] = json.loads(result["records_json"])
        return result
