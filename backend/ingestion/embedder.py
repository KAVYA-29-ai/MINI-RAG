"""
Embeddings Generator
Hugging Face Inference API (Router-based)
Production-safe for Render / Vercel
"""

import os
import requests
import logging
from typing import List, Union

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

HF_API_TOKEN = os.getenv("HF_API_TOKEN") or os.getenv("HF_API_KEY")

HF_EMBEDDING_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    f"{MODEL_NAME}"
)


def _get_headers() -> dict:
    if not HF_API_TOKEN:
        raise RuntimeError("HF_API_TOKEN or HF_API_KEY not set")

    return {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json",
    }


def generate_embeddings(
    texts: Union[str, List[str]]
) -> Union[List[float], List[List[float]]]:

    is_single = isinstance(texts, str)
    text_list = [texts] if is_single else texts

    if not text_list:
        raise ValueError("No text provided")

    for i, t in enumerate(text_list):
        if not isinstance(t, str) or not t.strip():
            raise ValueError(f"Invalid text at index {i}")

    logger.info(f"🧠 Generating {len(text_list)} embedding(s)")

    # 🔥 KEY FIX: explicit feature-extraction payload
    payload = {
        "inputs": {
            "sentences": text_list
        }
    }

    response = requests.post(
        HF_EMBEDDING_URL,
        headers=_get_headers(),
        json=payload,
        timeout=30,
    )

    try:
        response.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"HF embedding request failed: {response.text}") from e

    data = response.json()

    # HF returns List[List[float]]
    if is_single:
        embedding = data[0]
        if len(embedding) != EMBEDDING_DIM:
            raise ValueError(
                f"Expected {EMBEDDING_DIM}-d, got {len(embedding)}-d"
            )
        return embedding

    for i, emb in enumerate(data):
        if len(emb) != EMBEDDING_DIM:
            raise ValueError(f"Embedding {i} has dimension {len(emb)}")

    logger.info(f"✅ Generated {len(data)} embeddings")
    return data


def verify_embeddings_setup() -> dict:
    try:
        test = generate_embeddings("health check")
        return {
            "status": "healthy",
            "model": MODEL_NAME,
            "dimension": len(test),
            "api_key_configured": bool(HF_API_TOKEN),
        }
    except Exception as e:
        logger.error(f"❌ Embedding health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "model": MODEL_NAME,
            "api_key_configured": bool(HF_API_TOKEN),
        }
