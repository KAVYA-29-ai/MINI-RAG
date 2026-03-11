"""
Vercel Serverless Function — entry point for FastAPI backend.
Vercel auto-detects the `app` variable (ASGI) and wraps it.
"""
import sys
import os

# Import the FastAPI app from backend.main (absolute import)
from backend.main import app
