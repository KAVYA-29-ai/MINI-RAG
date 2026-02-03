"""
🚀 Enterprise Knowledge Intelligence Platform - Main API
FastAPI Backend for RAG System
Render / Vercel Production Ready
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
import uvicorn

# ========================================
# ABSOLUTE IMPORTS (Render / Vercel Safe)
# ========================================

from db.supabase_client import verify_connection
from ingestion.pdf_reader import extract_text_from_pdf
from ingestion.chunker import chunk_text
from ingestion.embedder import generate_embeddings, verify_embeddings_setup
from ingestion.store import store_document_chunks
from rag.retriever import search_documents
from rag.generator import generate_answer, verify_gemini_setup
from rag.guard import validate_query, validate_filename

# ========================================
# Logging
# ========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
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
# CORS CONFIG
# ========================================

ALLOWED_ORIGINS = [
    "https://mini-rag-ebon.vercel.app",
    "https://mini-34rhg2u98-kavya-aicoders-projects.vercel.app",
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
# 🔴 CRITICAL: CORS PREFLIGHT FIX
# ========================================

@app.options("/{path:path}")
async def options_handler(path: str, request: Request):
    return Response(status_code=200)

# ========================================
# Models
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
# Routes
# ========================================

@app.get("/")
async def root():
    return {
        "message": "🚀 Enterprise Knowledge Intelligence API",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health"
    }

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    logger.info("🏥 Health check")

    supabase_status = verify_connection()
    embeddings_status = verify_embeddings_setup()

    # ⚠️ Gemini quota bachane ke liye
    gemini_status = {
        "status": "healthy",
        "model": "gemini-2.5-flash",
        "note": "Live call skipped to avoid quota exhaustion"
    }

    all_ok = (
        supabase_status["status"] == "healthy"
        and embeddings_status["status"] == "healthy"
    )

    return {
        "status": "healthy" if all_ok else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "supabase": supabase_status,
            "embeddings": embeddings_status,
            "gemini": gemini_status
        }
    }

# ========================================
# Upload PDF
# ========================================

@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    role: str = Form(default="Employee"),
    doc_type: str = Form(default="public")
):
    logger.info(f"📤 Uploading {file.filename}")

    try:
        filename_check = validate_filename(file.filename)
        if not filename_check["valid"]:
            raise HTTPException(400, filename_check["error"])

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(400, "Empty file")

        text = extract_text_from_pdf(file_bytes)
        if len(text.strip()) < 100:
            raise HTTPException(400, "Insufficient text content")

        chunks = chunk_text(text)
        embeddings = generate_embeddings(chunks)

        metadata = {
            "filename": filename_check["sanitized_filename"],
            "uploaded_by": role,
            "upload_date": datetime.utcnow().isoformat()
        }

        store_document_chunks(
            chunks=chunks,
            embeddings=embeddings,
            metadata=metadata,
            doc_type=doc_type
        )

        return {
            "status": "success",
            "filename": filename_check["sanitized_filename"],
            "chunks_created": len(chunks),
            "doc_type": doc_type
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise HTTPException(500, str(e))

# ========================================
# Query
# ========================================

@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    logger.info(f"🔍 Query: {request.query[:50]}")

    try:
        validation = validate_query(request.query)
        if not validation["valid"]:
            raise HTTPException(400, validation["error"])

        search_result = search_documents(
            query=validation["sanitized_query"],
            role=request.role,
            top_k=5,
            similarity_threshold=0.7
        )

        if search_result["count"] == 0:
            return QueryResponse(
                answer="No relevant information found.",
                sources=[],
                count=0,
                role=request.role
            )

        answer = generate_answer(
            query=validation["sanitized_query"],
            context=search_result["context"],
            role=request.role
        )

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
        raise HTTPException(500, str(e))

# ========================================
# Startup
# ========================================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 API starting")

    required = ["SUPABASE_URL", "SUPABASE_KEY", "GEMINI_API_KEY"]
    missing = [v for v in required if not os.getenv(v)]

    if missing:
        logger.warning(f"⚠️ Missing env vars: {missing}")
    else:
        logger.info("✅ All environment variables configured")

# ========================================
# Local run
# ========================================

if __name__ == "__main__":
    uvicorn.run(
        "index:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
