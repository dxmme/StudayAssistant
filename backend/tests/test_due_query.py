"""Due-card-query tests."""
from datetime import datetime, timedelta, timezone

_COURSE = "course-due-tests"
_BODY = {"type": "basic", "front": "Q", "back": "A"}


def _create_card(client):
    r = client.post(f"/api/courses/{_COURSE}/cards", json=_BODY)
    assert r.status_code == 201
    return r.json()


def _set_due(client, db_session, card_id, due_dt):
    """Directly patch fsrs_state.due in the DB to control test fixture timing."""
    from app.db.models.cards import Card

    card = db_session.get(Card, card_id)
    state = dict(card.fsrs_state)
    state["due"] = due_dt.isoformat()
    card.fsrs_state = state
    db_session.commit()
    db_session.refresh(card)


def test_due_returns_only_past_due(client, db_session):
    now = datetime.now(timezone.utc)
    c1 = _create_card(client)
    c2 = _create_card(client)
    c3 = _create_card(client)

    _set_due(client, db_session, c1["id"], now - timedelta(days=1))
    _set_due(client, db_session, c2["id"], now - timedelta(hours=1))
    _set_due(client, db_session, c3["id"], now + timedelta(days=3))

    r = client.get(f"/api/courses/{_COURSE}/cards/due")
    # c1 and c2 are due, c3 is not
    ids = [c["id"] for c in r.json()]
    assert c1["id"] in ids
    assert c2["id"] in ids
    assert c3["id"] not in ids


def test_due_excludes_archived(client, db_session):
    now = datetime.now(timezone.utc)
    c1 = _create_card(client)
    c2 = _create_card(client)

    _set_due(client, db_session, c1["id"], now - timedelta(days=1))
    _set_due(client, db_session, c2["id"], now - timedelta(days=1))

    client.delete(f"/api/cards/{c2['id']}")  # soft delete

    r = client.get(f"/api/courses/{_COURSE}/cards/due")
    ids = [c["id"] for c in r.json()]
    assert c1["id"] in ids
    assert c2["id"] not in ids


def test_due_sorted_ascending(client, db_session):
    now = datetime.now(timezone.utc)
    c1 = _create_card(client)
    c2 = _create_card(client)
    c3 = _create_card(client)

    _set_due(client, db_session, c1["id"], now - timedelta(days=3))
    _set_due(client, db_session, c2["id"], now - timedelta(days=1))
    _set_due(client, db_session, c3["id"], now - timedelta(hours=6))

    r = client.get(f"/api/courses/{_COURSE}/cards/due")
    dues = [c["fsrs_state"]["due"] for c in r.json()]
    assert dues == sorted(dues)


def test_due_empty_when_none_due(client, db_session):
    c = _create_card(client)
    future = datetime.now(timezone.utc) + timedelta(days=30)
    _set_due(client, db_session, c["id"], future)

    r = client.get(f"/api/courses/{_COURSE}/cards/due")
    assert r.json() == []


def test_due_default_on_is_today(client, db_session):
    c = _create_card(client)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    _set_due(client, db_session, c["id"], yesterday)

    r = client.get(f"/api/courses/{_COURSE}/cards/due")
    ids = [x["id"] for x in r.json()]
    assert c["id"] in ids
