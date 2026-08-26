"""
pages/2_Editor.py

Edits a single resume, identified by st.session_state.active_resume_id
(set by the dashboard before switch_page). All persistence goes through
services/resume_service.py, scoped to user_id from require_auth() — so
even if active_resume_id were tampered with, update_resume/get_resume
would raise ResumeNotFoundError rather than touch another user's row.

Uses st.form so the DB write happens once on "Save", not on every
keystroke rerun (per the state-engine rules).
"""

from __future__ import annotations

import streamlit as st

from components.pdf_export import PdfGenerationError, resume_to_pdf_bytes
from components.resume_preview import render_preview
from services.auth_service import require_auth
from services.resume_service import ResumeNotFoundError, get_resume, update_resume

user_id = require_auth()

resume_id = st.session_state.get("active_resume_id")
if resume_id is None:
    st.warning("No resume selected.")
    if st.button("Back to dashboard"):
        st.switch_page("pages/1_Dashboard.py")
    st.stop()

try:
    resume = get_resume(user_id, resume_id)
except ResumeNotFoundError:
    st.error("That resume no longer exists or isn't yours.")
    if st.button("Back to dashboard"):
        st.switch_page("pages/1_Dashboard.py")
    st.stop()

st.title(f"Editing: {resume.title}")
if st.button("← Back to dashboard"):
    st.switch_page("pages/1_Dashboard.py")

edit_col, preview_col = st.columns([3, 2])

with edit_col:
    with st.form("resume_form"):
        title = st.text_input("Resume title", value=resume.title)

        st.subheader("Personal details")
        personal = resume.data.get("personal", {})
        name = st.text_input("Full name", value=personal.get("name", ""))
        email = st.text_input("Email", value=personal.get("email", ""))
        phone = st.text_input("Phone", value=personal.get("phone", ""))
        location = st.text_input("Location", value=personal.get("location", ""))
        summary = st.text_area("Summary", value=personal.get("summary", ""))

        st.subheader("Skills")
        skills_raw = st.text_area(
            "Comma-separated skills",
            value=", ".join(resume.data.get("skills", [])),
        )

        st.caption(
            "Work experience, education, and projects support full "
            "add/remove editing in a future iteration — this form "
            "covers the fields needed for a complete first pass."
        )

        submitted = st.form_submit_button("💾 Save", use_container_width=True)

    if submitted:
        new_data = dict(resume.data)
        new_data["personal"] = {
            "name": name,
            "email": email,
            "phone": phone,
            "location": location,
            "summary": summary,
        }
        new_data["skills"] = [s.strip() for s in skills_raw.split(",") if s.strip()]

        resume = update_resume(user_id, resume_id, title=title, data=new_data)
        st.success("Saved.")
        st.rerun()

    st.divider()

    # PDF generation is deliberately NOT run on every page load — only
    # when this button is clicked. Keeping it click-triggered and
    # wrapped in error handling means a PDF-export problem never
    # blocks editing or previewing the resume.
    if st.button("🖨️ Generate PDF", use_container_width=True):
        try:
            st.session_state[f"pdf_bytes_{resume_id}"] = resume_to_pdf_bytes(resume.data)
        except ImportError:
            st.error(
                "PDF export isn't available: the `xhtml2pdf` package "
                "isn't installed. Run `pip install xhtml2pdf` and restart "
                "the app."
            )
        except PdfGenerationError as e:
            st.error(f"PDF generation failed: {e}")
        except Exception as e:
            st.error(f"Unexpected error generating PDF: {e}")

    pdf_bytes = st.session_state.get(f"pdf_bytes_{resume_id}")
    if pdf_bytes:
        st.download_button(
            "⬇️ Download PDF",
            data=pdf_bytes,
            file_name=f"{resume.title.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

with preview_col:
    st.subheader("Live preview")
    render_preview(resume.data)
