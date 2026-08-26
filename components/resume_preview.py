"""
components/resume_preview.py

Turns a resume's structured JSON (see EMPTY_RESUME_DATA in
resume_service.py) into rendered HTML, using
static/resume_template.html as the shell. Used both for the live
in-app preview (st.components.v1.html) and as the input to
components/pdf_export.py, so there is exactly one place that knows
how resume JSON maps to markup.

All user-supplied text is HTML-escaped before insertion — resume
content is untrusted input and this HTML is rendered directly in an
iframe (and in the PDF), so this is the one place injection would
otherwise be possible.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "static" / "resume_template.html"


def _esc(value: str | None) -> str:
    return escape(value or "", quote=True)


def _contact_line(personal: dict[str, Any]) -> str:
    parts = [personal.get("email"), personal.get("phone"), personal.get("location")]
    return " &nbsp;•&nbsp; ".join(_esc(p) for p in parts if p)


def _summary_section(personal: dict[str, Any]) -> str:
    summary = personal.get("summary")
    if not summary:
        return ""
    return f"<h2>Summary</h2><p>{_esc(summary)}</p>"


def _entry_header_row(title_html: str, dates_html: str) -> str:
    """
    Two-cell table row for a "title ... dates" line. Used instead of
    flexbox (unsupported by xhtml2pdf) so the same markup renders
    identically in the live preview and the exported PDF.
    """
    return f"""<table class="entry-header-table"><tr>
        <td class="entry-title">{title_html}</td>
        <td class="entry-dates">{dates_html}</td>
    </tr></table>"""


def _experience_section(experience: list[dict[str, Any]]) -> str:
    if not experience:
        return ""
    entries = []
    for job in experience:
        bullets = "".join(f"<li>{_esc(b)}</li>" for b in job.get("bullets", []))
        header = _entry_header_row(
            f"{_esc(job.get('title'))} — {_esc(job.get('company'))}",
            f"{_esc(job.get('start'))} – {_esc(job.get('end'))}",
        )
        entries.append(f'<div class="entry">{header}<ul>{bullets}</ul></div>')
    return "<h2>Experience</h2>" + "".join(entries)


def _education_section(education: list[dict[str, Any]]) -> str:
    if not education:
        return ""
    entries = []
    for edu in education:
        header = _entry_header_row(
            _esc(edu.get("school")),
            f"{_esc(edu.get('start'))} – {_esc(edu.get('end'))}",
        )
        entries.append(
            f'<div class="entry">{header}<div class="entry-sub">{_esc(edu.get("degree"))}</div></div>'
        )
    return "<h2>Education</h2>" + "".join(entries)


def _skills_section(skills: list[str]) -> str:
    if not skills:
        return ""
    return f"<h2>Skills</h2><div class='skills'>{_esc(', '.join(skills))}</div>"


def _projects_section(projects: list[dict[str, Any]]) -> str:
    if not projects:
        return ""
    entries = []
    for proj in projects:
        link = f" — <a href='{_esc(proj.get('link'))}'>{_esc(proj.get('link'))}</a>" if proj.get("link") else ""
        entries.append(
            f"""<div class="entry">
                <div class="entry-title">{_esc(proj.get('name'))}</div>
                <div>{_esc(proj.get('description'))}{link}</div>
            </div>"""
        )
    return "<h2>Projects</h2>" + "".join(entries)


def render_resume_html(data: dict[str, Any]) -> str:
    """Pure function: resume JSON -> full standalone HTML string."""
    personal = data.get("personal", {})
    template = TEMPLATE_PATH.read_text()

    replacements = {
        "{{name}}": _esc(personal.get("name") or "Your Name"),
        "{{contact_line}}": _contact_line(personal),
        "{{summary_section}}": _summary_section(personal),
        "{{experience_section}}": _experience_section(data.get("experience", [])),
        "{{education_section}}": _education_section(data.get("education", [])),
        "{{skills_section}}": _skills_section(data.get("skills", [])),
        "{{projects_section}}": _projects_section(data.get("projects", [])),
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template


def render_preview(data: dict[str, Any], height: int = 900) -> None:
    """Render the live preview inline in the Streamlit app."""
    html = render_resume_html(data)
    components.html(html, height=height, scrolling=True)
