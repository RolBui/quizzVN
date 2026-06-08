import logging
from uuid import uuid4

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import engine
from app.models.uploaded_image import UploadedImage

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
ALLOWED_CHAT_FILE_CONTENT_TYPES = {
    **ALLOWED_IMAGE_CONTENT_TYPES,
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/zip": ".zip",
}
ALLOWED_DOCUMENT_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

logger = logging.getLogger(__name__)


def bootstrap_media_storage() -> None:
    """Create the uploaded_images table if it does not exist."""
    UploadedImage.__table__.create(bind=engine, checkfirst=True)


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


def _upload_to_cloudinary(upload: UploadFile) -> dict:
    """Upload file to Cloudinary and return raw metadata (no DB)."""
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


def upload_chat_file(upload: UploadFile) -> dict:
    """Upload a chat attachment to Cloudinary and return file metadata."""
    _ensure_cloudinary_configured()

    content_type = (upload.content_type or "").strip().lower()
    extension = ALLOWED_CHAT_FILE_CONTENT_TYPES.get(content_type)
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed: images, pdf, office documents, txt, csv, zip",
        )

    file_bytes = upload.file.read(settings.MAX_CHAT_FILE_UPLOAD_BYTES + 1)
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    if len(file_bytes) > settings.MAX_CHAT_FILE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File is too large. Max size is {settings.MAX_CHAT_FILE_UPLOAD_BYTES} bytes",
        )

    filename = upload.filename or f"{uuid4().hex}{extension}"
    is_image = content_type in ALLOWED_IMAGE_CONTENT_TYPES
    resource_type = "image" if is_image else "raw"
    public_id = uuid4().hex if is_image else f"{uuid4().hex}{extension}"
    try:
        upload_result = cloudinary.uploader.upload(
            file_bytes,
            resource_type=resource_type,
            folder=settings.CLOUDINARY_CHAT_UPLOAD_FOLDER.strip("/") or None,
            public_id=public_id,
            overwrite=False,
        )
    except cloudinary.exceptions.Error as exc:
        logger.exception("Cloudinary chat file upload failed")
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


def upload_document_file(upload: UploadFile) -> dict:
    """Upload a learning document file to Cloudinary and return file metadata."""
    _ensure_cloudinary_configured()

    content_type = (upload.content_type or "").strip().lower()
    extension = ALLOWED_DOCUMENT_CONTENT_TYPES.get(content_type)
    if not extension:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported document type. Allowed: pdf, docx",
        )

    file_bytes = upload.file.read(settings.MAX_DOCUMENT_UPLOAD_BYTES + 1)
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded document is empty")

    if len(file_bytes) > settings.MAX_DOCUMENT_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is too large. Max size is {settings.MAX_DOCUMENT_UPLOAD_BYTES} bytes",
        )

    filename = upload.filename or f"{uuid4().hex}{extension}"
    public_id = f"{uuid4().hex}{extension}"
    try:
        upload_result = cloudinary.uploader.upload(
            file_bytes,
            resource_type="raw",
            folder=settings.CLOUDINARY_DOCUMENT_UPLOAD_FOLDER.strip("/") or None,
            public_id=public_id,
            overwrite=False,
        )
    except cloudinary.exceptions.Error as exc:
        logger.exception("Cloudinary document upload failed")
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


def delete_document_file(public_id: str | None) -> None:
    """Best-effort delete for a raw document file stored in Cloudinary."""
    if not public_id:
        return

    try:
        _ensure_cloudinary_configured()
        cloudinary.uploader.destroy(public_id, resource_type="raw")
    except Exception:
        logger.warning("Failed to delete document %s from Cloudinary", public_id)


def save_exam_image(db: Session, user_id: int, upload: UploadFile) -> dict:
    """Upload image to Cloudinary and persist metadata in the DB."""
    image_data = _upload_to_cloudinary(upload)

    record = UploadedImage(
        uploaded_by_user_id=user_id,
        filename=image_data["filename"],
        content_type=image_data["content_type"],
        size_bytes=image_data["size_bytes"],
        public_id=image_data["public_id"],
        url=image_data["url"],
        category="exam",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "filename": record.filename,
        "content_type": record.content_type,
        "size_bytes": record.size_bytes,
        "public_id": record.public_id,
        "url": record.url,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def save_avatar_image(db: Session, user_id: int, upload: UploadFile) -> dict:
    """Upload avatar image to Cloudinary and persist metadata in the DB."""
    image_data = _upload_to_cloudinary(upload)

    record = UploadedImage(
        uploaded_by_user_id=user_id,
        filename=image_data["filename"],
        content_type=image_data["content_type"],
        size_bytes=image_data["size_bytes"],
        public_id=image_data["public_id"],
        url=image_data["url"],
        category="avatar",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "filename": record.filename,
        "content_type": record.content_type,
        "size_bytes": record.size_bytes,
        "public_id": record.public_id,
        "url": record.url,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def list_uploaded_images(db: Session, user_id: int, category: str = "exam") -> list[dict]:
    """Return all uploaded images for a given user and category."""
    rows = (
        db.query(UploadedImage)
        .filter(
            UploadedImage.uploaded_by_user_id == user_id,
            UploadedImage.category == category,
        )
        .order_by(UploadedImage.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "content_type": r.content_type,
            "size_bytes": r.size_bytes,
            "public_id": r.public_id,
            "url": r.url,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def _delete_uploaded_image_record(db: Session, record: UploadedImage) -> None:
    try:
        _ensure_cloudinary_configured()
        cloudinary.uploader.destroy(record.public_id, resource_type="image")
    except Exception:
        logger.warning("Failed to delete image %s from Cloudinary, removing DB record anyway", record.public_id)

    db.delete(record)
    db.commit()


def delete_uploaded_avatars_except_url(db: Session, user_id: int, avatar_url: str) -> int:
    """Delete all uploaded avatar records for a user except the active avatar URL."""
    records = (
        db.query(UploadedImage)
        .filter(
            UploadedImage.uploaded_by_user_id == user_id,
            UploadedImage.category == "avatar",
            UploadedImage.url != avatar_url,
        )
        .all()
    )

    deleted_count = 0
    for record in records:
        _delete_uploaded_image_record(db, record)
        deleted_count += 1

    return deleted_count


def delete_uploaded_image(db: Session, user_id: int, image_id: int) -> None:
    """Delete an uploaded image from Cloudinary and the DB."""
    record = (
        db.query(UploadedImage)
        .filter(
            UploadedImage.id == image_id,
            UploadedImage.uploaded_by_user_id == user_id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    _delete_uploaded_image_record(db, record)
