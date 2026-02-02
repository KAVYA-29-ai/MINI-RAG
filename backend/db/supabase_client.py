"""
Supabase Client - Database Connection
Production-ready for Render deployment
"""
import os
import logging
from functools import lru_cache
from supabase import create_client, Client

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Get cached Supabase client (singleton pattern).
    Environment variables required:
    - SUPABASE_URL
    - SUPABASE_KEY
    
    Returns:
        Configured Supabase client
        
    Raises:
        EnvironmentError: If credentials missing
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_KEY must be set in environment variables. "
            "Get them from: https://app.supabase.com/project/_/settings/api"
        )
    
    logger.info(f"🔗 Connecting to Supabase: {url[:30]}...")
    
    try:
        client = create_client(url, key)
        logger.info("✅ Supabase client created successfully")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to create Supabase client: {e}")
        raise


def verify_connection() -> dict:
    """
    Health check for Supabase connection.
    
    Returns:
        Status dict with connection info
    """
    try:
        client = get_supabase_client()
        
        # Test connection by querying documents table
        result = client.table("documents").select("id").limit(1).execute()
        
        return {
            "status": "healthy",
            "connected": True,
            "url_configured": bool(os.getenv("SUPABASE_URL")),
            "key_configured": bool(os.getenv("SUPABASE_KEY")),
            "table_accessible": True
        }
    except Exception as e:
        logger.error(f"❌ Supabase connection check failed: {e}")
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
            "url_configured": bool(os.getenv("SUPABASE_URL")),
            "key_configured": bool(os.getenv("SUPABASE_KEY"))
        }