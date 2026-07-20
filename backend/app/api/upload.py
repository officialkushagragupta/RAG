"""
Document upload endpoints.

This app has exactly one active document at a time (see README's
"Architecture Constraints"). Uploading a new PDF always replaces whatever
was previously indexed: old Chroma collection dropped, old uploaded file
removed, chat history cleared, new index built, new suggested questions
generated. File type/size validation is enforced here; the indexing
pipeline itself lives in the service layer, this handler only orchestrates.

Responses are flat (`DocumentInfo`) so the frontend can render filename,
page/chunk counts, status, and suggested questions straight from the
upload response -- no follow-up call needed.
"""

from pathlib import Path

from fastapi import APIRouter, File, UploadFile, status

from app.core.config import get_settings
from app.models.schemas import ClearResponse, DocumentInfo, DocumentStatus
from app.services.chunk_service import ChunkService
from app.services.pdf_service import PDFService
from app.services.question_service import QuestionService
from app.services.state_service import DocumentStateService, get_document_state_service
from app.services.vector_service import VectorService
from app.utils.logger import get_logger
from app.utils.validators import validate_file_extension, validate_file_size, validate_mime_type

logger = get_logger(__name__)
router = APIRouter(prefix="/document", tags=["Document"])


@router.post("", response_model=DocumentInfo, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(..., description="PDF file to index.")) -> DocumentInfo:
    """
    Replace the active document with `file`: validate it, drop whatever was
    previously indexed, save the new file, extract/chunk/embed/index it,
    and generate 5 suggested questions -- returning filename, page count,
    chunk count, status, and the suggested questions in one response.
    """
    validate_file_extension(file.filename)
    validate_mime_type(file.content_type)
    validate_file_size(file)

    settings = get_settings()
    state_service = get_document_state_service()
    vector_service = VectorService()

    _clear_active_document(state_service, vector_service)

    assert file.filename is not None  # validate_file_extension already rejects a missing filename
    filename = Path(file.filename).name  # strip any directory components from a hostile filename
    file_path = settings.upload_dir_path / filename
    file.file.seek(0)
    file_path.write_bytes(file.file.read())

    try:
        pdf_service = PDFService()
        pages = pdf_service.extract_text(file_path)
        document_title = pdf_service.get_document_title(file_path)

        chunk_service = ChunkService()
        chunks = chunk_service.split_into_chunks(pages, filename=filename, document_title=document_title)
        vector_service.add_documents(chunks)

        document_text = "\n\n".join(page["text"] for page in pages)
        suggested_questions = QuestionService().generate_recommended_questions(document_text)
    except Exception:
        logger.exception("Failed to index uploaded document '%s'", filename)
        file_path.unlink(missing_ok=True)
        vector_service.delete_collection()
        raise

    document = {
        "filename": filename,
        "file_path": str(file_path),
        "pages": len(pages),
        "chunks": len(chunks),
        "status": DocumentStatus.INDEXED.value,
        "suggested_questions": suggested_questions,
    }
    state_service.set_active_document(document)
    logger.info("Indexed '%s': %d pages, %d chunks", filename, len(pages), len(chunks))

    return DocumentInfo(
        filename=filename,
        pages=len(pages),
        chunks=len(chunks),
        status=DocumentStatus.INDEXED,
        suggested_questions=suggested_questions,
    )


@router.get("", response_model=DocumentInfo | None)
async def get_active_document() -> DocumentInfo | None:
    """Return the currently active document's info, or `null` if nothing has been uploaded yet."""
    document = get_document_state_service().get_active_document()
    if document is None:
        return None
    return DocumentInfo(
        filename=document["filename"],
        pages=document["pages"],
        chunks=document["chunks"],
        status=DocumentStatus(document["status"]),
        suggested_questions=document.get("suggested_questions", []),
    )


@router.delete("", response_model=ClearResponse)
async def clear_document() -> ClearResponse:
    """Clear the active document, its vector index, and its chat history, without uploading a new file."""
    state_service = get_document_state_service()
    had_document = state_service.get_active_document() is not None
    _clear_active_document(state_service, VectorService())
    return ClearResponse(message="Document cleared." if had_document else "No active document.", cleared=had_document)


def _clear_active_document(state_service: DocumentStateService, vector_service: VectorService) -> None:
    """Shared teardown: drop the active document's state, its vector index, and its uploaded file."""
    previous = state_service.get_active_document()
    state_service.clear()
    vector_service.delete_collection()
    if previous and previous.get("file_path"):
        Path(previous["file_path"]).unlink(missing_ok=True)
