"""
app.py — entry point.

Responsibilities, in order:
1. Initialize the DB schema (idempotent, cheap to call every run).
2. Initialize session_state keys so nothing downstream does
   `if "user_id" in st.session_state` defensively.
3. Gate on authentication: unauthenticated -> auth screen, else -> app.
4. Route authenticated users via st.navigation.
"""

from __future__ import annotations

import streamlit as st

from database.connection import init_db
from services.auth_service import init_session_state, is_authenticated, logout

st.set_page_config(page_title="Resume Generator", page_icon="📄", layout="wide")

init_db()
init_session_state()

if not is_authenticated():
    from components.auth_forms import render_auth_gate

    render_auth_gate()
    st.stop()

# --- Authenticated area -------------------------------------------------

with st.sidebar:
    st.write(f"Signed in as **{st.session_state.user_email}**")
    if st.button("Log out", use_container_width=True):
        logout()
        st.rerun()

dashboard_page = st.Page("pages/1_Dashboard.py", title="Dashboard", icon="🗂️", default=True)
editor_page = st.Page("pages/2_Editor.py", title="Editor", icon="✏️")

pg = st.navigation([dashboard_page, editor_page])
pg.run()
