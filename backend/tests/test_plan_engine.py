import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.cards import Card
from app.db.models.concepts import Concept, ConceptEdge
from app.db.models.courses import Course
from app.db.models.user_preferences import UserPreferences


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_course(db: Session, exam_date: date | None = None) -> Course:
    course = Course(id=str(uuid.uuid4()), name="Test Course", exam_date=exam_date)
    db.add(course)
    db.commit()
    return course


def make_concept(
    db: Session,
    course_id: str,
    name: str = "Konzept",
    importance: float = 0.5,
) -> Concept:
    concept = Concept(
        id=str(uuid.uuid4()),
        course_id=course_id,
        name=name,
        importance=importance,
    )
    db.add(concept)
    db.commit()
    return concept


def make_card(
    db: Session,
    course_id: str,
    concept_id: str | None = None,
    due: str | None = None,
    stability: float = 0.0,
) -> Card:
    today = date.today().isoformat()
    card = Card(
        id=str(uuid.uuid4()),
        course_id=course_id,
        concept_id=concept_id,
        front="Q",
        back="A",
        fsrs_state={"due": due or today, "stability": stability},
        archived=False,
    )
    db.add(card)
    db.commit()
    return card


def make_concept_edge(db: Session, src: str, dst: str) -> ConceptEdge:
    edge = ConceptEdge(src=src, dst=dst, relation="prerequisite")
    db.add(edge)
    db.commit()
    return edge


def make_prefs(db: Session, max_session_minutes: int = 90) -> UserPreferences:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    prefs = UserPreferences(
        id="default",
        max_session_minutes=max_session_minutes,
        weekly_availability_minutes={
            "mon": 120, "tue": 120, "wed": 120,
            "thu": 120, "fri": 120, "sat": 0, "sun": 0,
        },
        created_at=now,
        updated_at=now,
    )
    db.add(prefs)
    db.commit()
    return prefs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_plan_creates_session(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session)
    make_card(db_session, course.id)

    r = client.post(f"/api/courses/{course.id}/plan/today")
    assert r.status_code == 201
    data = r.json()
    assert data["course_id"] == course.id
    assert data["status"] == "pending"
    assert data["completed_at"] is None
    types = [i["type"] for i in data["items"]]
    assert "card_review" in types


def test_plan_idempotent(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session)
    make_card(db_session, course.id)

    r1 = client.post(f"/api/courses/{course.id}/plan/today")
    r2 = client.post(f"/api/courses/{course.id}/plan/today")

    assert r1.status_code == 201
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


def test_plan_get_today_existing(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session)
    make_card(db_session, course.id)

    post = client.post(f"/api/courses/{course.id}/plan/today")
    get = client.get(f"/api/courses/{course.id}/plan/today")

    assert get.status_code == 200
    assert get.json()["id"] == post.json()["id"]


def test_plan_get_today_none(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session)

    r = client.get(f"/api/courses/{course.id}/plan/today")
    assert r.status_code == 404


def test_plan_no_exam_date_semester_companion(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session, exam_date=None)
    make_concept(db_session, course.id, name="SVD")

    r = client.post(f"/api/courses/{course.id}/plan/today")
    assert r.status_code == 201
    types = [i["type"] for i in r.json()["items"]]
    assert "new_concept" in types


def test_plan_phase_active_preparation(client: TestClient, db_session: Session) -> None:
    exam = date.today() + timedelta(days=20)
    course = make_course(db_session, exam_date=exam)
    make_concept(db_session, course.id, name="EM")

    r = client.post(f"/api/courses/{course.id}/plan/today")
    assert r.status_code == 201
    types = [i["type"] for i in r.json()["items"]]
    assert "new_concept" in types


def test_plan_phase_consolidation(client: TestClient, db_session: Session) -> None:
    exam = date.today() + timedelta(days=10)
    course = make_course(db_session, exam_date=exam)
    make_concept(db_session, course.id, name="SVM")
    make_card(db_session, course.id)

    r = client.post(f"/api/courses/{course.id}/plan/today")
    assert r.status_code == 201
    types = [i["type"] for i in r.json()["items"]]
    assert "new_concept" not in types
    assert "coaching" not in types


def test_plan_phase_final_review(client: TestClient, db_session: Session) -> None:
    exam = date.today() + timedelta(days=2)
    course = make_course(db_session, exam_date=exam)
    make_concept(db_session, course.id, name="SGD")
    make_card(db_session, course.id)

    r = client.post(f"/api/courses/{course.id}/plan/today")
    assert r.status_code == 201
    types = [i["type"] for i in r.json()["items"]]
    assert "new_concept" not in types
    assert "coaching" not in types


def test_plan_empty_curriculum(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session)
    make_card(db_session, course.id)

    r = client.post(f"/api/courses/{course.id}/plan/today")
    assert r.status_code == 201
    types = [i["type"] for i in r.json()["items"]]
    assert types == ["card_review"]


def test_plan_no_cards_no_concepts(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session)

    r = client.post(f"/api/courses/{course.id}/plan/today")
    assert r.status_code == 201
    data = r.json()
    assert data["items"] == []
    assert data["duration_min"] == 0


def test_plan_concept_topological_order(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session, exam_date=None)
    concept_a = make_concept(db_session, course.id, name="A", importance=0.9)
    concept_b = make_concept(db_session, course.id, name="B", importance=1.0)
    # B requires A — A not mastered → only A is candidate
    make_concept_edge(db_session, src=concept_a.id, dst=concept_b.id)

    r = client.post(f"/api/courses/{course.id}/plan/today")
    assert r.status_code == 201
    new_concept_items = [i for i in r.json()["items"] if i["type"] == "new_concept"]
    assert len(new_concept_items) == 1
    assert new_concept_items[0]["concept_id"] == concept_a.id


def test_plan_mastery_skip(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session, exam_date=None)
    concept = make_concept(db_session, course.id, name="Mastered")
    # Card with high stability → mastered
    make_card(db_session, course.id, concept_id=concept.id, stability=25.0)

    r = client.post(f"/api/courses/{course.id}/plan/today")
    assert r.status_code == 201
    types = [i["type"] for i in r.json()["items"]]
    assert "new_concept" not in types


def test_plan_budget_trim(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session, exam_date=None)
    make_concept(db_session, course.id, name="Trim")
    make_prefs(db_session, max_session_minutes=15)

    r = client.post(f"/api/courses/{course.id}/plan/today")
    assert r.status_code == 201
    types = [i["type"] for i in r.json()["items"]]
    # budget=15: new_concept costs 10 → fits; coaching costs 15 more → does not fit
    assert "new_concept" in types
    assert "coaching" not in types


def test_plan_mark_item_complete(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session)
    make_card(db_session, course.id)

    plan_id = client.post(f"/api/courses/{course.id}/plan/today").json()["id"]
    r = client.patch(f"/api/plans/{plan_id}/items/0/complete")
    assert r.status_code == 200
    assert r.json()["items"][0]["done"] is True


def test_plan_mark_item_out_of_range(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session)
    make_card(db_session, course.id)

    plan_id = client.post(f"/api/courses/{course.id}/plan/today").json()["id"]
    r = client.patch(f"/api/plans/{plan_id}/items/99/complete")
    assert r.status_code == 422


def test_plan_complete_session(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session)
    make_card(db_session, course.id)

    plan_id = client.post(f"/api/courses/{course.id}/plan/today").json()["id"]
    r = client.post(f"/api/plans/{plan_id}/complete")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


def test_plan_course_not_found(client: TestClient) -> None:
    r = client.post("/api/courses/nonexistent/plan/today")
    assert r.status_code == 404
    assert r.json()["detail"] == "Course not found"
