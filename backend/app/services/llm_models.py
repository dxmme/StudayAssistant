from typing import Literal

Tier = Literal["default", "cheap", "hard"]

TIER_MODEL_MAP: dict[str, str] = {
    "default": "claude-sonnet-4-6",
    "cheap": "claude-haiku-4-5-20251001",
    # hard = only for proof verification (Phase 3+)
    "hard": "claude-opus-4-7",
}
