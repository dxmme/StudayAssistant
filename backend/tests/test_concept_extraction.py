from unittest.mock import MagicMock, patch

import pytest

from app.services.concept_extractor import ExtractedConcept, _parse_concepts, extract_concepts
from app.services.llm_gateway import LLMResponse, UsageInfo

_GOOD_JSON = """
[
  {"name": "SVD", "type": "definition", "summary": "Factorization $A=U\\\\Sigma V^T$.", "source_pages": [1, 2]},
  {"name": "Eigenvalue", "type": "definition", "summary": "Scalar $\\\\lambda$ s.t. $Av=\\\\lambda v$.", "source_pages": [3]}
]
"""

_BAD_JSON = "Here are the concepts: SVD is a factorization method..."

_USAGE = UsageInfo(
    input_tokens=100,
    output_tokens=50,
    cache_creation_input_tokens=0,
    cache_read_input_tokens=0,
)


def _mock_response(text: str) -> LLMResponse:
    return LLMResponse(text=text, model="haiku", usage=_USAGE, stop_reason="end_turn")


def test_parse_concepts_valid():
    concepts = _parse_concepts(_GOOD_JSON)
    assert len(concepts) == 2
    assert concepts[0].name == "SVD"
    assert concepts[0].type == "definition"
    assert concepts[1].source_pages == [3]


def test_parse_concepts_strips_markdown_fences():
    fenced = "```json\n" + _GOOD_JSON.strip() + "\n```"
    concepts = _parse_concepts(fenced)
    assert len(concepts) == 2


def test_parse_concepts_invalid_json_raises():
    with pytest.raises(ValueError, match="JSON parse error"):
        _parse_concepts("not json at all")


def test_parse_concepts_non_list_raises():
    with pytest.raises(ValueError, match="Expected list"):
        _parse_concepts('{"name": "SVD"}')


def test_extract_concepts_happy_path():
    gateway = MagicMock()
    gateway.complete.return_value = _mock_response(_GOOD_JSON)

    concepts = extract_concepts("Some markdown about SVD.", gateway)
    assert len(concepts) == 2
    assert gateway.complete.call_count == 1


def test_extract_concepts_retry_on_bad_json():
    gateway = MagicMock()
    # First call returns bad JSON, second returns good
    gateway.complete.side_effect = [
        _mock_response(_BAD_JSON),
        _mock_response(_GOOD_JSON),
    ]

    concepts = extract_concepts("Some markdown.", gateway)
    assert len(concepts) == 2
    assert gateway.complete.call_count == 2


def test_extract_concepts_both_calls_fail():
    gateway = MagicMock()
    gateway.complete.return_value = _mock_response(_BAD_JSON)

    with pytest.raises(ValueError):
        extract_concepts("Some markdown.", gateway)


def test_extract_concepts_deduplicates_by_name():
    duplicate_json = """
    [
      {"name": "SVD", "type": "definition", "summary": "First.", "source_pages": []},
      {"name": "svd", "type": "theorem", "summary": "Duplicate.", "source_pages": []}
    ]
    """
    gateway = MagicMock()
    gateway.complete.return_value = _mock_response(duplicate_json)

    concepts = extract_concepts("markdown", gateway)
    names = [c.name for c in concepts]
    assert len(names) == len(set(n.lower() for n in names))


def test_extract_concepts_batches_large_document():
    # Build a document > 80k tokens by repeating text
    # We don't actually want to tokenize 80k tokens in tests, so patch _split_into_batches
    gateway = MagicMock()
    gateway.complete.return_value = _mock_response(_GOOD_JSON)

    with patch(
        "app.services.concept_extractor._split_into_batches",
        return_value=["batch1", "batch2"],
    ):
        concepts = extract_concepts("large doc", gateway)

    # Two batches → two LLM calls → deduplication removes SVD/Eigenvalue duplicates
    assert gateway.complete.call_count == 2
    names = {c.name for c in concepts}
    assert "SVD" in names
