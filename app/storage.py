"""Private S3 object storage used for optional AWS-only feature testing."""
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

def _client_and_bucket():
    bucket = os.getenv("S3_BUCKET_NAME")
    region = os.getenv("AWS_REGION", "ap-south-1")
    if not bucket:
        raise HTTPException(status_code=503, detail="S3_BUCKET_NAME is not configured")
    try:
        import boto3
        return boto3.client("s3", region_name=region), bucket
    except Exception as exc:
        raise HTTPException(status_code=503, detail="AWS S3 client is unavailable") from exc

async def upload_private_file(upload: UploadFile, owner_id: int) -> dict:
    content = await upload.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Maximum upload size is 10 MB")
    suffix = Path(upload.filename or "").suffix.lower()[:10]
    key = f"uploads/{owner_id}/{uuid.uuid4().hex}{suffix}"
    client, bucket = _client_and_bucket()
    try:
        client.put_object(
            Bucket=bucket, Key=key, Body=content,
            ContentType=upload.content_type or "application/octet-stream",
            ServerSideEncryption="AES256",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="S3 upload failed") from exc
    return {"bucket": bucket, "key": key, "size_bytes": len(content)}

def create_private_download_url(key: str, owner_id: int) -> dict:
    if not key.startswith(f"uploads/{owner_id}/") or ".." in key.split("/"):
        raise HTTPException(status_code=400, detail="Invalid object key")
    client, bucket = _client_and_bucket()
    try:
        url = client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=300
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to create download URL") from exc
    return {"download_url": url, "expires_in_seconds": 300}
