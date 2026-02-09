import os
import logging
from typing import List, Union
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ✅ CORRECTED MODEL NAME
MODEL_NAME = "gemini-embedding-001"
EMBEDDING_DIM = 768  # We'll use output_dimensionality to get 768-d vectors

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

# ✅ Simple client initialization (no version needed)
client = genai.Client(api_key=GEMINI_API_KEY)


def generate_embeddings(
    texts: Union[str, List[str]]
) -> Union[List[float], List[List[float]]]:
    """
    Generate embeddings using Google Gemini embedding model.
    
    Args:
        texts: Single string or list of strings to embed
        
    Returns:
        Single embedding (list of floats) or list of embeddings
    """
    is_single = isinstance(texts, str)
    text_list = [texts] if is_single else texts
    
    if not text_list or not all(isinstance(t, str) and t.strip() for t in text_list):
        raise ValueError("Invalid input text(s)")
    
    logger.info(f"🧠 Generating {len(text_list)} Gemini embedding(s)")
    
    # ✅ Use output_dimensionality to get 768-d vectors
    response = client.models.embed_content(
        model=MODEL_NAME,
        contents=text_list,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIM
        )
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
    """
    Lightweight health check for embeddings.
    Does NOT call Gemini API to avoid quota exhaustion.
    """
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "dimension": EMBEDDING_DIM,
        "provider": "gemini",
        "note": "Live embedding call skipped in health check"
    }
