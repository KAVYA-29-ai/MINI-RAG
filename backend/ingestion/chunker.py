"""
Text Chunking - Semantic chunking with overlap
Production-ready for Render deployment
"""
import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# Optimal for 384-d embeddings
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 200

def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP
) -> List[str]:
    """
    Split text into overlapping chunks with sentence boundaries.
    
    Args:
        text: Full document text
        chunk_size: Max characters per chunk (default: 1000)
        overlap: Characters to overlap (default: 200)
        
    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        logger.warning("Empty text provided to chunker")
        return []
    
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    text_len = len(text)
    
    # If text is shorter than chunk_size, return as single chunk
    if text_len <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < text_len:
        # Calculate end position
        end = min(start + chunk_size, text_len)
        
        # Try to break at sentence boundary
        if end < text_len:
            # Look for sentence endings (. ! ?) within last 100 chars
            sentence_end = _find_sentence_boundary(text, max(end - 100, start), end)
            if sentence_end != -1:
                end = sentence_end
            else:
                # Fallback to word boundary
                word_end = _find_word_boundary(text, max(end - 50, start), end)
                if word_end != -1:
                    end = word_end
        
        # Extract chunk
        chunk = text[start:end].strip()
        
        if chunk and len(chunk) >= 100:  # Minimum chunk size
            chunks.append(chunk)
        
        # Move start position with overlap
        start += (chunk_size - overlap)
    
    logger.info(f"✂️ Created {len(chunks)} chunks from {text_len} characters")
    
    return chunks


def _find_sentence_boundary(text: str, start: int, end: int) -> int:
    """Find last sentence ending within range."""
    for pos in range(end - 1, start - 1, -1):
        if text[pos] in '.!?' and (pos + 1 >= len(text) or text[pos + 1].isspace()):
            return pos + 1
    return -1


def _find_word_boundary(text: str, start: int, end: int) -> int:
    """Find last word boundary (space) within range."""
    last_space = text.rfind(' ', start, end)
    if last_space != -1:
        return last_space + 1
    return -1