import hashlib
from pathlib import Path

from app.core.config import settings

DEFAULT_EXAM_COVER_FILENAMES = (
    "exam-cover-1.jpeg",
    "exam-cover-2.jpeg",
    "exam-cover-3.jpeg",
    "exam-cover-4.jpeg",
)

_ASSETS_DIR = Path(__file__).resolve().parents[2] / "admin-web" / "src" / "assets"


def _cover_seed(*parts: object) -> str:
    seed = " ".join(str(part or "").strip() for part in parts).strip()
    return seed or "default-exam-cover"


def get_default_exam_cover_filename(*seed_parts: object) -> str:
    digest = hashlib.sha256(_cover_seed(*seed_parts).encode("utf-8")).digest()
    index = int.from_bytes(digest[:4], "big") % len(DEFAULT_EXAM_COVER_FILENAMES)
    return DEFAULT_EXAM_COVER_FILENAMES[index]


def get_default_exam_cover_url(*seed_parts: object) -> str:
    filename = get_default_exam_cover_filename(*seed_parts)
    return f"{settings.BACKEND_URL}/assets/{filename}"


def resolve_exam_image_url(image_url: str | None, *seed_parts: object) -> str:
    normalized = (image_url or "").strip()
    if normalized:
        return normalized
    return get_default_exam_cover_url(*seed_parts)


def get_default_exam_cover_path(filename: str) -> Path:
    if filename not in DEFAULT_EXAM_COVER_FILENAMES:
        raise ValueError("Unknown default exam cover")
    return _ASSETS_DIR / filename
