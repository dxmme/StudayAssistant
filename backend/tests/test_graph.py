import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.concepts import Concept, ConceptEdge
from app.db.models.courses import Course


def make_course(db: Session) -> Course:
    course = Course(id=str(uuid.uuid4()), name="Test Course")
    db.add(course)
    db.commit()
    return course


def make_concept(db: Session, course_id: str, name: str = "Concept") -> Concept:
    concept = Concept(id=str(uuid.uuid4()), course_id=course_id, name=name, summary=f"{name} summary", type="theory")
    db.add(concept)
    db.commit()
    return concept


def make_edge(db: Session, src: str, dst: str, relation: str = "prerequisite") -> ConceptEdge:
    edge = ConceptEdge(src=src, dst=dst, relation=relation)
    db.add(edge)
    db.commit()
    return edge


def test_graph_course_not_found(client: TestClient) -> None:
    r = client.get("/api/courses/nonexistent/graph")
    assert r.status_code == 404
    assert r.json()["detail"] == "Course not found"


def test_graph_empty_course(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session)
    r = client.get(f"/api/courses/{course.id}/graph")
    assert r.status_code == 200
    data = r.json()
    assert data["nodes"] == []
    assert data["edges"] == []


def test_graph_returns_nodes_and_edges(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session)
    c1 = make_concept(db_session, course.id, "SGD")
    c2 = make_concept(db_session, course.id, "Gradient Descent")
    make_edge(db_session, c1.id, c2.id, "prerequisite")

    r = client.get(f"/api/courses/{course.id}/graph")
    assert r.status_code == 200
    data = r.json()

    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1

    node_names = {n["name"] for n in data["nodes"]}
    assert node_names == {"SGD", "Gradient Descent"}

    edge = data["edges"][0]
    assert edge["src"] == c1.id
    assert edge["dst"] == c2.id
    assert edge["relation"] == "prerequisite"


def test_graph_excludes_other_courses(client: TestClient, db_session: Session) -> None:
    course_a = make_course(db_session)
    course_b = make_course(db_session)

    c_a = make_concept(db_session, course_a.id, "A-Concept")
    c_b = make_concept(db_session, course_b.id, "B-Concept")
    # Edge crosses courses — must not appear in either course's graph
    make_edge(db_session, c_a.id, c_b.id)

    r = client.get(f"/api/courses/{course_a.id}/graph")
    data = r.json()
    assert len(data["nodes"]) == 1
    assert data["edges"] == []

    r = client.get(f"/api/courses/{course_b.id}/graph")
    data = r.json()
    assert len(data["nodes"]) == 1
    assert data["edges"] == []


def test_graph_edge_fields(client: TestClient, db_session: Session) -> None:
    course = make_course(db_session)
    c1 = make_concept(db_session, course.id, "A")
    c2 = make_concept(db_session, course.id, "B")
    make_edge(db_session, c1.id, c2.id, "related")

    r = client.get(f"/api/courses/{course.id}/graph")
    edge = r.json()["edges"][0]
    assert edge["src"] == c1.id
    assert edge["dst"] == c2.id
    assert edge["relation"] == "related"
