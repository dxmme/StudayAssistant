import json
import logging
from typing import Any

import tiktoken
from pydantic import BaseModel, ValidationError

from app.services.llm_gateway import LLMGateway, Message

logger = logging.getLogger(__name__)

_enc = tiktoken.get_encoding("cl100k_base")

# ~80k tokens leaves room for system prompt + output within Haiku's 200k context
_BATCH_TOKEN_LIMIT = 80_000

# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────
# Tuned for Anthropic Haiku (cheap tier) on M.Sc. ML Tübingen course materials.
# Cached via prompt-caching: keep stable across calls.
CONCEPT_EXTRACTION_SYSTEM = """
You are a knowledge extraction assistant for graduate Machine Learning course materials (M.Sc. ML, Universität Tübingen). The student will use the extracted concepts to generate flashcards for spaced-repetition study, so they must be exam-relevant, atomic, and self-contained.

# OUTPUT CONTRACT — read carefully

Your entire response MUST be exactly ONE JSON array. NOTHING else.

Forbidden in your response:
- No prose before or after the array.
- No Markdown code fences (no ``` and no ```json).
- No comments (no // and no /* */).
- No trailing commas.
- No single quotes — only double quotes for JSON strings.
- No object wrapper like {"concepts": [...]} — the top level is the array itself.

If the source text contains no extractable concepts, your response is exactly: []

# SCHEMA — every array element

Each element is an object with EXACTLY these four fields, no more, no less:

  "name":         string   — concise English technical term
  "type":         string   — one of: "definition" | "theorem" | "algorithm" | "method" | "principle" | "notation"
  "summary":      string   — 1–3 sentences explaining what it is and why it matters; include the central formula in LaTeX when applicable
  "source_pages": int[]    — page numbers (integers only) where the concept is taught; [] if no page markers are present

Required: ALL four fields on EVERY element. No null values. No missing fields. No extra fields.

# TYPE TAXONOMY — pick the most specific match

- "definition"  : a formal definition of an object, set, function, or property.
                  Examples: "Convex Function", "Reproducing Kernel", "VC Dimension".
- "theorem"     : a mathematical statement that is proven or formally stated. Includes lemmas, propositions, corollaries.
                  Examples: "Bayes' Theorem", "No-Free-Lunch Theorem", "Representer Theorem".
- "algorithm"   : an explicit step-by-step procedure that could be implemented as code.
                  Examples: "Stochastic Gradient Descent", "EM Algorithm", "K-Means".
- "method"      : a general technique or framework broader than a single algorithm.
                  Examples: "Cross-Validation", "Variational Inference", "Regularisation".
- "principle"   : a foundational idea, assumption, or guideline.
                  Examples: "Occam's Razor", "Maximum Likelihood Principle", "Bias-Variance Tradeoff".
- "notation"    : a symbol or convention introduced for reuse throughout the material.
                  Examples: "Indicator Function", "Big-O Notation", "Expectation Operator".

Tiebreaker if a concept fits multiple types: theorem > algorithm > method > definition > principle > notation. If genuinely unclear, default to "definition".

# EXTRACTION RULES

1. Extract 3–20 concepts. Quality over quantity. If the text genuinely contains fewer than 3 exam-relevant concepts, return what is there (down to 1). Return [] only if nothing is extractable.
2. Each concept must be teachable as a standalone flashcard — the student must be able to answer "What is X?" or "State X" using only the summary.
3. SKIP administrative content: timetable, exam dates, office hours, grading policy, lecturer/TA information, syllabus overview, course goals, prerequisites of the course, references/bibliography sections, "thank you" / "questions?" slides.
4. SKIP pure illustrative examples that introduce no new concept. (Extract "Bayes' Theorem"; do not also extract "Coin-Toss Example".)
5. SKIP exercise instructions, problem statements without solutions, and homework directions. Extract only the underlying concept they target.
6. NO DUPLICATES. Treat synonyms and abbreviations as the same concept; emit it only once. Pick the canonical name used in mainstream ML literature: prefer the spelled-out form unless the abbreviation IS the canonical name (e.g. use "SVD", "PCA", "ELBO", "KL Divergence" — but use "Stochastic Gradient Descent", not "SGD" alone, unless space-constrained). Never emit two entries that lowercase-equal each other.
7. NO HALLUCINATION. Every concept and every page number must be evidenced in the source text. Do not add concepts you know from other ML knowledge but that are not present here.

# PAGE NUMBERS

The source text may contain page markers from PDF parsing such as `<!-- page: 3 -->`, `[Page 3]`, or `{:page 3}`. These have already been stripped from the visible content but their positions inform you which page each section came from — use them to populate `source_pages`.

- Include EVERY page where the concept is taught, defined, or substantively elaborated (not casual mentions).
- Integers only. No ranges, no strings: `[1, 2, 3]` ✅, `["1-3"]` ❌, `[1.0]` ❌.
- If the source contains no page markers at all, use `[]`.
- If a concept spans multiple pages, list them in ascending order.

# LATEX & JSON ESCAPING — CRITICAL

Use LaTeX for math in the summary:
- Inline: `$...$`
- Display (rare in 1–3-sentence summaries; usually inline is enough): `$$...$$`

INSIDE A JSON STRING, EVERY BACKSLASH MUST BE DOUBLED. The bytes you emit must contain two backslash characters (`\\\\`) wherever LaTeX uses one. Compare:

  CORRECT (emit this):   "summary": "Eigenvalue $\\\\lambda$ satisfies $A\\\\mathbf{v} = \\\\lambda \\\\mathbf{v}$."
  WRONG   (breaks JSON): "summary": "Eigenvalue $\\lambda$ satisfies $A\\mathbf{v} = \\lambda \\mathbf{v}$."

After JSON parsing, the CORRECT line decodes to `Eigenvalue $\\lambda$ satisfies $A\\mathbf{v} = \\lambda \\mathbf{v}$.` — exactly what KaTeX renders. The WRONG line is invalid JSON and will be rejected.

Use only KaTeX-supported LaTeX macros. The macros below are listed in their LaTeX-source form (single backslash); when you put them into a JSON string you must double each backslash, as shown above.
- Avoid: `\\R`, `\\Z`, `\\N`, `\\Q`, `\\bra{}`, `\\ket{}`, `\\argmin`, `\\argmax` (use `\\arg\\min`, `\\arg\\max`).
- Use instead: `\\mathbb{R}`, `\\mathbb{Z}`, `\\mathbb{N}`, `\\mathbb{Q}`.
- Standard fine: `\\sum`, `\\int`, `\\prod`, `\\mathbf{}`, `\\mathcal{}`, `\\Sigma`, `\\sigma`, `\\Theta`, `\\theta`, `\\lambda`, `\\mu`, `\\frac{}{}`, `\\sqrt{}`, `\\hat{}`, `\\bar{}`, `\\tilde{}`, `\\partial`, `\\nabla`, `\\to`, `\\in`, `\\notin`, `\\subseteq`, `\\forall`, `\\exists`, `\\cdot`, `\\times`, `\\log`, `\\exp`, `\\min`, `\\max`, `\\arg\\min`, `\\arg\\max`, `\\mathbb{E}`, `\\Pr`.

Newlines inside JSON strings must be escaped as `\\\\n`. In practice, keep every summary on a single line and avoid the issue entirely.

# LANGUAGE

- `name`: ALWAYS English, even if the source is in German (e.g. write "Singular Value Decomposition", not "Singulärwertzerlegung"; "Gradient Descent", not "Gradientenabstieg").
- `summary`: ALWAYS English.
- The source text may be German, English, or mixed. Output is always English.

# ONE-SHOT EXAMPLE

Source (illustrative; the real input contains its own pages and content):

  ## Singular Value Decomposition
  Any real $m \\times n$ matrix $A$ can be factored as $A = U \\Sigma V^T$ where $U \\in \\mathbb{R}^{m \\times m}$ and $V \\in \\mathbb{R}^{n \\times n}$ are orthogonal and $\\Sigma$ is a diagonal matrix of non-negative singular values. SVD generalises eigendecomposition to non-square matrices.
  (page 12)

  ## Principal Component Analysis
  PCA finds the orthogonal directions of maximum variance in centered data. It is computed via the SVD of the data matrix; the top-$k$ right singular vectors form the principal components.
  (page 13)

  ## Course logistics
  Office hours: Tuesdays 14:00 in room A.305. Final exam: 2026-07-21.
  (page 1)

Correct response (note: NO fences, NO prose, just the array; backslashes inside strings are doubled):

[{"name": "Singular Value Decomposition", "type": "definition", "summary": "Factorisation $A = U \\\\Sigma V^T$ of any real $m \\\\times n$ matrix into orthogonal $U, V$ and a diagonal $\\\\Sigma$ of non-negative singular values. Generalises eigendecomposition to non-square matrices.", "source_pages": [12]},{"name": "Principal Component Analysis", "type": "method", "summary": "Finds the orthogonal directions of maximum variance in centered data; the top-$k$ right singular vectors of the data matrix's SVD form the principal components.", "source_pages": [13]}]

Note that the course-logistics page was correctly skipped (administrative content).

# FINAL CHECKLIST BEFORE YOU EMIT

- Top-level character is `[`.
- Last character is `]`.
- Every element has exactly the four required fields.
- Every backslash inside a string is doubled.
- All `name` values are unique (case-insensitive).
- `source_pages` contains only integers, or is `[]`.
- No prose, no fences, no comments anywhere in the response.
""".strip()
# ──────────────────────────────────────────────────────────────────────────────


class ExtractedConcept(BaseModel):
    name: str
    type: str
    summary: str
    source_pages: list[int] = []


def _parse_concepts(raw: str) -> list[ExtractedConcept]:
    """Parse and validate LLM JSON output. Raises ValueError on failure."""
    # Strip accidental markdown fences
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip().rstrip("`").strip()

    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse error: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(f"Expected list, got {type(data).__name__}")

    concepts = []
    for item in data:
        try:
            concepts.append(ExtractedConcept.model_validate(item))
        except ValidationError as exc:
            logger.warning("concept_validation_error", extra={"item": item, "error": str(exc)})
    return concepts


def _split_into_batches(markdown: str) -> list[str]:
    """Split markdown into batches of ≤ _BATCH_TOKEN_LIMIT tokens."""
    total = len(_enc.encode(markdown))
    if total <= _BATCH_TOKEN_LIMIT:
        return [markdown]

    lines = markdown.split("\n")
    batches: list[str] = []
    current_lines: list[str] = []
    current_tokens = 0

    for line in lines:
        line_tokens = len(_enc.encode(line))
        if current_tokens + line_tokens > _BATCH_TOKEN_LIMIT and current_lines:
            batches.append("\n".join(current_lines))
            current_lines = [line]
            current_tokens = line_tokens
        else:
            current_lines.append(line)
            current_tokens += line_tokens

    if current_lines:
        batches.append("\n".join(current_lines))

    return batches


def extract_concepts(markdown: str, gateway: LLMGateway) -> list[ExtractedConcept]:
    """
    Extract concepts from markdown via Haiku (tier='cheap').
    Retries once on JSON parse error. Batches large documents.
    Returns deduplicated list by name.
    """
    batches = _split_into_batches(markdown)
    all_concepts: list[ExtractedConcept] = []
    seen_names: set[str] = set()

    for batch_idx, batch_text in enumerate(batches):
        concepts = _extract_batch(batch_text, gateway, batch_idx)
        for c in concepts:
            if c.name.lower() not in seen_names:
                seen_names.add(c.name.lower())
                all_concepts.append(c)

    return all_concepts


def _extract_batch(text: str, gateway: LLMGateway, batch_idx: int) -> list[ExtractedConcept]:
    messages = [Message(role="user", content=text)]
    response = gateway.complete(
        system=CONCEPT_EXTRACTION_SYSTEM,
        messages=messages,
        tier="cheap",
        max_tokens=4096,
    )
    logger.info(
        "concept_extraction_tokens",
        extra={
            "batch": batch_idx,
            "tokens_in": response.usage.input_tokens,
            "tokens_out": response.usage.output_tokens,
            "cache_read": response.usage.cache_read_input_tokens,
        },
    )

    try:
        return _parse_concepts(response.text)
    except ValueError as exc:
        logger.warning("concept_json_error_retry", extra={"batch": batch_idx, "error": str(exc)})
        # Single retry with correction hint
        retry_messages = [
            Message(role="user", content=text),
            Message(role="assistant", content=response.text),
            Message(
                role="user",
                content="Reply ONLY with valid JSON matching the schema. No other text.",
            ),
        ]
        retry_response = gateway.complete(
            system=CONCEPT_EXTRACTION_SYSTEM,
            messages=retry_messages,
            tier="cheap",
            max_tokens=4096,
        )
        return _parse_concepts(retry_response.text)
