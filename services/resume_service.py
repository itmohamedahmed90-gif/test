"""
services/resume_service.py

All resume CRUD lives here. Every function takes user_id and includes it
in the WHERE clause — there is no code path in this file that reads or
writes a resume without a user_id filter. Pages/components pass
st.session_state.user_id in; they never build SQL themselves.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from database.connection import get_db_connection

EMPTY_RESUME_DATA: dict[str, Any] = {
    "personal": {"name": "", "email": "", "phone": "", "location": "", "summary": ""},
    "experience": [],   # [{title, company, start, end, bullets: [str]}]
    "education": [],    # [{school, degree, start, end}]
    "skills": [],       # [str]
    "projects": [],     # [{name, description, link}]
}


class ResumeNotFoundError(Exception):
    """Raised when a resume_id doesn't exist for the given user_id."""


@dataclass(frozen=True)
class Resume:
    id: int
    user_id: int
    title: str
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


def _row_to_resume(row) -> Resume:
    return Resume(
        id=row["id"],
        user_id=row["user_id"],
        title=row["title"],
        data=json.loads(row["data_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_resumes(user_id: int) -> list[Resume]:
    """Summaries for the dashboard. Always filtered by user_id."""
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, title, data_json, created_at, updated_at
            FROM resumes
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [_row_to_resume(r) for r in rows]


def get_resume(user_id: int, resume_id: int) -> Resume:
    """
    Fetch a single resume. The user_id check is in the WHERE clause,
    not applied after the fact — a resume belonging to another user
    returns no row at all, not a permission error revealing it exists.
    """
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, title, data_json, created_at, updated_at
            FROM resumes
            WHERE id = ? AND user_id = ?
            """,
            (resume_id, user_id),
        ).fetchone()
    if row is None:
        raise ResumeNotFoundError(f"Resume {resume_id} not found for this user.")
    return _row_to_resume(row)


def create_resume(user_id: int, title: str = "Untitled Resume") -> Resume:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO resumes (user_id, title, data_json) VALUES (?, ?, ?)",
            (user_id, title.strip() or "Untitled Resume", json.dumps(EMPTY_RESUME_DATA)),
        )
        resume_id = cursor.lastrowid
    return get_resume(user_id, resume_id)


def update_resume(user_id: int, resume_id: int, *, title: str | None = None,
                   data: dict[str, Any] | None = None) -> Resume:
    """
    Partial update. Both the SET and the WHERE user_id=? matter here:
    even if a caller somehow passed another user's resume_id, the
    UPDATE affects zero rows rather than someone else's data.
    """
    current = get_resume(user_id, resume_id)  # raises if not owned by user_id
    new_title = title if title is not None else current.title
    new_data = data if data is not None else current.data

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE resumes
            SET title = ?, data_json = ?, updated_at = datetime('now')
            WHERE id = ? AND user_id = ?
            """,
            (new_title.strip() or "Untitled Resume", json.dumps(new_data), resume_id, user_id),
        )
        if cursor.rowcount == 0:
            raise ResumeNotFoundError(f"Resume {resume_id} not found for this user.")

    return get_resume(user_id, resume_id)


def delete_resume(user_id: int, resume_id: int) -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM resumes WHERE id = ? AND user_id = ?",
            (resume_id, user_id),
        )
        if cursor.rowcount == 0:
            raise ResumeNotFoundError(f"Resume {resume_id} not found for this user.")
