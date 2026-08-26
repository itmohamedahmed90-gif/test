"""
pages/1_Dashboard.py

Lists the current user's resumes, lets them create a new one or delete
an existing one. All DB access goes through services/resume_service.py,
scoped by st.session_state.user_id via require_auth().
"""

from __future__ import annotations

import streamlit as st

from services.auth_service import require_auth
from services.resume_service import create_resume, delete_resume, list_resumes

user_id = require_auth()

st.title("Your resumes")

if st.button("➕ New resume"):
    new_resume = create_resume(user_id)
    st.session_state.active_resume_id = new_resume.id
    st.switch_page("pages/2_Editor.py")

resumes = list_resumes(user_id)

if not resumes:
    st.info("No resumes yet. Click **New resume** to create one.")
else:
    for resume in resumes:
        col_title, col_updated, col_edit, col_delete = st.columns([4, 3, 1, 1])
        col_title.write(f"**{resume.title}**")
        col_updated.caption(f"Updated {resume.updated_at}")

        if col_edit.button("Edit", key=f"edit_{resume.id}"):
            st.session_state.active_resume_id = resume.id
            st.switch_page("pages/2_Editor.py")

        if col_delete.button("Delete", key=f"delete_{resume.id}"):
            st.session_state[f"confirm_delete_{resume.id}"] = True

        if st.session_state.get(f"confirm_delete_{resume.id}"):
            st.warning(f"Delete **{resume.title}**? This cannot be undone.")
            c1, c2 = st.columns(2)
            if c1.button("Confirm delete", key=f"confirm_yes_{resume.id}"):
                delete_resume(user_id, resume.id)
                del st.session_state[f"confirm_delete_{resume.id}"]
                st.rerun()
            if c2.button("Cancel", key=f"confirm_no_{resume.id}"):
                del st.session_state[f"confirm_delete_{resume.id}"]
                st.rerun()
