import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.user_preferences import DEFAULT_AVAILABILITY, DEFAULT_USER_ID, UserPreferences

DEFAULT_RESPONSE = {
    "id": DEFAULT_USER_ID,
    "display_name": None,
    "weekly_availability_minutes": DEFAULT_AVAILABILITY,
    "max_session_minutes": 90,
}


def test_get_me_creates_default(client: TestClient) -> None:
    r = client.get("/me")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == DEFAULT_USER_ID
    assert data["display_name"] is None
    assert data["weekly_availability_minutes"] == DEFAULT_AVAILABILITY
    assert data["max_session_minutes"] == 90


def test_get_me_idempotent(client: TestClient, db_session: Session) -> None:
    client.get("/me")
    client.get("/me")
    count = db_session.query(UserPreferences).count()
    assert count == 1


def test_patch_display_name(client: TestClient) -> None:
    r = client.patch("/me", json={"display_name": "Dominique"})
    assert r.status_code == 200
    assert r.json()["display_name"] == "Dominique"
    assert r.json()["max_session_minutes"] == 90


def test_patch_availability(client: TestClient) -> None:
    new_avail = {"mon": 180, "tue": 0, "wed": 180, "thu": 120, "fri": 60, "sat": 0, "sun": 0}
    r = client.patch("/me", json={"weekly_availability_minutes": new_avail})
    assert r.status_code == 200
    assert r.json()["weekly_availability_minutes"] == new_avail


def test_patch_partial_keeps_other_fields(client: TestClient) -> None:
    client.patch("/me", json={"max_session_minutes": 60})
    r = client.patch("/me", json={"display_name": "Test"})
    assert r.status_code == 200
    assert r.json()["max_session_minutes"] == 60
    assert r.json()["display_name"] == "Test"


def test_patch_max_session_invalid(client: TestClient) -> None:
    r = client.patch("/me", json={"max_session_minutes": 5})
    assert r.status_code == 422


def test_patch_availability_out_of_range(client: TestClient) -> None:
    bad_avail = {"mon": 600, "tue": 0, "wed": 0, "thu": 0, "fri": 0, "sat": 0, "sun": 0}
    r = client.patch("/me", json={"weekly_availability_minutes": bad_avail})
    assert r.status_code == 422
