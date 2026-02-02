"""RAG module - Retrieval-Augmented Generation"""
from .retriever import search_documents
from .generator import generate_answer
from .prompt import build_rag_prompt, get_role_instructions
from .guard import validate_query, sanitize_input

__all__ = [
    'search_documents',
    'generate_answer', 
    'build_rag_prompt',
    'get_role_instructions',
    'validate_query',
    'sanitize_input'
]
