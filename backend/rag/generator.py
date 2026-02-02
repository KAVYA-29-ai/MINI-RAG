"""
RAG Generator - Answer generation with Google Gemini
Production-ready for Render
"""
import os
import time
import logging
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold

logger = logging.getLogger(__name__)

# Configure Gemini at module level (singleton)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in environment")

genai.configure(api_key=GEMINI_API_KEY)

# Reusable model instance
MODEL = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=GenerationConfig(
        temperature=0.3,
        max_output_tokens=1024,
        top_p=0.95,
        top_k=40
    ),
    safety_settings={
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    }
)

# Constants
MAX_CONTEXT_CHARS = 6000
MAX_RETRIES = 3
RETRY_DELAY = 2

def _build_system_prompt(role: str) -> str:
    """Build role-aware system prompt."""
    return f"""You are the Enterprise Knowledge Intelligence Assistant.

USER ROLE: {role}

CRITICAL RULES:
1. Answer ONLY using the provided CONTEXT below
2. If answer is NOT in CONTEXT, say: "I don't have that information in our knowledge base."
3. Do NOT use external or general knowledge
4. Be professional, concise, and accurate
5. Always cite sources: [Source: filename, Page: X]
6. Respect role-based access - don't share info outside user's authorization"""


def generate_answer(
    query: str,
    context: str,
    role: str = "Employee"
) -> str:
    """
    Generate RAG answer using Gemini.
    
    Args:
        query: User's question
        context: Retrieved document context
        role: User role
        
    Returns:
        AI-generated answer
    """
    if not query or not query.strip():
        return "Invalid question."
    
    if not context or not context.strip():
        return "I don't have any relevant information to answer that question."
    
    # Truncate context if too long
    if len(context) > MAX_CONTEXT_CHARS:
        logger.warning(f"⚠️ Context truncated: {len(context)} → {MAX_CONTEXT_CHARS} chars")
        context = context[:MAX_CONTEXT_CHARS]
    
    system_prompt = _build_system_prompt(role)
    
    user_prompt = f"""CONTEXT:
{context}

QUESTION:
{query}

Provide a clear answer based ONLY on the CONTEXT above. Include source citations."""
    
    # Retry logic
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"🤖 Generating answer (attempt {attempt + 1}/{MAX_RETRIES})")
            
            response = MODEL.generate_content([system_prompt, user_prompt])
            
            if not response or not response.text:
                return "Unable to generate an answer at the moment."
            
            logger.info("✅ Answer generated successfully")
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"❌ Gemini error (attempt {attempt + 1}): {e}")
            
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return "The service is temporarily unavailable. Please try again later."
    
    return "Failed to generate response after multiple attempts."


def verify_gemini_setup() -> dict:
    """Health check for Gemini API."""
    try:
        response = MODEL.generate_content("Say OK")
        return {
            "status": "healthy",
            "model": "gemini-1.5-flash",
            "response": response.text.strip() if response.text else None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
