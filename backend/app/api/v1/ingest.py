import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import logger
from app.dependencies import get_db

MAX_FILE_SIZE = settings.max_upload_size_mb * 1024 * 1024
from app.models.database import ExtractionResult, IngestionJob
from app.models.schemas import (
    ClinicalNoteRequest,
    IngestionResponse,
    JobStatusResponse,
    ExtractionResultResponse,
    ProcessingStatusEvent,
)
from app.services import storage
from app.services.dicom_service import parse_dicom
from app.services.pdf_parser import extract_text_from_pdf
from app.services.phi_scrubber import scrub_text
from app.services.llm.extraction import extract_prior_auth_data

router = APIRouter()

# In-memory status tracking for SSE (replace with Redis in Phase 2)
_job_status: dict[str, ProcessingStatusEvent] = {}


def _validate_file_size(file_bytes: bytes):
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB.",
        )


def _update_status(job_id: str, status: str, step: str, progress: float):
    _job_status[job_id] = ProcessingStatusEvent(status=status, step=step, progress=progress)


async def _process_text_ingestion(
    job_id: uuid.UUID,
    text: str,
    db: AsyncSession,
):
    """Background task: scrub PHI, run LLM extraction, store results."""
    job_id_str = str(job_id)
    try:
        _update_status(job_id_str, "processing", "phi_scrubbing", 0.2)
        scrubbed = scrub_text(text)

        _update_status(job_id_str, "processing", "llm_extraction", 0.5)
        extraction = await extract_prior_auth_data(scrubbed)

        _update_status(job_id_str, "processing", "saving_results", 0.8)

        result = ExtractionResult(
            ingestion_job_id=job_id,
            diagnosis_code=extraction.diagnosis_code,
            conservative_treatments_failed=extraction.conservative_treatments_failed,
            implant_type_requested=extraction.implant_type_requested,
            robotic_assistance_required=extraction.robotic_assistance_required,
            clinical_justification=extraction.clinical_justification,
            confidence_score=extraction.confidence_score,
            raw_extraction_json=extraction.model_dump(),
        )
        db.add(result)

        job = await db.get(IngestionJob, job_id)
        job.status = "completed"
        await db.commit()

        _update_status(job_id_str, "completed", "done", 1.0)
        logger.info("Job %s completed successfully", job_id_str)

    except Exception as e:
        logger.error("Job %s failed: %s", job_id_str, str(e))
        job = await db.get(IngestionJob, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(e)
            await db.commit()
        _update_status(job_id_str, "failed", "error", 0.0)


# --- Endpoints ---


@router.post("/dicom", response_model=IngestionResponse)
async def ingest_dicom(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    """Ingest a DICOM file: extract metadata, strip PHI, store de-identified copy."""
    if not file.filename or not file.filename.lower().endswith(".dcm"):
        raise HTTPException(status_code=400, detail="File must be a .dcm DICOM file")

    file_bytes = await file.read()
    _validate_file_size(file_bytes)

    try:
        metadata, deidentified_bytes = parse_dicom(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid DICOM file: {e}")

    file_key = storage.upload_file(deidentified_bytes, "dicom", "dcm")

    job = IngestionJob(
        source_type="dicom",
        status="completed",
        file_key=file_key,
        original_filename=file.filename,
        file_size_bytes=len(file_bytes),
        metadata_json=metadata,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    return IngestionResponse(
        job_id=job.id,
        status="completed",
        message="DICOM file processed and de-identified",
        metadata=metadata,
        file_key=file_key,
    )


@router.post("/clinical-note", response_model=IngestionResponse)
async def ingest_clinical_note(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    file: UploadFile | None = None,
    body: ClinicalNoteRequest | None = None,
):
    """Ingest a clinical note as text file or JSON body."""
    if file:
        text = (await file.read()).decode("utf-8")
        filename = file.filename
        size = len(text.encode("utf-8"))
    elif body:
        text = body.text
        filename = "inline_note.txt"
        size = len(text.encode("utf-8"))
    else:
        raise HTTPException(status_code=400, detail="Provide a text file or JSON body with 'text' field")

    file_key = storage.upload_file(text.encode("utf-8"), "clinical_note", "txt")

    job = IngestionJob(
        source_type="clinical_note",
        status="pending",
        file_key=file_key,
        original_filename=filename,
        file_size_bytes=size,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(_process_text_ingestion, job.id, text, db)

    return IngestionResponse(
        job_id=job.id,
        status="processing",
        message="Clinical note received. Extraction in progress.",
        file_key=file_key,
    )


@router.post("/robotic-report", response_model=IngestionResponse)
async def ingest_robotic_report(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Ingest a robotic report PDF: extract text, scrub PHI, run LLM extraction."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a .pdf file")

    file_bytes = await file.read()
    _validate_file_size(file_bytes)

    try:
        text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {e}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="PDF contains no extractable text")

    file_key = storage.upload_file(file_bytes, "robotic_report", "pdf")

    job = IngestionJob(
        source_type="robotic_report",
        status="pending",
        file_key=file_key,
        original_filename=file.filename,
        file_size_bytes=len(file_bytes),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(_process_text_ingestion, job.id, text, db)

    return IngestionResponse(
        job_id=job.id,
        status="processing",
        message="Robotic report received. PDF parsing and extraction in progress.",
        file_key=file_key,
    )


# --- Job List & Status ---


@router.get("/jobs")
async def list_jobs(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List all ingestion jobs, most recent first."""
    result = await db.execute(
        select(IngestionJob)
        .order_by(IngestionJob.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    jobs = result.scalars().all()
    return [
        {
            "job_id": str(job.id),
            "status": job.status,
            "source_type": job.source_type,
            "original_filename": job.original_filename,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
        for job in jobs
    ]


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get the status and results of an ingestion job."""
    job = await db.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    extraction = None
    if job.status == "completed":
        result = await db.execute(
            select(ExtractionResult).where(ExtractionResult.ingestion_job_id == job_id)
        )
        ext = result.scalar_one_or_none()
        if ext:
            extraction = ExtractionResultResponse(
                id=ext.id,
                diagnosis_code=ext.diagnosis_code,
                conservative_treatments_failed=ext.conservative_treatments_failed,
                implant_type_requested=ext.implant_type_requested,
                robotic_assistance_required=ext.robotic_assistance_required,
                clinical_justification=ext.clinical_justification,
                confidence_score=ext.confidence_score,
            )

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        source_type=job.source_type,
        created_at=job.created_at,
        extraction_result=extraction,
        error_message=job.error_message,
    )


@router.get("/jobs/{job_id}/status")
async def job_status_sse(job_id: uuid.UUID):
    """SSE endpoint for real-time job processing status."""

    async def event_stream() -> AsyncGenerator[str, None]:
        job_id_str = str(job_id)
        last_status = None

        for _ in range(120):  # 2 minute timeout (120 * 1s)
            current = _job_status.get(job_id_str)
            if current and current != last_status:
                yield f"event: status\ndata: {current.model_dump_json()}\n\n"
                last_status = current
                if current.status in ("completed", "failed"):
                    return
            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
