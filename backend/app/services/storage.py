import uuid
from datetime import datetime, timezone
from io import BytesIO

import boto3
from botocore.config import Config

from app.config import settings
from app.core.logging import logger


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"{'https' if settings.minio_use_ssl else 'http'}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        region_name="auto",
    )


def upload_file(file_bytes: bytes, source_type: str, extension: str) -> str:
    """Upload a file to MinIO/S3 and return the object key."""
    now = datetime.now(timezone.utc)
    file_id = uuid.uuid4().hex
    key = f"{source_type}/{now.year}/{now.month:02d}/{now.day:02d}/{file_id}.{extension}"

    client = _get_s3_client()
    client.upload_fileobj(BytesIO(file_bytes), settings.minio_bucket, key)
    logger.info("Uploaded file to %s (%d bytes)", key, len(file_bytes))
    return key


def download_file(key: str) -> bytes:
    """Download a file from MinIO/S3."""
    client = _get_s3_client()
    response = client.get_object(Bucket=settings.minio_bucket, Key=key)
    return response["Body"].read()


def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for temporary file access."""
    client = _get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.minio_bucket, "Key": key},
        ExpiresIn=expires_in,
    )
