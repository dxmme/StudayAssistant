from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.concepts import ConceptResponse
from app.api.schemas.graph import ConceptGraphResponse, GraphEdge, GraphNode
from app.db.models.concepts import Concept, ConceptEdge
from app.db.models.courses import Course
from app.db.session import get_db

router = APIRouter(tags=["concepts"])


@router.get("/api/courses/{course_id}/concepts", response_model=list[ConceptResponse])
def list_concepts(course_id: str, db: Session = Depends(get_db)) -> list[Concept]:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return db.query(Concept).filter(Concept.course_id == course_id).all()


@router.get("/api/courses/{course_id}/graph", response_model=ConceptGraphResponse)
def get_concept_graph(course_id: str, db: Session = Depends(get_db)) -> ConceptGraphResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    concepts = db.query(Concept).filter(Concept.course_id == course_id).all()
    concept_ids = {c.id for c in concepts}

    edges: list[ConceptEdge] = []
    if concept_ids:
        edges = (
            db.query(ConceptEdge)
            .filter(ConceptEdge.src.in_(concept_ids), ConceptEdge.dst.in_(concept_ids))
            .all()
        )

    return ConceptGraphResponse(
        nodes=[GraphNode(id=c.id, name=c.name, summary=c.summary, type=c.type) for c in concepts],
        edges=[GraphEdge(src=e.src, dst=e.dst, relation=e.relation) for e in edges],
    )
