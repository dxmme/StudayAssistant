import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SLOW_PARSE_THRESHOLD_MS = 120_000


def parse_pdf(pdf_path: Path) -> tuple[str, int]:
    """Convert PDF to markdown via marker-pdf. Returns (markdown, page_count)."""
    t0 = time.monotonic()

    # Page count via pymupdf (fast, no model download)
    import fitz  # type: ignore[import-untyped]

    doc = fitz.open(str(pdf_path))
    page_count = len(doc)
    doc.close()

    # Markdown conversion via marker-pdf
    from marker.converters.pdf import PdfConverter  # type: ignore[import-untyped]
    from marker.models import create_model_dict  # type: ignore[import-untyped]
    from marker.output import text_from_rendered  # type: ignore[import-untyped]

    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(str(pdf_path))
    markdown_text, _images, _meta = text_from_rendered(rendered)

    elapsed_ms = (time.monotonic() - t0) * 1000
    if elapsed_ms > SLOW_PARSE_THRESHOLD_MS:
        logger.warning(
            "slow_parse",
            extra={"duration_ms": round(elapsed_ms), "path": str(pdf_path)},
        )

    return markdown_text, page_count
