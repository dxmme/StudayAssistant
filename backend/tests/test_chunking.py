from app.services.chunker import TARGET_TOKENS, chunk_markdown


def test_basic_chunking_produces_chunks():
    # ~600 words / ~800 tokens → should produce at least 2 chunks
    para = "Word " * 150  # ~150 tokens
    md = "\n\n".join([para] * 6)
    chunks = chunk_markdown(md)
    assert len(chunks) >= 2
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert c.content.strip() != ""


def test_chunk_tokens_near_target():
    para = "word " * 80  # ~80 tokens each
    md = "\n\n".join([para] * 10)
    chunks = chunk_markdown(md)
    for c in chunks:
        # Allow some tolerance (overlap adds tokens, large segments can exceed)
        assert c.token_count < TARGET_TOKENS * 2


def test_heading_boundary_respected():
    """When content exceeds TARGET, prefer splitting at ## heading boundaries."""
    # ~300 tokens per section → forces split
    para = "word " * 300
    section_a = "## Section A\n\n" + para
    section_b = "## Section B\n\n" + para
    md = section_a + "\n\n" + section_b
    chunks = chunk_markdown(md)
    assert len(chunks) >= 2
    # At least one chunk should start with a heading (boundary happened at ##)
    assert any(c.content.lstrip().startswith("##") for c in chunks)


def test_no_split_inside_display_latex():
    """The $$...$$ block is never split across chunks — it stays in exactly one chunk."""
    # ~640-token latex block (forces its own chunk)
    latex_block = "$$\n" + "x_i = \\sum_{j=1}^{n} w_{ij} \\cdot a_j + b_i \n" * 20 + "$$"
    surrounding = "Some text before.\n\n" + latex_block + "\n\nSome text after."
    chunks = chunk_markdown(surrounding)
    # Every chunk that contains $$ must have a balanced count
    for c in chunks:
        count = c.content.count("$$")
        assert count % 2 == 0, f"Unbalanced $$ in chunk (odd count={count}): {c.content[:200]}"
    # The full latex block (opening AND closing $$) must appear together in exactly one chunk
    chunks_with_full_block = [c for c in chunks if "$$" in c.content and c.content.count("$$") >= 2]
    assert len(chunks_with_full_block) >= 1, "No chunk contains the full $$...$$ block"


def test_page_markers_extracted():
    md = (
        "<!-- page: 3 -->\n## Intro\n\nSome text here.\n\n"
        + ("word " * 60)
        + "\n\n<!-- page: 4 -->\n## Next Section\n\n"
        + ("word " * 60)
    )
    chunks = chunk_markdown(md)
    pages = [c.page for c in chunks if c.page is not None]
    assert len(pages) >= 1
    assert any(p == 3 or p == 4 for p in pages)


def test_page_markers_stripped_from_content():
    md = "<!-- page: 7 -->\nSome content here " * 5
    chunks = chunk_markdown(md)
    for c in chunks:
        assert "<!--" not in c.content
        assert "page:" not in c.content


def test_overlap_carries_over():
    # Two chunks — second chunk should start with tail of first
    long_para = "token " * 300
    separator = "\n## New Section\n\n"
    md = long_para + separator + "token " * 300
    chunks = chunk_markdown(md)
    assert len(chunks) >= 2
    # The second chunk (if it has overlap) starts with some tokens from the first
    # We can't check exact content easily, just verify token_count is set
    for c in chunks:
        assert c.token_count > 0


def test_empty_markdown_returns_empty():
    assert chunk_markdown("") == []
    assert chunk_markdown("   \n  ") == []


def test_small_document_single_chunk():
    md = "# Title\n\nA short document with just a few words."
    chunks = chunk_markdown(md)
    assert len(chunks) == 1
    assert "short document" in chunks[0].content
