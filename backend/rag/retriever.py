"""
RAG Retriever - Semantic search with Supabase pgvector
Gemini embeddings (768-d)
RBAC enforced at database level
"""

import logging
from typing import Dict, Any

from db.supabase_client import get_supabase_client
from ingestion.embedder import generate_embeddings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768  # ✅ GEMINI STANDARD


def search_documents(
    query: str,
    role: str = "Employee",
    top_k: int = 5,
    similarity_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Semantic search using Gemini embeddings + Supabase RPC
    """

    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    valid_roles = ["Admin", "HR", "Employee"]
    if role not in valid_roles:
        logger.warning(f"Invalid role '{role}', defaulting to Employee")
        role = "Employee"

    logger.info(f"🔍 Searching query='{query[:50]}...' role={role}")

    try:
        # 1️⃣ Generate query embedding (Gemini)
        query_embedding = generate_embeddings(query)

        if len(query_embedding) != EMBEDDING_DIM:
            raise ValueError(
                f"Invalid embedding dimension: {len(query_embedding)}"
            )

        # 2️⃣ Call Supabase RPC (RBAC handled in SQL)
        client = get_supabase_client()

        response = client.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_role": role,
                "match_threshold": similarity_threshold,
                "match_count": top_k
            }
        ).execute()

        rows = response.data or []

        if not rows:
            logger.info("⚠️ No matching documents found")
            return {
                "context": "",
                "sources": [],
                "count": 0
            }

        # 3️⃣ Build context + sources
        context_chunks = []
        sources = []

        for idx, row in enumerate(rows):
            context_chunks.append(row["content"])

            sources.append({
                "filename": row["filename"],
                "page": row["page_number"],
                "similarity": round(row["similarity"], 3),
                "doc_type": row["doc_type"]
            })

        return {
            "context": "\n\n".join(context_chunks),
            "sources": sources,
            "count": len(rows)
        }

    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        raise Exception(f"Failed to search documents: {str(e)}")
