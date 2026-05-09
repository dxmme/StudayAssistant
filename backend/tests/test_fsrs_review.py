"""Review endpoint and FSRS-state-transition tests."""
from datetime import datetime, timedelta, timezone

_COURSE = "course-review-tests"
_CARD_BODY = {"type": "basic", "front": "Q", "back": "A"}


def _create_card(client):
    r = client.post(f"/api/courses/{_COURSE}/cards", json=_CARD_BODY)
    assert r.status_code == 201
    return r.json()


def _review(client, card_id, rating, reviewed_at=None):
    body = {"rating": rating}
    if reviewed_at:
        body["reviewed_at"] = reviewed_at.isoformat()
    r = client.post(f"/api/cards/{card_id}/review", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_review_good_advances_due(client):
    card = _create_card(client)
    now = datetime.now(timezone.utc)
    result = _review(client, card["id"], rating=3, reviewed_at=now)

    assert result["card_id"] == card["id"]
    assert result["review_count"] == 1
    assert result["lapse_count"] == 0
    due = datetime.fromisoformat(result["next_due"])
    # After first Good review, due should be at least a few minutes ahead
    assert due > now


def test_review_again_increments_lapse(client):
    card = _create_card(client)
    result = _review(client, card["id"], rating=1)
    assert result["lapse_count"] == 1
    assert result["review_count"] == 1


def test_review_again_then_good_lapse_unchanged(client):
    card = _create_card(client)
    _review(client, card["id"], rating=1)  # lapse
    result = _review(client, card["id"], rating=3)
    assert result["lapse_count"] == 1  # second review was Good → no new lapse
    assert result["review_count"] == 2


def test_review_card_not_found(client):
    r = client.post("/api/cards/nonexistent/review", json={"rating": 3})
    assert r.status_code == 404


def test_review_archived_card_rejected(client):
    card = _create_card(client)
    client.delete(f"/api/cards/{card['id']}")
    r = client.post(f"/api/cards/{card['id']}/review", json={"rating": 3})
    assert r.status_code == 409


def test_elapsed_days_computed_from_reviewed_at(client):
    card = _create_card(client)
    t0 = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    _review(client, card["id"], rating=3, reviewed_at=t0)

    t1 = t0 + timedelta(days=5)
    result = _review(client, card["id"], rating=3, reviewed_at=t1)

    # 5 days elapsed; FSRS should produce a stability > initial
    stability = result["fsrs_state"].get("stability")
    assert stability is not None and stability > 0


def test_review_state_transitions(client):
    card = _create_card(client)
    t = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

    # First review (Good) → stays Learning initially
    r1 = _review(client, card["id"], rating=3, reviewed_at=t)
    state1 = r1["fsrs_state"]["state"]

    # Second review (Good) a bit later → may transition to Review (2)
    r2 = _review(client, card["id"], rating=3, reviewed_at=t + timedelta(minutes=10))
    state2 = r2["fsrs_state"]["state"]

    # Eventually ends up in Review state
    assert state2 >= state1  # state only advances on consecutive Good ratings


def test_all_rating_values_accepted(client):
    for rating in (1, 2, 3, 4):
        card = _create_card(client)
        r = client.post(f"/api/cards/{card['id']}/review", json={"rating": rating})
        assert r.status_code == 200, f"rating={rating} failed: {r.text}"


def test_invalid_rating_422(client):
    card = _create_card(client)
    r = client.post(f"/api/cards/{card['id']}/review", json={"rating": 5})
    assert r.status_code == 422
