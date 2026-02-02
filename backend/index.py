"""
🚀 Enterprise Knowledge Intelligence Platform - Main API
FastAPI Backend for RAG System
Render Deployment Ready
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# ✅ FIXED IMPORTS (relative imports for package structure)
from .db.supabase_client import get_supabase_client, verify_connection
from .ingestion.pdf_reader import extract_text_from_pdf
from .ingestion.chunker import chunk_text
from .ingestion.embedder import generate_embeddings, verify_embeddings_setup
from .ingestion.store import store_document_chunks
from .rag.retriever import search_documents
from .rag.generator import generate_answer, verify_gemini_setup
from .rag.guard import validate_query, validate_filename

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========================================
# FastAPI App
# ========================================

app = FastAPI(
    title="Enterprise Knowledge Intelligence API",
    description="RAG-powered document search with RBAC",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ========================================
# CORS - UPDATED with your URLs
# ========================================

ALLOWED_ORIGINS = [
    "https://mini-34rhg2u98-kavya-aicoders-projects.vercel.app",  # ✅ Your Vercel URL
    "http://localhost:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================
# Request/Response Models
# ========================================

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    role: str = Field(default="Employee")

class QueryResponse(BaseModel):
    answer: str
    sources: list
    count: int
    role: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, Any]

# ========================================
# Endpoints
# ========================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "🚀 Enterprise Knowledge Intelligence API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health"
    }

@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check for all services"""
    logger.info("🏥 Health check requested")
    
    supabase_status = verify_connection()
    embeddings_status = verify_embeddings_setup()
    gemini_status = verify_gemini_setup()
    
    all_healthy = (
        supabase_status.get("status") == "healthy" and
        embeddings_status.get("status") == "healthy" and
        gemini_status.get("status") == "healthy"
    )
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "supabase": supabase_status,
            "embeddings": embeddings_status,
            "gemini": gemini_status
        }
    }

@app.post("/api/upload", tags=["Documents"])
async def upload_document(
    file: UploadFile = File(...),
    role: str = Form(default="Employee"),
    doc_type: str = Form(default="public")
):
    """Upload and process PDF"""
    logger.info(f"📤 Upload: {file.filename} (role: {role}, type: {doc_type})")
    
    try:
        # Validate filename
        filename_validation = validate_filename(file.filename)
        if not filename_validation["valid"]:
            raise HTTPException(400, filename_validation["error"])
        
        # Read file
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(400, "Empty file")
        
        logger.info(f"📦 Size: {len(file_bytes) / 1024 / 1024:.2f} MB")
        
        # Extract text
        logger.info("📄 Extracting text...")
        text = extract_text_from_pdf(file_bytes)
        
        if len(text.strip()) < 100:
            raise HTTPException(400, "Insufficient text content")
        
        logger.info(f"✅ Extracted {len(text)} chars")
        
        # Chunk
        logger.info("✂️ Chunking...")
        chunks = chunk_text(text)
        if not chunks:
            raise HTTPException(500, "Chunking failed")
        
        logger.info(f"✅ Created {len(chunks)} chunks")
        
        # Embed
        logger.info("🧠 Generating embeddings...")
        embeddings = generate_embeddings(chunks)
        logger.info(f"✅ Generated {len(embeddings)} embeddings")
        
        # Store
        logger.info("💾 Storing...")
        metadata = {
            "filename": filename_validation["sanitized_filename"],
            "upload_date": datetime.utcnow().isoformat(),
            "uploaded_by": role
        }
        
        store_result = store_document_chunks(
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
            doc_type=doc_type
        )
        
        logger.info("🎉 Upload complete!")
        
        return {
            "status": "success",
            "filename": filename_validation["sanitized_filename"],
            "chunks_created": len(chunks),
            "text_length": len(text),
            "doc_type": doc_type,
            "storage_result": store_result
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"❌ Validation: {e}")
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")

@app.post("/api/query", response_model=QueryResponse, tags=["Search"])
async def query_documents(request: QueryRequest):
    """Search and generate answer"""
    logger.info(f"🔍 Query: '{request.query[:50]}...' (role: {request.role})")
    
    try:
        # Validate
        validation = validate_query(request.query)
        if not validation["valid"]:
            raise HTTPException(400, validation["error"])
        
        sanitized = validation["sanitized_query"]
        
        # Search
        logger.info("🔎 Searching...")
        search_result = search_documents(
            query=sanitized,
            role=request.role,
            top_k=5,
            similarity_threshold=0.7
        )
        
        # Check results
        if search_result["count"] == 0:
            return QueryResponse(
                answer="I couldn't find relevant information to answer your question.",
                sources=[],
                count=0,
                role=request.role
            )
        
        logger.info(f"✅ Found {search_result['count']} docs")
        
        # Generate answer
        logger.info("🤖 Generating answer...")
        answer = generate_answer(
            query=sanitized,
            context=search_result["context"],
            role=request.role
        )
        
        logger.info("✅ Answer generated")
        
        return QueryResponse(
            answer=answer,
            sources=search_result["sources"],
            count=search_result["count"],
            role=request.role
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Query failed: {e}")
        raise HTTPException(500, f"Query failed: {str(e)}")

# ========================================
# Startup
# ========================================

@app.on_event("startup")
async def startup_event():
    """Startup checks"""
    logger.info("🚀 Starting API...")
    logger.info("=" * 50)
    
    required_vars = ["SUPABASE_URL", "SUPABASE_KEY", "GEMINI_API_KEY"]
    missing = [v for v in required_vars if not os.getenv(v)]
    
    if missing:
        logger.warning(f"⚠️ Missing: {', '.join(missing)}")
    else:
        logger.info("✅ All env vars configured")
    
    if not (os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN")):
        logger.warning("⚠️ HF token missing")
    
    logger.info("=" * 50)
    logger.info("✅ API ready!")

# ========================================
# Run (local testing)
# ========================================

if __name__ == "__main__":
    uvicorn.run(
        "index:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
