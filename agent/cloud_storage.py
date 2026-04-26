"""
Cloud storage for generated documents (DOCX, PDF, TXT).

Uses Cloudinary if credentials are set in .env, otherwise falls back
to local filesystem (agent/exports/).

Usage:
    from cloud_storage import upload_document, get_download_url

    url = upload_document(file_path, session_id, filename)
    # url is a public HTTPS link (Cloudinary) or a local path marker
"""

import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

CLOUD_NAME   = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
API_KEY      = os.getenv("CLOUDINARY_API_KEY", "").strip()
API_SECRET   = os.getenv("CLOUDINARY_API_SECRET", "").strip()

_cloudinary_ready = bool(CLOUD_NAME and API_KEY and API_SECRET)

if _cloudinary_ready:
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(
        cloud_name=CLOUD_NAME,
        api_key=API_KEY,
        api_secret=API_SECRET,
        secure=True,
    )
    print(f"[CloudStorage] Cloudinary configured → cloud={CLOUD_NAME}")
else:
    print("[CloudStorage] Cloudinary not configured — using local filesystem fallback")

# Local fallback directory
LOCAL_EXPORTS = Path(__file__).resolve().parent / "exports"
LOCAL_EXPORTS.mkdir(exist_ok=True)


def upload_document(file_path: str | Path, session_id: str, filename: str) -> dict:
    """
    Upload a document to Cloudinary (or keep locally as fallback).

    Returns:
        {
            "url": "https://res.cloudinary.com/...",   # public download URL
            "public_id": "nyayamitr/session_id/filename",
            "storage": "cloudinary" | "local",
            "filename": "fir_abc123.pdf",
        }
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if _cloudinary_ready:
        return _upload_cloudinary(file_path, session_id, filename)
    else:
        return _store_local(file_path, session_id, filename)


def _upload_cloudinary(file_path: Path, session_id: str, filename: str) -> dict:
    """Upload to Cloudinary under nyayamitr/{session_id}/"""
    suffix = file_path.suffix.lower()

    # Cloudinary resource type
    resource_type = "raw"  # for DOCX, PDF, TXT — not image/video

    public_id = f"nyayamitr/{session_id}/{filename}"

    result = cloudinary.uploader.upload(
        str(file_path),
        public_id=public_id,
        resource_type=resource_type,
        overwrite=True,
        use_filename=True,
        unique_filename=False,
    )

    url = result.get("secure_url", "")
    print(f"[CloudStorage] Uploaded to Cloudinary: {url}")

    return {
        "url": url,
        "public_id": public_id,
        "storage": "cloudinary",
        "filename": filename,
    }


def _store_local(file_path: Path, session_id: str, filename: str) -> dict:
    """Keep file in local exports directory."""
    dest_dir = LOCAL_EXPORTS / session_id
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / filename

    if file_path != dest:
        shutil.copy2(file_path, dest)

    # Return a local marker URL — the FastAPI server will serve this
    url = f"/document/{session_id}/{filename}"
    print(f"[CloudStorage] Stored locally: {dest}")

    return {
        "url": url,
        "public_id": str(dest),
        "storage": "local",
        "filename": filename,
    }


def delete_document(public_id: str, storage: str = "cloudinary") -> bool:
    """Delete a document from Cloudinary or local storage."""
    if storage == "cloudinary" and _cloudinary_ready:
        try:
            cloudinary.uploader.destroy(public_id, resource_type="raw")
            return True
        except Exception as e:
            print(f"[CloudStorage] Delete failed: {e}")
            return False
    elif storage == "local":
        p = Path(public_id)
        if p.exists():
            p.unlink()
            return True
    return False


def is_cloudinary_enabled() -> bool:
    return _cloudinary_ready
