"""
Embedding service (Google gemini-embedding-001 via LangChain).
"""

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import get_settings


class EmbeddingService:
    """
    Wraps the embedding model (Settings.EMBEDDING_MODEL_NAME) used to embed
    both document chunks (for indexing) and user queries (for retrieval).

    Truncates vectors to Settings.EMBEDDING_DIMENSION (Matryoshka
    representation learning -- gemini-embedding-001 natively returns 3072
    dims but is trained so a shorter prefix of the vector remains a valid,
    slightly-lower-fidelity embedding) to keep ChromaDB's storage/RAM
    footprint small, which matters on free-tier hosting.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._dimension = settings.EMBEDDING_DIMENSION
        self._embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.EMBEDDING_MODEL_NAME,
            google_api_key=settings.GEMINI_API_KEY,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of chunk texts for indexing. Returns one vector per input text."""
        if not texts:
            return []
        return self._embeddings.embed_documents(texts, output_dimensionality=self._dimension)

    def embed_query(self, text: str) -> list[float]:
        """Embed a single user query for similarity search."""
        return self._embeddings.embed_query(text, output_dimensionality=self._dimension)
