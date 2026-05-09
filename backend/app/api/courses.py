import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.courses import CourseCreate, CourseResponse
from app.db.models.courses import Course
from app.db.session import get_db

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.post("", response_model=CourseResponse, status_code=201)
def create_course(body: CourseCreate, db: Session = Depends(get_db)) -> Course:
    course = Course(
        id=str(uuid.uuid4()),
        name=body.name,
        semester=body.semester,
        exam_date=body.exam_date,
        exam_format=body.exam_format,
        professor=body.professor,
        notes=body.notes,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("", response_model=list[CourseResponse])
def list_courses(db: Session = Depends(get_db)) -> list[Course]:
    return db.query(Course).all()


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: str, db: Session = Depends(get_db)) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course
