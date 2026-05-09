from typing import Any, Optional

from pydantic import BaseModel


class ConceptResponse(BaseModel):
    id: str
    course_id: Optional[str]
    name: Optional[str]
    type: Optional[str]
    summary: Optional[str]
    source_pages: Optional[Any]

    model_config = {"from_attributes": True}
