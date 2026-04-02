import asyncio
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
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
from app.services.phi_scrubber import scrub_text, scrub_text_with_stats
from app.core.audit import log_event, log_event_standalone
from app.core.security import get_current_tenant
from app.models.database import Organization
from app.services.llm.extraction import extract_prior_auth_data

router = APIRouter()


def _validate_file_size(file_bytes: bytes):
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB.",
        )


async def _process_text_ingestion(job_id: uuid.UUID, text: str):
    """Background task: scrub PHI, run LLM extraction, store results.

    Creates its own DB session — does NOT reuse the request session,
    which closes after the response is sent.
    """
    from app.core.db import async_session

    async with async_session() as db:
        try:
            job = await db.get(IngestionJob, job_id)
            if job:
                job.status = "processing"
                await db.commit()

            # Check budget cap before calling Claude (saves API costs)
            if job and job.tenant_id:
                from app.api.v1.billing import record_extraction_usage
                tenant_org = await db.get(Organization, job.tenant_id)
                if tenant_org:
                    allowed = await record_extraction_usage(db, tenant_org)
                    if not allowed:
                        job = await db.get(IngestionJob, job_id)
                        if job:
                            job.status = "failed"
                            job.error_message = "Monthly overage budget cap reached. Increase your budget at /billing or upgrade your plan."
                            await db.commit()
                        return

            scrub_result = scrub_text_with_stats(text)
            scrubbed = scrub_result.text

            await log_event(
                db, "phi_scrub", "ingestion_job", job_id,
                metadata={
                    "regex_redactions": scrub_result.regex_count,
                    "presidio_redactions": scrub_result.presidio_count,
                    "total_redactions": scrub_result.total_redactions,
                },
            )
            await db.commit()

            extraction = await extract_prior_auth_data(scrubbed)

            result = ExtractionResult(
                tenant_id=job.tenant_id if job else None,
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
            await db.refresh(result)

            await log_event(
                db, "extract", "extraction_result", result.id,
                metadata={
                    "ingestion_job_id": str(job_id),
                    "diagnosis_code": extraction.diagnosis_code,
                    "confidence": extraction.confidence_score,
                },
            )
            await db.commit()

            logger.info("Job %s completed successfully", str(job_id))

        except Exception as e:
            logger.error("Job %s failed: %s", str(job_id), str(e))
            async with async_session() as err_db:
                job = await err_db.get(IngestionJob, job_id)
                if job:
                    job.status = "failed"
                    job.error_message = str(e)
                    await err_db.commit()


# --- Endpoints ---


@router.post("/dicom", response_model=IngestionResponse)
async def ingest_dicom(
    request: Request,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
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
        tenant_id=tenant.id,
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

    await log_event(
        db, "ingest", "ingestion_job", job.id,
        ip_address=request.client.host if request.client else None,
        metadata={"source_type": "dicom", "file_size": len(file_bytes)},
    )
    await db.commit()

    return IngestionResponse(
        job_id=job.id,
        status="completed",
        message="DICOM file processed and de-identified",
        metadata=metadata,
        file_key=file_key,
    )


async def _ingest_note(
    text: str,
    filename: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    tenant_id: uuid.UUID | None = None,
) -> IngestionResponse:
    """Shared logic for clinical note ingestion."""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Clinical note text cannot be empty")
    if len(text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Clinical note text is too short to extract meaningful data")
    size = len(text.encode("utf-8"))
    file_key = storage.upload_file(text.encode("utf-8"), "clinical_note", "txt")

    job = IngestionJob(
        tenant_id=tenant_id,
        source_type="clinical_note",
        status="pending",
        file_key=file_key,
        original_filename=filename,
        file_size_bytes=size,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(_process_text_ingestion, job.id, text)

    return IngestionResponse(
        job_id=job.id,
        status="processing",
        message="Clinical note received. Extraction in progress.",
        file_key=file_key,
    )


@router.post("/clinical-note", response_model=IngestionResponse)
async def ingest_clinical_note(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
    file: UploadFile | None = None,
):
    """Ingest a clinical note as text file upload."""
    if not file:
        raise HTTPException(status_code=400, detail="Provide a text file")
    text = (await file.read()).decode("utf-8")
    return await _ingest_note(text, file.filename or "upload.txt", background_tasks, db, tenant.id)


@router.post("/clinical-note/text", response_model=IngestionResponse)
async def ingest_clinical_note_text(
    body: ClinicalNoteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
):
    """Ingest a clinical note as JSON text body."""
    return await _ingest_note(body.text, "inline_note.txt", background_tasks, db, tenant.id)


@router.post("/robotic-report", response_model=IngestionResponse)
async def ingest_robotic_report(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    tenant: Organization = Depends(get_current_tenant),
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
        tenant_id=tenant.id,
        source_type="robotic_report",
        status="pending",
        file_key=file_key,
        original_filename=file.filename,
        file_size_bytes=len(file_bytes),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(_process_text_ingestion, job.id, text)

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
    tenant: Organization = Depends(get_current_tenant),
):
    """List ingestion jobs for the current tenant, most recent first."""
    result = await db.execute(
        select(IngestionJob)
        .where(IngestionJob.tenant_id == tenant.id)
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
                outcome=ext.outcome,
            )

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        source_type=job.source_type,
        created_at=job.created_at,
        extraction_result=extraction,
        error_message=job.error_message,
    )


@router.post("/jobs/{job_id}/retry", response_model=IngestionResponse)
async def retry_job(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed job by re-running the extraction pipeline."""
    job = await db.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed jobs can be retried")
    if not job.file_key:
        raise HTTPException(status_code=400, detail="No file stored for this job")

    # Re-download the stored file and re-run
    file_bytes = storage.download_file(job.file_key)

    if job.source_type == "clinical_note":
        text = file_bytes.decode("utf-8")
    elif job.source_type == "robotic_report":
        text = extract_text_from_pdf(file_bytes)
    else:
        raise HTTPException(status_code=400, detail="DICOM jobs do not support retry (already completed on upload)")

    job.status = "pending"
    job.error_message = None
    await db.commit()

    background_tasks.add_task(_process_text_ingestion, job.id, text)

    return IngestionResponse(
        job_id=job.id,
        status="processing",
        message="Job requeued for processing.",
    )


@router.get("/jobs/{job_id}/status")
async def job_status_sse(job_id: uuid.UUID):
    """SSE endpoint for real-time job processing status. Polls DB — survives deploys."""
    from app.core.db import async_session

    async def event_stream() -> AsyncGenerator[str, None]:
        last_status = None

        for _ in range(120):  # 2 minute timeout (120 * 2s)
            async with async_session() as db:
                job = await db.get(IngestionJob, job_id)

            if job:
                current_status = job.status
                if current_status != last_status:
                    progress = {
                        "pending": 0.1,
                        "processing": 0.5,
                        "completed": 1.0,
                        "failed": 0.0,
                    }.get(current_status, 0.0)
                    step = {
                        "pending": "queued",
                        "processing": "extracting",
                        "completed": "done",
                        "failed": "error",
                    }.get(current_status, current_status)

                    event = ProcessingStatusEvent(
                        status=current_status, step=step, progress=progress
                    )
                    yield f"event: status\ndata: {event.model_dump_json()}\n\n"
                    last_status = current_status

                    if current_status in ("completed", "failed"):
                        return

            await asyncio.sleep(2)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
