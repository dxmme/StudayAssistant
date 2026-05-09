from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel


class User(BaseModel):
    id: str
    name: str


async def get_current_user() -> User:
    return User(id="local", name="local-user")


CurrentUser = Annotated[User, Depends(get_current_user)]
