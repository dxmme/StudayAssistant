from pydantic import BaseModel


class WorkedExampleResponse(BaseModel):
    content: str
