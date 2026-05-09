from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class CourseCreate(BaseModel):
    name: str
    semester: Optional[str] = None
    exam_date: Optional[date] = None
    exam_format: Optional[str] = None
    professor: Optional[str] = None
    notes: Optional[str] = None


class CourseResponse(BaseModel):
    id: str
    name: str
    semester: Optional[str]
    exam_date: Optional[date]
    exam_format: Optional[str]
    professor: Optional[str]
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}
