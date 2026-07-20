"""
Standalone input validators.

Generic upload validation (file extension, MIME type, size limit). This is
infrastructure-level input validation, not RAG business logic, so it is
implemented for real rather than stubbed -- every upload should be rejected
early if it can't possibly be processed.
"""

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


def validate_file_extension(filename: str | None) -> None:
    """Raise HTTP 415 if `filename` doesn't end in an allowed extension."""
    settings = get_settings()
    allowed = settings.allowed_file_extensions_list
    if not filename or not any(filename.lower().endswith(ext) for ext in allowed):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type for '{filename}'. Allowed extensions: {allowed}",
        )


def validate_mime_type(content_type: str | None) -> None:
    """Raise HTTP 415 if `content_type` is not an allowed MIME type."""
    settings = get_settings()
    allowed = settings.allowed_mime_types_list
    if content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type '{content_type}'. Allowed: {allowed}",
        )


def validate_file_size(file: UploadFile) -> int:
    """
    Raise HTTP 413 if `file` exceeds the configured maximum upload size.

    Reads to the end of the underlying stream to measure its size, then
    resets the cursor to the start so downstream code can read it again.
    Returns the size in bytes on success.
    """
    settings = get_settings()
    file.file.seek(0, 2)  # seek to end
    size = file.file.tell()
    file.file.seek(0)  # reset for downstream readers

    if size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File too large ({size} bytes). "
                f"Max allowed: {settings.max_upload_size_bytes} bytes "
                f"({settings.MAX_UPLOAD_SIZE_MB} MB)."
            ),
        )
    return size
