"""
RAG Generator - Answer generation with Google Gemini 2.5 Flash
Using NEW google-genai SDK (Feb 2026 compatible)
"""

import os
import time
import logging
from google import genai

logger = logging.getLogger(__name__)

# ========================================
# Gemini Client Setup (NEW SDK)
# ========================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in environment")

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"

MAX_CONTEXT_CHARS = 6000
MAX_RETRIES = 3
RETRY_DELAY = 2


def _build_system_prompt(role: str) -> str:
    return f"""
You are the Enterprise Knowledge Intelligence Assistant.

USER ROLE: {role}

CRITICAL RULES:
1. Answer ONLY using the provided CONTEXT
2. If answer is NOT in CONTEXT, say:
   "I don't have that information in our knowledge base."
3. Do NOT use external knowledge
4. Be concise, professional, and accurate
5. Cite sources when present
"""


def generate_answer(query: str, context: str, role: str = "Employee") -> str:
    if not query.strip():
        return "Invalid question."

    if not context.strip():
        return "I don't have any relevant information to answer that question."

    if len(context) > MAX_CONTEXT_CHARS:
        logger.warning("⚠️ Context truncated")
        context = context[:MAX_CONTEXT_CHARS]

    prompt = f"""
SYSTEM:
{_build_system_prompt(role)}

CONTEXT:
{context}

QUESTION:
{query}

Answer using ONLY the context above.
"""

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"🤖 Gemini call attempt {attempt + 1}")

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            if response and response.text:
                return response.text.strip()

            return "Unable to generate an answer at the moment."

        except Exception as e:
            logger.error(f"❌ Gemini error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return "The service is temporarily unavailable. Please try again later."


def verify_gemini_setup() -> dict:
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents="Say OK"
        )

        return {
            "status": "healthy",
            "model": MODEL_NAME,
            "response": response.text.strip() if response.text else None
        }

    except Exception as e:
        logger.error(f"❌ Gemini health check failed: {e}")
        return {
            "status": "unhealthy",
            "model": MODEL_NAME,
            "error": str(e)
        }
