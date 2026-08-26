"""
services/auth_service.py

All password hashing and credential-checking logic lives here — nothing
in components/ or pages/ should touch bcrypt or raw SQL directly.

Session state contract (set by login(), cleared by logout()):
    st.session_state.authenticated : bool
    st.session_state.user_id       : int | None
    st.session_state.user_email    : str | None
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import bcrypt
import streamlit as st

from database.connection import get_db_connection

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LEN = 8


class AuthError(Exception):
    """Raised for any expected auth failure (bad creds, dup email, etc.)."""


@dataclass(frozen=True)
class AuthUser:
    id: int
    email: str


# ---------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------

def _hash_password(password: str) -> str:
    """Hash with bcrypt (auto-generated salt per call, stored in the hash)."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed hash in the DB — treat as a verification failure,
        # not a crash.
        return False


def _validate_credentials(email: str, password: str) -> None:
    if not EMAIL_RE.match(email or ""):
        raise AuthError("Please enter a valid email address.")
    if not password or len(password) < MIN_PASSWORD_LEN:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LEN} characters.")


# ---------------------------------------------------------------------
# Registration / credential verification (pure — no session_state)
# ---------------------------------------------------------------------

def register_user(email: str, password: str) -> AuthUser:
    """
    Create a new user. Raises AuthError if the email is invalid,
    the password is too weak, or the email is already registered.
    """
    email = email.strip().lower()
    _validate_credentials(email, password)

    password_hash = _hash_password(password)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        existing = cursor.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing is not None:
            raise AuthError("An account with this email already exists.")

        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash),
        )
        user_id = cursor.lastrowid

    return AuthUser(id=user_id, email=email)


def verify_credentials(email: str, password: str) -> AuthUser:
    """
    Check email/password against the DB. Raises AuthError on any
    mismatch. Deliberately uses the same error message for "no such
    user" and "wrong password" so login doesn't leak which emails
    are registered.
    """
    email = email.strip().lower()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    generic_error = "Incorrect email or password."
    if row is None:
        raise AuthError(generic_error)
    if not _verify_password(password, row["password_hash"]):
        raise AuthError(generic_error)

    return AuthUser(id=row["id"], email=row["email"])


# ---------------------------------------------------------------------
# Streamlit session integration
# ---------------------------------------------------------------------

def init_session_state() -> None:
    """Ensure auth keys exist before anything reads them. Call at app top."""
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("user_email", None)


def login(user: AuthUser) -> None:
    """
    Populate session_state for a successfully authenticated user.
    Caller is responsible for calling st.rerun() immediately after,
    per the state-altering-operation rule — this function only
    mutates state, it does not trigger the rerun itself, so it stays
    testable and side-effect-predictable.
    """
    st.session_state.authenticated = True
    st.session_state.user_id = user.id
    st.session_state.user_email = user.email


def logout() -> None:
    """Clear all auth-related session state. Caller triggers st.rerun()."""
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.user_email = None


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated", False))


def require_auth() -> int:
    """
    Guard for pages that require a logged-in user.
    Returns user_id if authenticated, otherwise halts page execution.
    """
    if not is_authenticated() or st.session_state.get("user_id") is None:
        st.warning("Please log in to continue.")
        st.stop()
    return st.session_state.user_id
