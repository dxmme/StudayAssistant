"""
Determinism test: replay 529 reviews over 100 cards across 14 days and compare
final fsrs states against a committed snapshot. If this test breaks after a
py-fsrs update, regenerate the fixtures (see comment at bottom of file) and
commit the new snapshot.
"""
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fsrs import Card, Rating, Scheduler

FIXTURES = Path(__file__).parent / "fixtures"
BASE_DATE = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
NUM_CARDS = 100


def _load_stream():
    rows = []
    with open(FIXTURES / "review_stream_14d.csv", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append((int(row["card_idx"]), int(row["day_offset"]), int(row["rating"])))
    return rows


def _load_expected():
    with open(FIXTURES / "expected_states.json") as f:
        return json.load(f)


def test_fsrs_determinism():
    """Replay the fixture stream and assert final states match the snapshot."""
    sched = Scheduler(enable_fuzzing=False)  # production scheduler keeps fuzzing; test requires determinism
    stream = _load_stream()
    expected = _load_expected()

    # Build initial cards with due = BASE_DATE - 1h
    cards: list[Card] = []
    for _ in range(NUM_CARDS):
        c = Card()
        d = c.to_dict()
        d["due"] = (BASE_DATE - timedelta(hours=1)).isoformat()
        cards.append(Card.from_dict(d))

    # Group reviews by (day, card) for ordered replay
    for card_idx, day_offset, rating_val in stream:
        review_date = BASE_DATE + timedelta(days=day_offset)
        new_card, _ = sched.review_card(cards[card_idx], Rating(rating_val), review_datetime=review_date)
        cards[card_idx] = new_card

    # Compare against snapshot (excluding volatile card_id)
    for i, (card, exp) in enumerate(zip(cards, expected)):
        actual = card.to_dict()
        actual.pop("card_id", None)
        assert actual["state"] == exp["state"], f"card {i}: state mismatch"
        assert abs((actual["stability"] or 0) - (exp["stability"] or 0)) < 1e-6, (
            f"card {i}: stability mismatch {actual['stability']} vs {exp['stability']}"
        )
        assert actual["due"] == exp["due"], f"card {i}: due mismatch"


# ── Fixture regeneration ──────────────────────────────────────────────────────
# If py-fsrs changes its algorithm, run:
#
#   python tests/test_fsrs_determinism.py
#
# to regenerate tests/fixtures/review_stream_14d.csv and expected_states.json,
# then commit both files. The determinism test will then serve as a regression
# canary for future updates.
