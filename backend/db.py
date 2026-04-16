import sys
from supabase import create_client, Client
from backend.config import settings

SCHEMA = "vikaa_exam_assist"


def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


try:
    db = get_supabase()
except Exception as e:
    print(f"[FATAL] Supabase connection failed: {e}", file=sys.stderr)
    print("[FATAL] Check SUPABASE_URL and SUPABASE_KEY in your .env file", file=sys.stderr)
    raise


def tbl(name: str):
    """Return a query builder scoped to the vikaa_exam_assist schema."""
    return db.schema(SCHEMA).table(name)


# Shared in-memory store for the test-bypass session
bypass_session: dict = {}
