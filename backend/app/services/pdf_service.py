"""
PDF extraction service (PyMuPDF-based).
"""

from collections import Counter
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

# A line's max font size must be at least this many times the document's body-
# text font size to be treated as a heading. Tuned to skip minor emphasis
# (bold body text) while catching genuine section headings.
_HEADING_SIZE_RATIO = 1.15
# A "heading" longer than this is almost certainly a body paragraph that
# happens to use a larger font (e.g. a pull quote), not a real heading.
_MAX_HEADING_CHARS = 120


class PDFService:
    """
    Extracts raw text, page-level metadata, and heading structure from
    uploaded PDF files using PyMuPDF (fitz). Its output feeds ChunkService,
    which uses the heading structure to derive each chunk's `hierarchy`
    breadcrumb for richer citations (see models.schemas.Citation).
    """

    def extract_text(self, file_path: Path) -> list[dict[str, Any]]:
        """
        Extract text per page from a PDF file, including any detected
        headings (with heading level) so ChunkService can build each
        chunk's `hierarchy` breadcrumb.

        The document's body-text size is estimated once, globally (the
        mode/most-common font size across every line in the document), not
        per page -- a per-page estimate is unreliable on pages with only a
        handful of lines (e.g. a title page), where the heading itself can
        skew the estimate.

        Args:
            file_path: Path to the PDF file on disk.

        Returns:
            A list of per-page records, e.g. [{"page_number": 1, "text":
            "...", "headings": [{"text": "Leave Policy", "level": 2,
            "char_offset": 120}]}]. `level` is a relative heading depth
            (1 = largest/outermost font in the document). `headings` is
            empty if no heading structure is detected; `hierarchy` on the
            resulting chunks should be treated as best-effort, not
            guaranteed.
        """
        document = fitz.open(str(file_path))
        try:
            page_lines = [self._extract_lines(document[i]) for i in range(document.page_count)]
            body_size = self._estimate_body_size(page_lines)
            heading_threshold = body_size * _HEADING_SIZE_RATIO if body_size > 0 else float("inf")

            pages: list[dict[str, Any]] = []
            for page_index, lines in enumerate(page_lines):
                text, headings = self._build_page_text_and_headings(lines, body_size, heading_threshold)
                pages.append({"page_number": page_index + 1, "text": text, "headings": headings})
            return pages
        finally:
            document.close()

    def get_page_count(self, file_path: Path) -> int:
        """Return the number of pages in the given PDF file."""
        document = fitz.open(str(file_path))
        try:
            return document.page_count
        finally:
            document.close()

    def get_document_title(self, file_path: Path) -> str | None:
        """
        Return a human-readable document title for citations
        (models.schemas.Citation.document_title), preferring the PDF's
        embedded metadata title and falling back to None if absent (the
        caller should fall back to the filename).
        """
        document = fitz.open(str(file_path))
        try:
            title = (document.metadata or {}).get("title")
            title = (title or "").strip()
            return title or None
        finally:
            document.close()

    @staticmethod
    def _extract_lines(page: "fitz.Page") -> list[tuple[str, float]]:
        """Return (line_text, max_font_size) for every non-empty line on `page`."""
        raw = page.get_text("dict")
        lines: list[tuple[str, float]] = []
        for block in raw.get("blocks", []):
            for line in block.get("lines", []):
                line_text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
                if not line_text:
                    continue
                sizes = [span.get("size", 0.0) for span in line.get("spans", [])]
                lines.append((line_text, max(sizes) if sizes else 0.0))
        return lines

    @staticmethod
    def _estimate_body_size(page_lines: list[list[tuple[str, float]]]) -> float:
        """
        Estimate the document's body-text font size as the mode (most
        common size, rounded to the nearest 0.5pt) across every line in
        the document. Body text is by far the most-repeated size in a
        typical document, while headings are rare outliers, so the mode is
        a more robust estimator here than the median or mean.
        """
        rounded_sizes = [round(size * 2) / 2 for lines in page_lines for _, size in lines if size > 0]
        if not rounded_sizes:
            return 0.0
        return Counter(rounded_sizes).most_common(1)[0][0]

    @staticmethod
    def _build_page_text_and_headings(
        lines: list[tuple[str, float]], body_size: float, heading_threshold: float
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Build a page's plain text and its heading list from the same pass
        over `lines`, so each heading's `char_offset` is guaranteed to be a
        valid index into the returned text.
        """
        if not lines:
            return "", []

        text_parts: list[str] = []
        headings: list[dict[str, Any]] = []
        offset = 0
        for line_text, size in lines:
            if body_size > 0 and size >= heading_threshold and len(line_text) <= _MAX_HEADING_CHARS:
                ratio = size / body_size
                level = 1 if ratio >= 1.6 else 2 if ratio >= 1.35 else 3
                headings.append({"text": line_text, "level": level, "char_offset": offset})
            text_parts.append(line_text)
            offset += len(line_text) + 1  # +1 accounts for the "\n" joiner below

        return "\n".join(text_parts), headings
