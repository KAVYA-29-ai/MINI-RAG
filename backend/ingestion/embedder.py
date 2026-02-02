"""
Embeddings via HuggingFace InferenceClient
CORRECT API: Using provider='hf-inference' with feature_extraction
"""
import os
import logging
from typing import List, Union
from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

def get_hf_client() -> InferenceClient:
    """Get HuggingFace InferenceClient."""
    api_key = os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN")
    
    if not api_key:
        raise EnvironmentError(
            "HF_API_KEY or HF_TOKEN not found. "
            "Get one at: https://huggingface.co/settings/tokens"
        )
    
    # ✅ CORRECT: Use hf-inference provider
    return InferenceClient(
        provider="hf-inference",
        api_key=api_key
    )


def generate_embeddings(texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
    """
    Generate embeddings using HuggingFace InferenceClient.
    
    Args:
        texts: Single string or list of strings
        
    Returns:
        Single embedding or list of embeddings (384-d)
    """
    is_single = isinstance(texts, str)
    text_list = [texts] if is_single else texts
    
    if not text_list:
        raise ValueError("No text provided")
    
    for i, text in enumerate(text_list):
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Invalid text at index {i}")
    
    logger.info(f"🧠 Generating {len(text_list)} embedding(s)...")
    
    try:
        client = get_hf_client()
        
        # Single text
        if is_single:
            # ✅ Use feature_extraction method
            result = client.feature_extraction(
                text_list[0],
                model=MODEL_NAME
            )
            
            # Handle response format
            # HF returns different formats: [[emb]] or [emb]
            if isinstance(result, list):
                if len(result) > 0 and isinstance(result[0], list):
                    # Nested: [[emb]] -> [emb]
                    embedding = result[0]
                else:
                    # Flat: [emb]
                    embedding = result
            else:
                raise ValueError(f"Unexpected response type: {type(result)}")
            
            # Validate dimension
            if len(embedding) != EMBEDDING_DIM:
                raise ValueError(f"Expected {EMBEDDING_DIM}-d, got {len(embedding)}-d")
            
            logger.info(f"✅ Generated 1 embedding ({EMBEDDING_DIM}-d)")
            return embedding
        
        # Batch processing
        else:
            embeddings = []
            
            for i, text in enumerate(text_list):
                result = client.feature_extraction(
                    text,
                    model=MODEL_NAME
                )
                
                # Handle response format
                if isinstance(result, list):
                    if len(result) > 0 and isinstance(result[0], list):
                        embedding = result[0]
                    else:
                        embedding = result
                else:
                    raise ValueError(f"Unexpected response for item {i}")
                
                if len(embedding) != EMBEDDING_DIM:
                    raise ValueError(f"Embedding {i} has dimension {len(embedding)}")
                
                embeddings.append(embedding)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"📊 Progress: {i + 1}/{len(text_list)}")
            
            logger.info(f"✅ Generated {len(embeddings)} embeddings")
            return embeddings
            
    except Exception as e:
        logger.error(f"❌ Embedding failed: {e}")
        
        error_msg = str(e).lower()
        
        if "410" in error_msg or "gone" in error_msg:
            raise Exception(
                "HuggingFace API endpoint deprecated. "
                "Update to use InferenceClient with provider='hf-inference'"
            )
        elif "401" in error_msg or "unauthorized" in error_msg:
            raise Exception("Invalid HuggingFace API key")
        elif "404" in error_msg:
            raise Exception(f"Model {MODEL_NAME} not found")
        elif "429" in error_msg:
            raise Exception("Rate limit exceeded")
        else:
            raise Exception(f"Failed to generate embeddings: {str(e)}")


def verify_embeddings_setup() -> dict:
    """Health check for embeddings."""
    try:
        logger.info("🧪 Testing HuggingFace InferenceClient...")
        test_embedding = generate_embeddings("test")
        
        return {
            "status": "healthy",
            "model": MODEL_NAME,
            "dimension": len(test_embedding),
            "api_key_configured": bool(os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN"))
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "model": MODEL_NAME,
            "api_key_configured": bool(os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN"))
        }
