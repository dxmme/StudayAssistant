from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.me import UserProfileResponse, UserProfileUpdate
from app.db.models.user_preferences import (
    DEFAULT_AVAILABILITY,
    DEFAULT_USER_ID,
    UserPreferences,
)
from app.db.session import get_db

router = APIRouter()


def _get_or_create_prefs(db: Session) -> UserPreferences:
    prefs = db.get(UserPreferences, DEFAULT_USER_ID)
    if prefs is None:
        now = datetime.utcnow()
        prefs = UserPreferences(
            id=DEFAULT_USER_ID,
            weekly_availability_minutes=DEFAULT_AVAILABILITY,
            max_session_minutes=90,
            created_at=now,
            updated_at=now,
        )
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.get("/me", response_model=UserProfileResponse)
def get_me(db: Session = Depends(get_db)) -> UserProfileResponse:
    return UserProfileResponse.model_validate(_get_or_create_prefs(db))


@router.patch("/me", response_model=UserProfileResponse)
def patch_me(
    body: UserProfileUpdate,
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    prefs = _get_or_create_prefs(db)
    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        if field == "weekly_availability_minutes":
            setattr(prefs, field, value if isinstance(value, dict) else value.model_dump())
        else:
            setattr(prefs, field, value)
    prefs.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prefs)
    return UserProfileResponse.model_validate(prefs)
