"""Persistence adapter shim. Default uses Supabase if configured, else in-memory adapter."""

from __future__ import annotations

import os
from typing import Any

from src.storage.memory_store import default_memory_adapter


def get_default_adapter() -> Any:
    """Return the default persistence adapter instance.
    
    Returns SupabaseAdapter if SUPABASE_URL and SUPABASE_KEY are configured,
    otherwise falls back to InMemoryPersistenceAdapter.

    The returned adapter implements async `get(session_id)` and
    `save(session_id, state_dict)` methods as used by `StateManager`.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    # Use Supabase if credentials are configured
    if supabase_url and supabase_key:
        try:
            from src.orchestrator.supabase_adapter import create_supabase_adapter
            
            adapter = create_supabase_adapter(supabase_url, supabase_key)
            print("[persistence] Using SupabaseAdapter (Postgres backend)")
            return adapter
            
        except ImportError:
            print("[persistence] WARNING: Supabase credentials found but package not installed.")
            print("[persistence] Run: pip install supabase")
            print("[persistence] Falling back to InMemoryPersistenceAdapter")
            
        except Exception as e:
            print(f"[persistence] WARNING: Failed to initialize SupabaseAdapter: {e}")
            print("[persistence] Falling back to InMemoryPersistenceAdapter")
    
    # Fallback to in-memory adapter
    print("[persistence] Using InMemoryPersistenceAdapter (no database persistence)")
    return default_memory_adapter
