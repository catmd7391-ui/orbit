# supabase_client.py
"""
Supabase connection for Orbit.
"""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError(
        "Supabase credentials missing. Check your .env file for "
        "SUPABASE_URL and SUPABASE_SERVICE_KEY."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_supabase() -> Client:
    return supabase


def health_check():
    try:
        result = supabase.table("audit_log").select("*").limit(1).execute()
        return {"ok": True, "message": "Connected to Supabase", "data": result.data}
    except Exception as e:
        return {"ok": False, "error": str(e)}