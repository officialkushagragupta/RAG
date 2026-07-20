"""
Text chunking service (LangChain text splitters).
"""

from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings


class ChunkService:
    """
    Splits per-page document text into overlapping chunks suitable for
    embedding, using Settings.CHUNK_SIZE / Settings.CHUNK_OVERLAP.

    Stamps each chunk with rich metadata (filename, document_title,
    page_number, hierarchy, chunk_id, chunk_index, total_chunks,
    char_start, char_end) so VectorService can store it and RAGService can
    turn retrieved chunks directly into models.schemas.Citation objects
    without a second lookup. `hierarchy` is built by walking PDFService's
    `headings` output in document order and maintaining a stack keyed by
    heading `level`, so it correctly carries over across pages (a heading
    on page 3 still applies to a chunk on page 5 unless a new heading at
    the same or shallower level appears first). No `document_id` is
    stamped -- there is only ever one document (and one Chroma collection)
    active at a time.
    """

    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None) -> None:
        settings = get_settings()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size or settings.CHUNK_SIZE,
            chunk_overlap=chunk_overlap or settings.CHUNK_OVERLAP,
        )

    def split_into_chunks(
        self, pages: list[dict[str, Any]], filename: str, document_title: str | None
    ) -> list[dict[str, Any]]:
        """
        Split page records into richly-annotated chunk records ready for embedding.

        Args:
            pages: Per-page records as returned by PDFService.extract_text
                (including each page's detected `headings`, if any).
            filename: The active document's uploaded filename, stamped
                onto every chunk for citation rendering.
            document_title: The active document's title (PDFService.get_document_title),
                or None to let citations fall back to `filename`.

        Returns:
            A list of chunk records, e.g.:
            [{
                "chunk_id": 42, "chunk_index": 42, "total_chunks": 128,
                "filename": "Employee_Handbook.pdf",
                "document_title": "Employee Handbook",
                "hierarchy": ["HR Policies", "Leave Policy", "Annual Leave"],
                "page_number": 12,
                "char_start": 10420, "char_end": 11185,
                "text": "...",
            }, ...]
        """
        heading_stack: list[tuple[int, str]] = []
        chunks: list[dict[str, Any]] = []
        chunk_index = 0

        for page in pages:
            text = page.get("text", "")
            if not text.strip():
                continue

            page_number = page["page_number"]
            pending_headings = sorted(page.get("headings", []), key=lambda h: h["char_offset"])

            search_from = 0
            for chunk_text in self._splitter.split_text(text):
                char_start = text.find(chunk_text, search_from)
                if char_start == -1:
                    char_start = text.find(chunk_text)
                if char_start == -1:
                    char_start = search_from
                char_end = char_start + len(chunk_text)
                search_from = char_start + 1

                while pending_headings and pending_headings[0]["char_offset"] <= char_start:
                    heading = pending_headings.pop(0)
                    level = heading["level"]
                    while heading_stack and heading_stack[-1][0] >= level:
                        heading_stack.pop()
                    heading_stack.append((level, heading["text"]))

                chunks.append(
                    {
                        "chunk_id": chunk_index,
                        "chunk_index": chunk_index,
                        "filename": filename,
                        "document_title": document_title,
                        "hierarchy": [heading_text for _, heading_text in heading_stack],
                        "page_number": page_number,
                        "char_start": char_start,
                        "char_end": char_end,
                        "text": chunk_text,
                    }
                )
                chunk_index += 1

        total_chunks = len(chunks)
        for chunk in chunks:
            chunk["total_chunks"] = total_chunks

        return chunks
