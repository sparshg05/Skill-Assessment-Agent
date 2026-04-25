"""
Document parser service.
Extracts plain text from PDF, DOCX, and plain text inputs.
"""
from __future__ import annotations

import io
import structlog

logger = structlog.get_logger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        text = "\n".join(pages).strip()
        logger.info("pdf_parsed", pages=len(pages), chars=len(text))
        return text
    except Exception as e:
        logger.error("pdf_parse_failed", error=str(e))
        raise ValueError(f"Failed to parse PDF: {e}") from e


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs).strip()
        logger.info("docx_parsed", paragraphs=len(paragraphs), chars=len(text))
        return text
    except Exception as e:
        logger.error("docx_parse_failed", error=str(e))
        raise ValueError(f"Failed to parse DOCX: {e}") from e


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Route to the right parser based on file extension."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif lower.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    elif lower.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="replace")
    else:
        # Try to decode as UTF-8 text as a last resort
        try:
            return file_bytes.decode("utf-8", errors="replace")
        except Exception:
            raise ValueError(f"Unsupported file format: {filename}")