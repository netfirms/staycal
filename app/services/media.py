import os
import uuid
from typing import Optional

from ..config import settings


def _sniff_image_type(data: bytes) -> str | None:
    """Return a lowercase extension if bytes look like a common image, else None."""
    if not data or len(data) < 12:
        return None
    if data.startswith(b"\xFF\xD8\xFF"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    if data.startswith(b"BM"):
        return "bmp"
    return None

# Cloudinary is optional; import lazily
try:
    import cloudinary
    import cloudinary.uploader
except Exception:  # pragma: no cover - optional dependency
    cloudinary = None  # type: ignore


def _ensure_cloudinary_configured() -> bool:
    """
    Configure cloudinary from CLOUDINARY_URL if available.
    Returns True if Cloudinary is configured and usable.
    """
    url = getattr(settings, "CLOUDINARY_URL", "") or os.getenv("CLOUDINARY_URL", "")
    if not url or cloudinary is None:
        return False
    try:
        cloudinary.config(cloudinary_url=url)
        return True
    except Exception:
        return False


def save_image(file_bytes: bytes, original_filename: str | None = None, folder: str = "staycal") -> Optional[str]:
    """Save image to Cloudinary if configured; otherwise fallback to local uploads.

    Returns the public URL (secure) of the stored image, or None if input is not an image.
    """
    if not file_bytes:
        return None

    # Basic validation using lightweight header sniffing (Python 3.13-safe)
    kind = _sniff_image_type(file_bytes)
    if not kind:
        return None

    # Try Cloudinary first
    if _ensure_cloudinary_configured():
        try:
            public_id = uuid.uuid4().hex
            upload_res = cloudinary.uploader.upload(
                file_bytes,
                folder=folder,
                public_id=public_id,
                resource_type="image",
                overwrite=True,
            )
            # Prefer secure_url
            url = upload_res.get("secure_url") or upload_res.get("url")
            if url:
                return url
        except Exception:
            # fall back to local if cloudinary fails
            pass

    # Fallback: local file save in app/static/uploads
    try:
        os.makedirs("app/static/uploads", exist_ok=True)
        fname = f"{uuid.uuid4().hex}.{kind}"
        fpath = os.path.join("app/static/uploads", fname)
        with open(fpath, "wb") as f:
            f.write(file_bytes)
        return f"/static/uploads/{fname}"
    except Exception:
        return None
