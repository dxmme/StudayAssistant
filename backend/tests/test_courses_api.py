def test_create_course(client):
    resp = client.post("/api/courses", json={"name": "Statistical ML"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Statistical ML"
    assert "id" in data
    assert data["semester"] is None


def test_create_course_with_all_fields(client):
    resp = client.post(
        "/api/courses",
        json={
            "name": "Deep Learning",
            "semester": "WS2425",
            "exam_format": "written",
            "professor": "Dr. Müller",
            "notes": "Hard exam",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["semester"] == "WS2425"
    assert data["professor"] == "Dr. Müller"


def test_list_courses_empty(client):
    resp = client.get("/api/courses")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_courses(client):
    client.post("/api/courses", json={"name": "Course A"})
    client.post("/api/courses", json={"name": "Course B"})
    resp = client.get("/api/courses")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_course_by_id(client):
    created = client.post("/api/courses", json={"name": "Linear Algebra"}).json()
    resp = client.get(f"/api/courses/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Linear Algebra"


def test_get_course_not_found(client):
    resp = client.get("/api/courses/nonexistent-id")
    assert resp.status_code == 404
