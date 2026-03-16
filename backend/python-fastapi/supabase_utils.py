import os
from functools import lru_cache
from typing import Tuple

import httpx
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

# Historical default project config kept as fallback.
DEFAULT_SUPABASE_URL = "https://dcbpysgftwbjasaucbbr.supabase.co"
DEFAULT_SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4dXJxdWR4cGx4aGlnbmxzaGh5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyNDAxMjEsImV4cCI6MjA4MDgxNjEyMX0."
    "afuHUdv5pDwKrMbEon5Tcy2W2EHTR9ZMlka8jiECGDY"
)


def get_supabase_config(prefer_service_role: bool = False) -> Tuple[str, str]:
    """Read Supabase URL/key from env with safe fallback."""
    supabase_url = (os.getenv("SUPABASE_URL") or DEFAULT_SUPABASE_URL).strip()

    if prefer_service_role:
        supabase_key = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_KEY")
            or DEFAULT_SUPABASE_KEY
        )
    else:
        supabase_key = (
            os.getenv("SUPABASE_KEY")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or DEFAULT_SUPABASE_KEY
        )
    supabase_key = supabase_key.strip()

    if not supabase_url:
        raise ValueError("SUPABASE_URL is empty")
    if not supabase_key:
        raise ValueError("SUPABASE key is empty")
    return supabase_url, supabase_key


def _build_http_client() -> httpx.Client:
    # Disable `trust_env` so hidden proxy envs do not break Supabase TLS.
    return httpx.Client(
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
        http2=False,
        trust_env=False,
    )


@lru_cache(maxsize=2)
def _create_cached_client(prefer_service_role: bool) -> Client:
    supabase_url, supabase_key = get_supabase_config(prefer_service_role)
    options = SyncClientOptions(httpx_client=_build_http_client())
    return create_client(supabase_url, supabase_key, options=options)


def get_supabase_client(prefer_service_role: bool = False) -> Client:
    return _create_cached_client(bool(prefer_service_role))


def reset_supabase_clients() -> None:
    _create_cached_client.cache_clear()
