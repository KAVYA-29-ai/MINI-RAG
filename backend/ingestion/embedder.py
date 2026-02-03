"""
Embeddings via Google Gemini
Model: text-embedding-004 (768-d)
STABLE & PRODUCTION READY
"""

import os
import logging
from typing import List, Union
from google import genai

logger = logging.getLogger(__name__)

MODEL_NAME = "text-embedding-004"
EMBEDDING_DIM = 768

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_embeddings(
    texts: Union[str, List[str]]
) -> Union[List[float], List[List[float]]]:

    is_single = isinstance(texts, str)
    text_list = [texts] if is_single else texts

    if not text_list or not all(isinstance(t, str) and t.strip() for t in text_list):
        raise ValueError("Invalid input text(s)")

    logger.info(f"🧠 Generating {len(text_list)} Gemini embedding(s)")

    response = client.models.embed_content(
        model=MODEL_NAME,
        contents=text_list
    )

    if not response.embeddings:
        raise RuntimeError("No embeddings returned from Gemini")

    embeddings = [e.values for e in response.embeddings]

    for i, emb in enumerate(embeddings):
        if len(emb) != EMBEDDING_DIM:
            raise ValueError(
                f"Embedding {i} dimension mismatch: {len(emb)} != {EMBEDDING_DIM}"
            )

    return embeddings[0] if is_single else embeddings


def verify_embeddings_setup() -> dict:
    try:
        emb = generate_embeddings("health check")
        return {
            "status": "healthy",
            "model": MODEL_NAME,
            "dimension": len(emb),
            "provider": "gemini"
        }
    except Exception as e:
        logger.error(f"❌ Gemini embedding health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "model": MODEL_NAME,
            "provider": "gemini"
        }
