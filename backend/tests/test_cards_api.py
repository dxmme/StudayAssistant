"""CRUD and list/due-query tests for the cards API."""
import pytest

_COURSE = "course-x1"
_CARD_BODY = {"type": "basic", "front": "What is SVD?", "back": "A = U Sigma V^T"}


def _create_card(client, course_id=_COURSE, **overrides):
    body = {**_CARD_BODY, **overrides}
    r = client.post(f"/api/courses/{course_id}/cards", json=body)
    assert r.status_code == 201, r.text
    return r.json()


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_card_returns_201(client):
    r = client.post(f"/api/courses/{_COURSE}/cards", json=_CARD_BODY)
    assert r.status_code == 201
    data = r.json()
    assert data["type"] == "basic"
    assert data["front"] == "What is SVD?"
    assert data["archived"] is False
    assert data["review_count"] == 0
    assert data["lapse_count"] == 0
    assert data["fsrs_state"] is not None
    assert "due" in data["fsrs_state"]


def test_create_card_invalid_type_422(client):
    r = client.post(f"/api/courses/{_COURSE}/cards", json={**_CARD_BODY, "type": "invalid"})
    assert r.status_code == 422


def test_create_card_all_types(client):
    for t in ("basic", "cloze", "concept_diagram", "derivation", "proof_skeleton"):
        r = client.post(f"/api/courses/{_COURSE}/cards", json={**_CARD_BODY, "type": t})
        assert r.status_code == 201, f"Failed for type={t}: {r.text}"


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_card(client):
    card = _create_card(client)
    r = client.get(f"/api/cards/{card['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == card["id"]


def test_get_card_not_found(client):
    r = client.get("/api/cards/nonexistent")
    assert r.status_code == 404


# ── Patch ─────────────────────────────────────────────────────────────────────

def test_patch_card_front(client):
    card = _create_card(client)
    r = client.patch(f"/api/cards/{card['id']}", json={"front": "Updated front"})
    assert r.status_code == 200
    assert r.json()["front"] == "Updated front"
    assert r.json()["back"] == _CARD_BODY["back"]  # unchanged


def test_patch_card_archived(client):
    card = _create_card(client)
    r = client.patch(f"/api/cards/{card['id']}", json={"archived": True})
    assert r.status_code == 200
    assert r.json()["archived"] is True


def test_patch_card_not_found(client):
    r = client.patch("/api/cards/nonexistent", json={"front": "x"})
    assert r.status_code == 404


# ── Delete (soft) ─────────────────────────────────────────────────────────────

def test_delete_card_soft(client):
    card = _create_card(client)
    r = client.delete(f"/api/cards/{card['id']}")
    assert r.status_code == 204

    # Card still exists but archived
    r2 = client.get(f"/api/cards/{card['id']}")
    assert r2.status_code == 200
    assert r2.json()["archived"] is True


def test_delete_card_not_found(client):
    r = client.delete("/api/cards/nonexistent")
    assert r.status_code == 404


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_cards_excludes_archived_by_default(client):
    c1 = _create_card(client, front="Active")
    c2 = _create_card(client, front="ToArchive")
    client.delete(f"/api/cards/{c2['id']}")

    r = client.get(f"/api/courses/{_COURSE}/cards")
    ids = [c["id"] for c in r.json()]
    assert c1["id"] in ids
    assert c2["id"] not in ids


def test_list_cards_include_archived(client):
    c = _create_card(client)
    client.delete(f"/api/cards/{c['id']}")

    r = client.get(f"/api/courses/{_COURSE}/cards?include_archived=true")
    ids = [x["id"] for x in r.json()]
    assert c["id"] in ids


def test_list_cards_empty_course(client):
    r = client.get("/api/courses/empty-course/cards")
    assert r.status_code == 200
    assert r.json() == []
