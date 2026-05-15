import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SLOW_PARSE_THRESHOLD_MS = 60_000


def parse_pdf(pdf_path: Path) -> tuple[str, int]:
    """Extract PDF content to Markdown via Claude document understanding.

    Falls back to pymupdf text extraction when the API key is unavailable.
    Returns (markdown, page_count).
    """
    import fitz  # type: ignore[import-untyped]

    pdf_bytes = pdf_path.read_bytes()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    doc.close()

    t0 = time.monotonic()

    from app.core.config import settings

    if settings.anthropic_api_key:
        from app.services.llm_gateway import LLMGateway

        gw = LLMGateway()
        markdown_text = gw.extract_pdf(pdf_bytes)
    else:
        logger.warning("parse_fallback_pymupdf", extra={"path": str(pdf_path)})
        markdown_text = _pymupdf_extract(fitz.open(stream=pdf_bytes, filetype="pdf"))

    elapsed_ms = (time.monotonic() - t0) * 1000
    if elapsed_ms > SLOW_PARSE_THRESHOLD_MS:
        logger.warning(
            "slow_parse",
            extra={"duration_ms": round(elapsed_ms), "path": str(pdf_path)},
        )

    return markdown_text, page_count


def _pymupdf_extract(doc: object) -> str:
    """Lightweight fallback: plain text extraction via pymupdf (no ML, no API)."""
    import fitz  # type: ignore[import-untyped]

    pages_md: list[str] = []
    for page in doc:  # type: ignore[union-attr]
        blocks = page.get_text("blocks")
        lines = [b[4].strip() for b in sorted(blocks, key=lambda b: (b[1], b[0])) if b[4].strip()]
        if lines:
            pages_md.append("\n\n".join(lines))
    doc.close()  # type: ignore[union-attr]
    return "\n\n---\n\n".join(pages_md)
