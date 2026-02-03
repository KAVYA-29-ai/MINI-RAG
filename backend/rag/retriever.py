"""
RAG Retriever - Semantic search with Supabase pgvector
Embedding Model: Gemini (text-embedding-004) – 768 dimensions
RBAC: Enforced at DATABASE (match_documents RPC)
Status: PRODUCTION READY
"""

import logging
from typing import Dict, Any, List

from db.supabase_client import get_supabase_client
from ingestion.embedder import generate_embeddings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768  # Gemini standard


def _adaptive_threshold(query: str, base: float) -> float:
    """
    Lower threshold for short / vague queries like:
    'working hour', 'leave policy', etc.
    """
    word_count = len(query.split())

    if word_count <= 3:
        return max(base - 0.15, 0.4)

    if word_count <= 6:
        return max(base - 0.05, 0.5)

    return base


def search_documents(
    query: str,
    role: str = "Employee",
    top_k: int = 5,
    similarity_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Perform semantic search using Gemini embeddings + Supabase pgvector RPC
    """

    # --------------------
    # 1️⃣ Validate input
    # --------------------
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    valid_roles = {"Admin", "HR", "Employee"}
    if role not in valid_roles:
        logger.warning(f"Invalid role '{role}', defaulting to Employee")
        role = "Employee"

    threshold = _adaptive_threshold(query, similarity_threshold)

    logger.info(
        f"🔍 Query='{query[:60]}' | role={role} | top_k={top_k} | threshold={threshold}"
    )

    try:
        # --------------------
        # 2️⃣ Generate embedding
        # --------------------
        query_embedding: List[float] = generate_embeddings(query)

        if len(query_embedding) != EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dimension mismatch: {len(query_embedding)} != {EMBEDDING_DIM}"
            )

        # --------------------
        # 3️⃣ Call Supabase RPC
        # --------------------
        client = get_supabase_client()

        response = client.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_role": role,
                "match_threshold": threshold,
                "match_count": top_k
            }
        ).execute()

        rows = response.data or []

        if not rows:
            logger.info("⚠️ No relevant documents found")
            return {
                "context": "",
                "sources": [],
                "count": 0
            }

        # --------------------
        # 4️⃣ Build context + sources
        # --------------------
        context_chunks = []
        sources = []

        for idx, row in enumerate(rows):
            context_chunks.append(
                f"[Source {idx + 1}: {row['filename']} | Page {row['page_number']}]\n"
                f"{row['content'].strip()}"
            )

            sources.append({
                "filename": row["filename"],
                "page": row["page_number"],
                "similarity": round(row["similarity"], 3),
                "doc_type": row["doc_type"]
            })

        full_context = "\n\n".join(context_chunks)

        logger.info(
            f"✅ Retrieved {len(rows)} chunks | Context length={len(full_context)} chars"
        )

        return {
            "context": full_context,
            "sources": sources,
            "count": len(rows)
        }

    except Exception as e:
        logger.exception("❌ Retriever failure")
        raise RuntimeError(f"Failed to search documents: {str(e)}")
