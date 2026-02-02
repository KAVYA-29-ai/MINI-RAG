"""
Safety Guards - Input validation and security
Protection against injection attacks
"""
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Limits
MAX_QUERY_LENGTH = 1000
MIN_QUERY_LENGTH = 3

# Blocked patterns (SQL injection, prompt injection, XSS)
BLOCKED_PATTERNS = [
    r"(?i)(drop\s+table|delete\s+from|insert\s+into)",  # SQL injection
    r"(?i)(exec|execute|script|javascript)",             # Code injection
    r"(?i)(ignore\s+previous|forget\s+instructions)",    # Prompt injection
    r"(?i)(you\s+are\s+now|pretend\s+to\s+be)",         # Role manipulation
    r"<script|<iframe|onerror=|onclick=",                # XSS
]

def sanitize_input(text: str) -> str:
    """
    Sanitize user input.
    
    Args:
        text: Raw user input
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters (except newlines/tabs)
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    
    return text.strip()


def validate_query(query: str) -> Dict[str, Any]:
    """
    Validate user query for safety.
    
    Args:
        query: User's question
        
    Returns:
        Validation result dict
    """
    # Sanitize
    sanitized = sanitize_input(query)
    
    # Check length
    if len(sanitized) < MIN_QUERY_LENGTH:
        return {
            "valid": False,
            "error": f"Query too short (min {MIN_QUERY_LENGTH} chars)",
            "sanitized_query": sanitized
        }
    
    if len(sanitized) > MAX_QUERY_LENGTH:
        return {
            "valid": False,
            "error": f"Query too long (max {MAX_QUERY_LENGTH} chars)",
            "sanitized_query": sanitized[:MAX_QUERY_LENGTH]
        }
    
    # Check blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, sanitized):
            logger.warning(f"🚨 Blocked query: {sanitized[:100]}")
            return {
                "valid": False,
                "error": "Query contains prohibited content",
                "sanitized_query": sanitized
            }
    
    return {
        "valid": True,
        "error": None,
        "sanitized_query": sanitized
    }


def validate_filename(filename: str) -> Dict[str, Any]:
    """
    Validate uploaded filename.
    
    Args:
        filename: Original filename
        
    Returns:
        Validation result
    """
    sanitized = sanitize_input(filename)
    
    # Check for path traversal
    if '..' in sanitized or '/' in sanitized or '\\' in sanitized:
        return {
            "valid": False,
            "error": "Invalid filename characters",
            "sanitized_filename": sanitized.replace('..', '').replace('/', '').replace('\\', '')
        }
    
    # Check extension
    if not sanitized.lower().endswith('.pdf'):
        return {
            "valid": False,
            "error": "Only PDF files allowed",
            "sanitized_filename": sanitized
        }
    
    return {
        "valid": True,
        "error": None,
        "sanitized_filename": sanitized
    }
