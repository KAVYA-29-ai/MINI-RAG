"""
Embeddings via HuggingFace Hub InferenceClient
Latest API - Production-ready for Render
"""
import os
import logging
from typing import List, Union
from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

def get_hf_client() -> InferenceClient:
    """
    Get configured HuggingFace InferenceClient.
    Checks both HF_API_KEY and HF_TOKEN.
    """
    api_key = os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN")
    
    if not api_key:
        raise EnvironmentError(
            "HF_API_KEY or HF_TOKEN not found in environment. "
            "Get one at: https://huggingface.co/settings/tokens"
        )
    
    return InferenceClient(api_key=api_key)


def generate_embeddings(texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
    """
    Generate embeddings using HuggingFace Hub.
    
    Args:
        texts: Single string or list of strings
        
    Returns:
        Single embedding or list of embeddings (384-d each)
    """
    # Normalize input
    is_single = isinstance(texts, str)
    text_list = [texts] if is_single else texts
    
    if not text_list:
        raise ValueError("No text provided")
    
    # Validate
    for i, text in enumerate(text_list):
        if not isinstance(text, str):
            raise TypeError(f"Item {i} is not a string")
        if not text.strip():
            raise ValueError(f"Item {i} is empty")
    
    logger.info(f"🧠 Generating {len(text_list)} embedding(s)...")
    
    try:
        client = get_hf_client()
        
        # Single text
        if is_single:
            embedding = client.feature_extraction(
                text=text_list[0],
                model=MODEL_NAME
            )
            
            # Validate dimension
            if len(embedding) != EMBEDDING_DIM:
                raise ValueError(f"Expected {EMBEDDING_DIM}-d, got {len(embedding)}-d")
            
            logger.info(f"✅ Generated 1 embedding ({EMBEDDING_DIM}-d)")
            return embedding
        
        # Batch processing
        else:
            embeddings = []
            
            # Process one by one (HF Hub doesn't support batch feature_extraction yet)
            for i, text in enumerate(text_list):
                embedding = client.feature_extraction(
                    text=text,
                    model=MODEL_NAME
                )
                
                if len(embedding) != EMBEDDING_DIM:
                    raise ValueError(f"Embedding {i} dimension mismatch")
                
                embeddings.append(embedding)
                
                # Log progress
                if (i + 1) % 10 == 0:
                    logger.info(f"📊 Progress: {i + 1}/{len(text_list)}")
            
            logger.info(f"✅ Generated {len(embeddings)} embeddings")
            return embeddings
            
    except Exception as e:
        logger.error(f"❌ Embedding generation failed: {e}")
        
        error_msg = str(e).lower()
        
        if "unauthorized" in error_msg or "401" in error_msg:
            raise Exception("Invalid HuggingFace API key")
        elif "not found" in error_msg or "404" in error_msg:
            raise Exception(f"Model {MODEL_NAME} not found")
        elif "rate limit" in error_msg or "429" in error_msg:
            raise Exception("Rate limit exceeded. Wait and retry.")
        else:
            raise Exception(f"Failed to generate embeddings: {str(e)}")


def verify_embeddings_setup() -> dict:
    """Health check for embeddings API."""
    try:
        logger.info("🧪 Testing HuggingFace Hub...")
        test_embedding = generate_embeddings("test")
        
        return {
            "status": "healthy",
            "model": MODEL_NAME,
            "dimension": len(test_embedding),
            "api_key_configured": bool(os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN"))
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "model": MODEL_NAME,
            "api_key_configured": bool(os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN"))
        }