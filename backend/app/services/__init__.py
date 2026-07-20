"""
Service layer.

Owns all business logic: PDF extraction, chunking, embeddings, vector
storage, RAG orchestration, LLM calls, question generation, and in-memory
active-document/chat-history state. API handlers call into these
services; services never import from app.api. Every class in this
package is currently a stub (docstrings and method signatures only) --
implementations are intentionally deferred.
"""
