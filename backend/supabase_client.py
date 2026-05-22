"""
JobHunter Pro - Supabase Client Configuration
Loads keys from environment variables and initializes client.
"""

import os
import logging

logger = logging.getLogger(__name__)

# Supabase credentials. Never add fallback values here.
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Try to initialize client
supabase = None
try:
    from supabase import create_client, Client
    if SUPABASE_URL and SUPABASE_ANON_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    else:
        logger.info("Supabase client disabled. SUPABASE_URL and SUPABASE_ANON_KEY are required.")
except ImportError:
    logger.warning("Supabase Python SDK not installed. Run 'pip install supabase'")
except Exception as e:
    logger.warning(f"Could not connect to Supabase: {e}")

def get_supabase_client():
    """Get Supabase client instance, returns None if unavailable"""
    return supabase

def init_supabase_tables():
    """Returns the SQL query string list representing table schemas"""
    return []

def get_storage_bucket():
    """Get or create storage bucket for CVs and portfolios"""
    return "jobhunter-assets"
