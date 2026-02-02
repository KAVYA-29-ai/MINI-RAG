"""
RAG Retriever - Semantic search with Supabase pgvector
RBAC enforced at database level
"""
import logging
from typing import Dict, Any
from db.supabase_client import get_supabase_client
from ingestion.embedder import generate_embeddings

logger = logging.getLogger(__name__)

def search_documents(
    query: str,
    role: str = "Employee",
    top_k: int = 5,
    similarity_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Search for relevant documents using semantic similarity.
    RBAC filtering happens in SQL (match_documents function).
    
    Args:
        query: User's question
        role: User role (Admin/HR/Employee)
        top_k: Number of results (default: 5)
        similarity_threshold: Min similarity (0-1, default: 0.7)
        
    Returns:
        Dict with context, sources, and count
    """
    # Input validation
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    # Validate role
    valid_roles = ["Admin", "HR", "Employee"]
    if role not in valid_roles:
        logger.warning(f"Invalid role '{role}', defaulting to 'Employee'")
        role = "Employee"
    
    logger.info(f"🔍 Searching: '{query[:50]}...' (role: {role})")
    
    try:
        # 1. Generate query embedding
        logger.info("🧠 Generating query embedding...")
        query_embedding = generate_embeddings(query)
        
        # Validate dimension
        if len(query_embedding) != 384:
            raise ValueError(f"Invalid embedding dimension: {len(query_embedding)}")
        
        # 2. Call Supabase RPC function
        # RBAC happens in SQL - role passed to match_documents
        client = get_supabase_client()
        
        logger.info(f"📊 Calling match_documents RPC (role: {role})")
        
        results = client.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_role": role,
                "match_threshold": similarity_threshold,
                "match_count": top_k
            }
        ).execute()
        
        # 3. Check results
        if not results.data or len(results.data) == 0:
            logger.warning("⚠️ No documents found")
            return {
                "context": "",
                "sources": [],
                "count": 0
            }
        
        logger.info(f"✅ Found {len(results.data)} relevant documents")
        
        # 4. Format context and sources
        context_chunks = []
        sources = []
        
        for i, doc in enumerate(results.data):
            # Build context with source info
            context_chunks.append(
                f"[Source {i+1}: {doc.get('filename', 'Unknown')} - "
                f"Page {doc.get('page_number', '?')}]\n"
                f"{doc.get('content', '').strip()}"
            )
            
            # Track source metadata
            sources.append({
                "filename": doc.get("filename", "Unknown"),
                "page": doc.get("page_number"),
                "similarity": round(doc.get("similarity", 0), 3),
                "doc_type": doc.get("doc_type", "public")
            })
        
        # Combine context
        full_context = "\n\n".join(context_chunks)
        
        logger.info(f"📝 Context length: {len(full_context)} chars")
        
        return {
            "context": full_context,
            "sources": sources,
            "count": len(results.data)
        }
        
    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        raise Exception(f"Failed to search documents: {str(e)}")
