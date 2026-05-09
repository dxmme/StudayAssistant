import re
from dataclasses import dataclass

import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")

TARGET_TOKENS = 500
OVERLAP_TOKENS = 50

# Page marker patterns from marker-pdf (multiple formats, best-effort)
_PAGE_PATTERNS = [
    re.compile(r"<!--\s*page:\s*(\d+)\s*-->", re.IGNORECASE),
    re.compile(r"\[Page\s+(\d+)\]", re.IGNORECASE),
    re.compile(r"\{:page\s+(\d+)\}", re.IGNORECASE),
]

# Display LaTeX blocks — must not be split
_DISPLAY_LATEX_RE = re.compile(r"\$\$.*?\$\$", re.DOTALL)

# Preferred split boundaries (in priority order)
_BOUNDARY_RE = re.compile(r"(?=\n#{1,6} )|(?<=\n\n)|\n\n")


@dataclass
class Chunk:
    content: str
    page: int | None
    chunk_index: int
    token_count: int


def _count(text: str) -> int:
    return len(_enc.encode(text))


def _last_n_tokens(text: str, n: int) -> str:
    """Return the last n tokens of text as a string."""
    tokens = _enc.encode(text)
    if len(tokens) <= n:
        return text
    return _enc.decode(tokens[-n:])


def _safe_overlap(text: str, n: int) -> str:
    """Return last n tokens for overlap, but clear if it would start inside a $$...$$ block."""
    candidate = _last_n_tokens(text, n)
    # Odd number of $$ means we'd start mid-block — clear the overlap
    if candidate.count("$$") % 2 != 0:
        return ""
    return candidate


def _extract_page_map(markdown: str) -> dict[int, int]:
    """Build {char_position: page_number} from any recognised marker pattern."""
    page_map: dict[int, int] = {}
    for pattern in _PAGE_PATTERNS:
        for m in pattern.finditer(markdown):
            page_map[m.start()] = int(m.group(1))
    return page_map


def _strip_page_markers(markdown: str) -> str:
    for pattern in _PAGE_PATTERNS:
        markdown = pattern.sub("\n", markdown)
    return markdown


def _get_page(pos: int, sorted_markers: list[tuple[int, int]]) -> int | None:
    """Return the page number active at char position pos."""
    current = None
    for marker_pos, page_num in sorted_markers:
        if marker_pos <= pos:
            current = page_num
        else:
            break
    return current


def _split_segments(text: str) -> list[str]:
    """
    Split text into segments at heading and paragraph boundaries,
    keeping $$...$$ display-math blocks atomic (never cut inside them).
    """
    # Mark latex blocks so we never split inside them
    protected_ranges: list[tuple[int, int]] = [
        (m.start(), m.end()) for m in _DISPLAY_LATEX_RE.finditer(text)
    ]

    def is_protected(pos: int) -> bool:
        return any(s <= pos < e for s, e in protected_ranges)

    segments: list[str] = []
    last = 0
    for m in _BOUNDARY_RE.finditer(text):
        split_at = m.start()
        if not is_protected(split_at) and split_at > last:
            seg = text[last:split_at]
            if seg.strip():
                segments.append(seg)
            last = split_at
    tail = text[last:]
    if tail.strip():
        segments.append(tail)
    return segments if segments else [text]


def chunk_markdown(markdown: str) -> list[Chunk]:
    """Chunk a markdown document into ~TARGET_TOKENS chunks with OVERLAP_TOKENS overlap."""
    page_map = _extract_page_map(markdown)
    sorted_markers = sorted(page_map.items())
    clean = _strip_page_markers(markdown)
    segments = _split_segments(clean)

    chunks: list[Chunk] = []
    current_parts: list[str] = []
    current_tokens = 0
    current_page: int | None = None
    char_pos = 0
    overlap_prefix = ""

    for seg in segments:
        seg_tokens = _count(seg)
        seg_page = _get_page(char_pos, sorted_markers)

        if current_tokens + seg_tokens > TARGET_TOKENS and current_parts:
            # Emit current chunk
            raw = "".join(current_parts).strip()
            chunk_text = (overlap_prefix + raw).strip() if overlap_prefix else raw
            chunks.append(
                Chunk(
                    content=chunk_text,
                    page=current_page,
                    chunk_index=len(chunks),
                    token_count=_count(chunk_text),
                )
            )
            overlap_prefix = _safe_overlap(raw, OVERLAP_TOKENS)
            current_parts = [seg]
            current_tokens = seg_tokens
            current_page = seg_page
        else:
            if not current_parts:
                current_page = seg_page
            current_parts.append(seg)
            current_tokens += seg_tokens

        char_pos += len(seg)

    # Flush remaining
    if current_parts:
        raw = "".join(current_parts).strip()
        if raw:
            chunk_text = (overlap_prefix + raw).strip() if overlap_prefix else raw
            chunks.append(
                Chunk(
                    content=chunk_text,
                    page=current_page,
                    chunk_index=len(chunks),
                    token_count=_count(chunk_text),
                )
            )

    return chunks
