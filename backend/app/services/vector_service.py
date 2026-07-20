"""
Vector store service (ChromaDB via the raw chromadb client).
"""

from typing import Any

from app.core.chroma_client import get_chroma_client
from app.core.config import get_settings
from app.services.embedding_service import EmbeddingService


class VectorService:
    """
    Owns all reads/writes against the single, fixed ChromaDB collection
    (Settings.CHROMA_COLLECTION_NAME, "document_rag") that holds the
    currently active document. See app.core.chroma_client for the
    underlying client.

    Uses the raw chromadb client (not a LangChain VectorStore wrapper) so
    chunk metadata -- including `hierarchy`, which Chroma can't store as a
    list -- is under our direct control.
    """

    def __init__(self) -> None:
        self._embedding_service = EmbeddingService()

    def get_or_create_collection(self) -> Any:
        """Return the "document_rag" collection, creating it if absent."""
        settings = get_settings()
        client = get_chroma_client()
        # Cosine space so `1 - distance` in similarity_search is a valid similarity score.
        return client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, chunks: list[dict[str, Any]]) -> None:
        """
        Embed-and-store chunk records (as produced by ChunkService) into
        the collection. Every field on each chunk besides "text" (filename,
        document_title, page_number, hierarchy, chunk_id, chunk_index,
        total_chunks, char_start, char_end) is stored as Chroma metadata.

        Chroma metadata values must be primitives (str/int/float/bool), so
        `hierarchy` (a list[str]) is serialized as `" > ".join(hierarchy)`
        and split back out again in similarity_search.
        """
        if not chunks:
            return

        collection = self.get_or_create_collection()
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self._embedding_service.embed_documents(texts)

        collection.add(
            ids=[str(chunk["chunk_id"]) for chunk in chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=[self._to_chroma_metadata(chunk) for chunk in chunks],
        )

    def similarity_search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Return the top_k most relevant chunks for `query` within the
        collection, each with its full metadata intact (see add_documents,
        including deserializing `hierarchy` back into a list[str]) so
        RAGService can build models.schemas.Citation objects directly from
        the result without a second lookup. Each result also carries a
        `similarity` score (cosine similarity, 1.0 = identical) for
        RAGService's debug diagnostics (see models.schemas.ChatDebugInfo).
        """
        collection = self.get_or_create_collection()
        if collection.count() == 0:
            return []

        query_embedding = self._embedding_service.embed_query(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        chunks: list[dict[str, Any]] = []
        for text, metadata, distance in zip(documents, metadatas, distances):
            chunk = self._from_chroma_metadata(metadata or {})
            chunk["text"] = text
            chunk["similarity"] = 1.0 - distance if distance is not None else None
            chunks.append(chunk)
        return chunks

    def delete_collection(self) -> None:
        """
        Delete the "document_rag" collection entirely.

        Called before indexing a new upload (a new PDF always replaces the
        previous one) and by the explicit clear/reset endpoint. A no-op if
        the collection doesn't exist yet (e.g. nothing uploaded so far).
        """
        settings = get_settings()
        client = get_chroma_client()
        try:
            client.delete_collection(name=settings.CHROMA_COLLECTION_NAME)
        except Exception:  # noqa: BLE001 - chromadb raises if the collection is absent; that's fine here
            pass

    @staticmethod
    def _to_chroma_metadata(chunk: dict[str, Any]) -> dict[str, Any]:
        return {
            "chunk_id": chunk["chunk_id"],
            "chunk_index": chunk["chunk_index"],
            "total_chunks": chunk["total_chunks"],
            "filename": chunk["filename"],
            "document_title": chunk.get("document_title") or "",
            "hierarchy": " > ".join(chunk.get("hierarchy") or []),
            "page_number": chunk["page_number"],
            "char_start": chunk["char_start"],
            "char_end": chunk["char_end"],
        }

    @staticmethod
    def _from_chroma_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        chunk = dict(metadata)
        hierarchy_str = chunk.pop("hierarchy", "") or ""
        chunk["hierarchy"] = [part for part in hierarchy_str.split(" > ") if part]
        chunk["document_title"] = chunk.get("document_title") or None
        return chunk
