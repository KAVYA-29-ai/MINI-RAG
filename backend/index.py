"""
🚀 Enterprise Knowledge Intelligence Platform - Main API
FastAPI Backend for RAG System
Render Free Tier Deployment Ready
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import our modules
from db.supabase_client import get_supabase_client, verify_connection
from ingestion.pdf_reader import extract_text_from_pdf
from ingestion.chunker import chunk_text
from ingestion.embedder import generate_embeddings, verify_embeddings_setup
from ingestion.store import store_document_chunks
from rag.retriever import search_documents
from rag.generator import generate_answer, verify_gemini_setup
from rag.guard import validate_query, validate_filename

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========================================
# FastAPI App Initialization
# ========================================

app = FastAPI(
    title="Enterprise Knowledge Intelligence API",
    description="RAG-powered document search with RBAC",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ========================================
# CORS Configuration - Allow Vercel Frontend
# ========================================

ALLOWED_ORIGINS = [
    "https://mini-rag-ebon.vercel.app",  # Your deployed frontend
    "http://localhost:3000",              # Local development
    "http://localhost:5500",              # Live Server
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
# Pydantic Models
# ========================================

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000, description="User's question")
    role: str = Field(default="Employee", description="User role: Employee/HR/Admin")

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
# API Endpoints
# ========================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API info"""
    return {
        "message": "🚀 Enterprise Knowledge Intelligence API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health"
    }

@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Complete health check for all services
    """
    logger.info("🏥 Health check requested")
    
    # Check Supabase
    supabase_status = verify_connection()
    
    # Check HuggingFace Embeddings
    embeddings_status = verify_embeddings_setup()
    
    # Check Gemini
    gemini_status = verify_gemini_setup()
    
    # Overall status
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
    """
    Upload and process PDF document
    
    - Extracts text from PDF
    - Chunks the text
    - Generates embeddings
    - Stores in Supabase with RBAC
    """
    logger.info(f"📤 Upload request: {file.filename} (role: {role}, type: {doc_type})")
    
    try:
        # 1. Validate filename
        filename_validation = validate_filename(file.filename)
        if not filename_validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=filename_validation["error"]
            )
        
        # 2. Read file bytes
        file_bytes = await file.read()
        
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file provided"
            )
        
        logger.info(f"📦 File size: {len(file_bytes) / 1024 / 1024:.2f} MB")
        
        # 3. Extract text from PDF
        logger.info("📄 Extracting text from PDF...")
        text = extract_text_from_pdf(file_bytes)
        
        if not text or len(text.strip()) < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF has insufficient text content (may be scanned/image-based)"
            )
        
        logger.info(f"✅ Extracted {len(text)} characters")
        
        # 4. Chunk text
        logger.info("✂️ Chunking text...")
        chunks = chunk_text(text)
        
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create text chunks"
            )
        
        logger.info(f"✅ Created {len(chunks)} chunks")
        
        # 5. Generate embeddings
        logger.info("🧠 Generating embeddings...")
        embeddings = generate_embeddings(chunks)
        
        logger.info(f"✅ Generated {len(embeddings)} embeddings")
        
        # 6. Store in Supabase
        logger.info("💾 Storing in database...")
        metadata = {
            "filename": filename_validation["sanitized_filename"],
            "upload_date": datetime.utcnow().isoformat(),
            "uploaded_by": role,
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
        logger.error(f"❌ Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload processing failed: {str(e)}"
        )

@app.post("/api/query", response_model=QueryResponse, tags=["Search"])
async def query_documents(request: QueryRequest):
    """
    Search documents and generate AI answer
    
    - Validates query
    - Searches with semantic similarity
    - Enforces RBAC
    - Generates contextual answer
    """
    logger.info(f"🔍 Query: '{request.query[:50]}...' (role: {request.role})")
    
    try:
        # 1. Validate query
        validation = validate_query(request.query)
        if not validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=validation["error"]
            )
        
        sanitized_query = validation["sanitized_query"]
        
        # 2. Search documents (with RBAC)
        logger.info("🔎 Searching documents...")
        search_result = search_documents(
            query=sanitized_query,
            role=request.role,
            top_k=5,
            similarity_threshold=0.7
        )
        
        # 3. Check if we found anything
        if search_result["count"] == 0:
            return QueryResponse(
                answer="I couldn't find any relevant information in the knowledge base to answer your question. Please try rephrasing or contact your administrator.",
                sources=[],
                count=0,
                role=request.role
            )
        
        logger.info(f"✅ Found {search_result['count']} relevant documents")
        
        # 4. Generate answer
        logger.info("🤖 Generating AI answer...")
        answer = generate_answer(
            query=sanitized_query,
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )

# ========================================
# Error Handlers
# ========================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Endpoint not found",
        "path": str(request.url),
        "message": "Check /docs for available endpoints"
    }

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal error: {exc}")
    return {
        "error": "Internal server error",
        "message": "Something went wrong. Please try again later."
    }

# ========================================
# Startup Event
# ========================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("🚀 Starting Enterprise Knowledge Intelligence API...")
    logger.info("=" * 50)
    
    # Check environment variables
    required_vars = ["SUPABASE_URL", "SUPABASE_KEY", "GEMINI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
    else:
        logger.info("✅ All environment variables configured")
    
    # Check HF Token
    if not (os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN")):
        logger.warning("⚠️ HuggingFace token not found")
    
    logger.info("=" * 50)
    logger.info("✅ API is ready!")

# ========================================
# Run Server (for local testing)
# ========================================

if __name__ == "__main__":
    # For local development
    uvicorn.run(
        "index:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
