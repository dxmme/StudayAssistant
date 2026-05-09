from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

MaterialType = Literal["lecture_slides", "script", "past_exam", "topic_overview"]


class MaterialResponse(BaseModel):
    id: str
    course_id: Optional[str]
    type: Optional[str]
    title: Optional[str]
    file_path: Optional[str]
    page_count: Optional[int]
    indexed: bool
    uploaded_at: Optional[datetime]

    model_config = {"from_attributes": True}
