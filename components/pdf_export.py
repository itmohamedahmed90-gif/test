"""
components/pdf_export.py

Converts the same HTML used for the live preview into a PDF via
xhtml2pdf, so preview and export can never visually drift apart.

xhtml2pdf (built on reportlab) was chosen over weasyprint specifically
because it is pure Python — no GTK/pango/cairo system libraries to
install, which is what broke this app on Windows. Trade-off: weaker
CSS support (no flexbox/grid), which is why resume_preview.py's markup
uses table-based layout instead of flex for the "title ... dates" rows.
"""

from __future__ import annotations

import io
from typing import Any

from components.resume_preview import render_resume_html


class PdfGenerationError(Exception):
    """Raised when xhtml2pdf reports errors while rendering the PDF."""


def resume_to_pdf_bytes(data: dict[str, Any]) -> bytes:
    """Render resume JSON -> HTML -> PDF bytes, in memory (no temp files)."""
    from xhtml2pdf import pisa  # imported lazily so a missing/broken
    # install only affects the PDF export path, not the rest of the app.

    html_string = render_resume_html(data)
    buffer = io.BytesIO()
    result = pisa.CreatePDF(src=html_string, dest=buffer)

    if result.err:
        raise PdfGenerationError(
            f"xhtml2pdf reported {result.err} error(s) while rendering the PDF."
        )

    return buffer.getvalue()
