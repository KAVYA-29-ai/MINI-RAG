"""
Document Storage - Store chunks with embeddings in Supabase
Production-ready for Render
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
EMBEDDING_DIM = 768   # ✅ Gemini embedding dimension

def store_document_chunks(
    chunks: List[str],
    embeddings: List[List[float]],
    metadata: Dict[str, Any],
    doc_type: str = "public"
) -> Dict[str, Any]:

    # Basic validation
    if not chunks:
        raise ValueError("No chunks provided")

    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) mismatch"
        )

    # Validate doc_type
    valid_types = ["public", "hr", "admin"]
    if doc_type not in valid_types:
        logger.warning(f"Invalid doc_type '{doc_type}', defaulting to 'public'")
        doc_type = "public"

    # 🔥 FIX: Validate Gemini embedding dimensions (768-d)
    for i, emb in enumerate(embeddings):
        if not isinstance(emb, list) or len(emb) != EMBEDDING_DIM:
            raise ValueError(
                f"Embedding {i} has invalid dimension: "
                f"{len(emb) if isinstance(emb, list) else 'invalid'}"
            )

    logger.info(f"💾 Storing {len(chunks)} chunks (type: {doc_type})")

    try:
        client = get_supabase_client()

        filename = metadata.get("filename", "unknown.pdf")
        upload_date = metadata.get("upload_date") or datetime.utcnow().isoformat()

        records = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            records.append({
                "content": chunk.strip(),
                "embedding": embedding,
                "filename": filename,
                "page_number": metadata.get("page_number", i + 1),
                "chunk_index": i,
                "doc_type": doc_type,
                "upload_date": upload_date,
                "uploaded_by": metadata.get("uploaded_by", "system"),
                "source": "upload",
            })

        inserted_count = 0
        failed_count = 0

        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            try:
                client.table("documents").insert(batch).execute()
                inserted_count += len(batch)
                logger.info(f"✅ Batch {i // BATCH_SIZE + 1}: {len(batch)} records inserted")
            except Exception as e:
                logger.error(f"❌ Batch {i // BATCH_SIZE + 1} failed: {e}")
                failed_count += len(batch)

        logger.info(
            f"🎉 Storage complete: {inserted_count} inserted, {failed_count} failed"
        )

        return {
            "status": "success" if failed_count == 0 else "partial",
            "chunks_stored": inserted_count,
            "chunks_failed": failed_count,
            "filename": filename,
            "doc_type": doc_type,
        }

    except Exception as e:
        logger.error(f"❌ Storage failed: {e}")
        raise RuntimeError(f"Database insertion failed: {str(e)}")
