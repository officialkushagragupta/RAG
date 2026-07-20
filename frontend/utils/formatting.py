"""Presentation helpers: turn raw API payloads into display-ready strings."""

from typing import Any


def format_citation_label(citation: dict[str, Any]) -> str:
    """
    Build a breadcrumb citation label from a citation dict (see backend
    models.schemas.Citation) by joining document_title -> hierarchy ->
    page, degrading gracefully when any of those are missing.

    Example output only -- the actual text depends entirely on the
    document: "Employee Handbook -> HR Policies -> Leave Policy ->
    Annual Leave (Page 12)".
    """
    title = citation.get("document_title") or citation.get("filename") or "Document"
    parts = [title, *citation.get("hierarchy", [])]
    label = " → ".join(parts)
    if citation.get("page") is not None:
        label = f"{label} (Page {citation['page']})"
    return label
