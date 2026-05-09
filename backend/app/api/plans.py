from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.plans import PlanSessionResponse
from app.db.models.courses import Course
from app.db.models.plans import PlanSession
from app.db.session import get_db
from app.services.plan_engine import generate_plan

router = APIRouter(tags=["plans"])


@router.post(
    "/api/courses/{course_id}/plan/today",
    response_model=PlanSessionResponse,
    status_code=201,
)
def post_plan_today(course_id: str, db: Session = Depends(get_db)) -> PlanSession | JSONResponse:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    plan, created = generate_plan(course_id, db)
    if not created:
        return JSONResponse(
            content=PlanSessionResponse.model_validate(plan).model_dump(mode="json"),
            status_code=200,
        )
    return plan


@router.get("/api/courses/{course_id}/plan/today", response_model=PlanSessionResponse)
def get_plan_today(course_id: str, db: Session = Depends(get_db)) -> PlanSession:
    plan = db.scalars(
        select(PlanSession).where(
            PlanSession.course_id == course_id,
            PlanSession.scheduled_date == date.today(),
        )
    ).first()
    if plan is None:
        raise HTTPException(status_code=404, detail="No plan for today")
    return plan


@router.patch(
    "/api/plans/{plan_id}/items/{item_index}/complete",
    response_model=PlanSessionResponse,
)
def complete_item(plan_id: str, item_index: int, db: Session = Depends(get_db)) -> PlanSession:
    plan = db.get(PlanSession, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    items = list(plan.items or [])
    if item_index < 0 or item_index >= len(items):
        raise HTTPException(status_code=422, detail="item_index out of range")
    items[item_index] = {**items[item_index], "done": True}
    plan.items = items
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/api/plans/{plan_id}/complete", response_model=PlanSessionResponse)
def complete_session(plan_id: str, db: Session = Depends(get_db)) -> PlanSession:
    plan = db.get(PlanSession, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.status = "completed"
    plan.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(plan)
    return plan
