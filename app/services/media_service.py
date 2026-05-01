import logging
from uuid import uuid4

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

logger = logging.getLogger(__name__)


def _looks_like_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return True

    return (
        (normalized.startswith("<") and normalized.endswith(">"))
        or normalized.startswith("your_")
        or "replace" in normalized
        or normalized in {"changeme", "change_me", "todo", "tbd"}
    )


def _ensure_cloudinary_configured() -> None:
    if settings.CLOUDINARY_URL:
        cloudinary.config(cloudinary_url=settings.CLOUDINARY_URL, secure=True)
        return

    if (
        _looks_like_placeholder(settings.CLOUDINARY_CLOUD_NAME)
        or _looks_like_placeholder(settings.CLOUDINARY_API_KEY)
        or _looks_like_placeholder(settings.CLOUDINARY_API_SECRET)
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary credentials are missing or still using placeholder values",
        )

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def save_exam_image(upload: UploadFile) -> dict:
    _ensure_cloudinary_configured()

    content_type = (upload.content_type or "").strip().lower()
    extension = ALLOWED_IMAGE_CONTENT_TYPES.get(content_type)
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Allowed: jpg, png, webp, gif",
        )

    file_bytes = upload.file.read(settings.MAX_IMAGE_UPLOAD_BYTES + 1)
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded image is empty")

    if len(file_bytes) > settings.MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image is too large. Max size is {settings.MAX_IMAGE_UPLOAD_BYTES} bytes",
        )

    filename = upload.filename or f"{uuid4().hex}{extension}"
    public_id = uuid4().hex
    try:
        upload_result = cloudinary.uploader.upload(
            file_bytes,
            resource_type="image",
            folder=settings.CLOUDINARY_UPLOAD_FOLDER.strip("/") or None,
            public_id=public_id,
            overwrite=False,
        )
    except cloudinary.exceptions.Error as exc:
        logger.exception("Cloudinary upload failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloudinary upload failed. Verify the Cloudinary credentials and account settings.",
        ) from exc

    return {
        "filename": filename,
        "content_type": content_type,
        "size_bytes": len(file_bytes),
        "public_id": upload_result["public_id"],
        "url": upload_result.get("secure_url") or upload_result.get("url") or "",
    }
