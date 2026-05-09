from pydantic import BaseModel, Field


class WeeklyAvailability(BaseModel):
    mon: int = Field(ge=0, le=480)
    tue: int = Field(ge=0, le=480)
    wed: int = Field(ge=0, le=480)
    thu: int = Field(ge=0, le=480)
    fri: int = Field(ge=0, le=480)
    sat: int = Field(ge=0, le=480)
    sun: int = Field(ge=0, le=480)


class UserProfileResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    display_name: str | None
    weekly_availability_minutes: WeeklyAvailability
    max_session_minutes: int


class UserProfileUpdate(BaseModel):
    display_name: str | None = None
    weekly_availability_minutes: WeeklyAvailability | None = None
    max_session_minutes: int | None = Field(default=None, ge=15, le=180)
