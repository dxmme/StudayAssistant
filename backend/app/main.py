from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import cards, coaching, concepts, courses, health, materials, me
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title="StudyAssistant API", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(me.router)
app.include_router(courses.router)
app.include_router(materials.router)
app.include_router(concepts.router)
app.include_router(cards.router, prefix="/api")
app.include_router(coaching.router)
