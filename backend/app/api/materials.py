import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.schemas.materials import MaterialResponse, MaterialType
from app.core.config import settings
from app.db.models.courses import Course
from app.db.models.materials import Material, MaterialChunk
from app.db.session import SessionLocal, get_db
from app.services import parse_service
from app.services.ingest import IngestError, run_ingest
from app.services.rag import get_rag_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["materials"])


def _upload_dir(course_id: str) -> Path:
    d = settings.upload_dir / course_id
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("/api/courses/{course_id}/materials", response_model=MaterialResponse, status_code=201)
def upload_material(
    course_id: str,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    type: MaterialType = Form(...),
    title: str = Form(None),
    db: Session = Depends(get_db),
) -> Material:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Only application/pdf accepted")

    material_id = str(uuid.uuid4())
    derived_title = title or (Path(file.filename or "upload").stem)

    upload_dir = _upload_dir(course_id)
    pdf_path = upload_dir / f"{material_id}.pdf"

    pdf_bytes = file.file.read()
    pdf_path.write_bytes(pdf_bytes)

    # Quick page count via pymupdf — no ML, <100 ms
    import fitz  # type: ignore[import-untyped]
    doc = fitz.open(str(pdf_path))
    page_count = len(doc)
    doc.close()

    material = Material(
        id=material_id,
        course_id=course_id,
        type=type,
        title=derived_title,
        file_path=str(pdf_path),
        page_count=page_count,
        indexed=False,
        parse_status="pending",
        uploaded_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    logger.info(
        "material_uploaded",
        extra={
            "material_id": material_id,
            "course_id": course_id,
            "file_size_bytes": len(pdf_bytes),
            "page_count": page_count,
        },
    )

    background_tasks.add_task(_parse_background, material_id, pdf_path)
    return material


def _parse_background(material_id: str, pdf_path: Path) -> None:
    """Run Claude PDF extraction in background after upload response is returned."""
    db = SessionLocal()
    try:
        markdown_text, _ = parse_service.parse_pdf(pdf_path)
        pdf_path.with_suffix(".md").write_text(markdown_text, encoding="utf-8")
        material = db.query(Material).filter(Material.id == material_id).first()
        if material:
            material.parse_status = "done"
            db.commit()
        logger.info("parse_background_done", extra={"material_id": material_id})
    except Exception as exc:
        logger.error("parse_background_failed", extra={"material_id": material_id, "error": str(exc)})
        material = db.query(Material).filter(Material.id == material_id).first()
        if material:
            material.parse_status = "error"
            db.commit()
    finally:
        db.close()


@router.get("/api/courses/{course_id}/materials", response_model=list[MaterialResponse])
def list_materials(course_id: str, db: Session = Depends(get_db)) -> list[Material]:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return db.query(Material).filter(Material.course_id == course_id).all()


@router.get("/api/materials/{material_id}/parse-status")
def get_parse_status(material_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return {"material_id": material_id, "status": material.parse_status}


@router.get("/api/materials/{material_id}/markdown")
def get_markdown(material_id: str, db: Session = Depends(get_db)) -> FileResponse:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material or not material.file_path:
        raise HTTPException(status_code=404, detail="Material not found")
    md_path = Path(material.file_path).with_suffix(".md")
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="Markdown file not found")
    return FileResponse(str(md_path), media_type="text/markdown")


@router.post("/api/materials/{material_id}/ingest")
def ingest_material(material_id: str, db: Session = Depends(get_db)) -> dict:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if material.indexed:
        return {"status": "already_indexed"}
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=412,
            detail="OPENAI_API_KEY not configured. Set it in backend/.env to enable ingest.",
        )
    try:
        result = run_ingest(material, db, get_rag_service())
    except IngestError as exc:
        raise HTTPException(
            status_code=500, detail={"error": str(exc), "step": exc.step}
        )
    return {
        "status": "indexed",
        "chunks": result.chunks,
        "concepts": result.concepts,
        "duration_ms": result.duration_ms,
    }


@router.get("/api/materials/{material_id}/chunks")
def list_chunks(
    material_id: str, limit: int = 20, db: Session = Depends(get_db)
) -> list[dict]:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    chunks = (
        db.query(MaterialChunk)
        .filter(MaterialChunk.material_id == material_id)
        .order_by(MaterialChunk.chunk_index)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": c.id,
            "content": c.content,
            "page": c.page,
            "chunk_index": c.chunk_index,
            "token_count": c.token_count,
        }
        for c in chunks
    ]


@router.delete("/api/materials/{material_id}", status_code=204)
def delete_material(material_id: str, db: Session = Depends(get_db)) -> None:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    course_id = material.course_id or ""
    if material.indexed and course_id:
        get_rag_service().delete_material(course_id, material_id)
    if material.file_path:
        pdf_path = Path(material.file_path)
        pdf_path.unlink(missing_ok=True)
        pdf_path.with_suffix(".md").unlink(missing_ok=True)
    db.delete(material)
    db.commit()
