"""Supabase persistence adapter for AgenticMentor orchestrator.

This adapter implements the same interface as InMemoryPersistenceAdapter but
persists to Supabase PostgreSQL using the normalized schema:
- projects table (core + JSONB columns)
- conversation_messages table (1:N)
- mockups table (1:N)
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from src.state.project_state import ProjectState


class SupabaseAdapter:
    """Supabase-backed persistence adapter with async methods for StateManager.
    
    Implements the same interface as InMemoryPersistenceAdapter:
    - get(session_id) → dict | None
    - save(session_id, state_dict) → None
    - delete(session_id) → None
    - list_sessions() → list[str]
    - get_last_messages(session_id, n) → list[dict]
    - load_state(session_id) → ProjectState | None
    - save_project_state(session_id, state) → None
    """

    def __init__(self, supabase_url: str | None = None, supabase_key: str | None = None):
        """Initialize Supabase client.
        
        Args:
            supabase_url: Supabase project URL (defaults to SUPABASE_URL env var)
            supabase_key: Supabase anon/service key (defaults to SUPABASE_KEY env var)
        """
        try:
            from supabase import create_client, Client
        except ImportError as e:
            raise ImportError(
                "supabase package not installed. Run: pip install supabase"
            ) from e
        
        self.url = supabase_url or os.getenv("SUPABASE_URL")
        self.key = supabase_key or os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment or passed to constructor. "
                "Check your .env file."
            )
        
        self.client: Client = create_client(self.url, self.key)

    # ========================================================================
    # Core Interface Methods
    # ========================================================================

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load complete project state as dict (or None if not found).
        
        Joins projects + conversation_messages + mockups tables and reconstructs
        the state_dict format expected by StateManager.
        """
        try:
            # Get project data
            project_response = self.client.table("projects").select("*").eq("session_id", session_id).execute()
            
            if not project_response.data:
                return None
            
            project = project_response.data[0]
            
            # Get conversation messages
            messages_response = (
                self.client.table("conversation_messages")
                .select("role, content, created_at, metadata")
                .eq("session_id", session_id)
                .order("created_at")
                .execute()
            )
            
            # Get mockups
            mockups_response = (
                self.client.table("mockups")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at")
                .execute()
            )
            
            # Reconstruct state_dict in the format ProjectState expects
            state_dict = {
                "session_id": project["session_id"],
                "project_name": project.get("project_name"),
                "created_at": project["created_at"],
                "updated_at": project["updated_at"],
                "current_phase": project["current_phase"],
                "agent_selection_mode": project["agent_selection_mode"],
                "selected_agent_id": project.get("selected_agent_id"),
                "agent_interactions": project["agent_interactions"],
                "requirements": project["requirements"],
                "decisions": project.get("decisions") or [],
                "assumptions": project.get("assumptions") or [],
                "architecture": project["architecture"],
                "roadmap": project["roadmap"],
                "export_artifacts": project["export_artifacts"],
                "conversation_history": [
                    {
                        "role": msg["role"],
                        "content": msg["content"],
                        "timestamp": msg["created_at"],
                    }
                    for msg in messages_response.data
                ],
                "mockups": [
                    {
                        "screen_name": m["screen_name"],
                        "screen_id": m["screen_id"],
                        "wireframe_spec": m["wireframe_spec"],
                        "excalidraw_scene": m.get("excalidraw_scene"),
                        "screenshot_path": m.get("screenshot_path"),
                        "user_flow": m.get("user_flow"),
                        "interactions": m.get("interactions") or [],
                        "template_used": m["template_used"],
                        "version": m.get("version", "1.0"),
                    }
                    for m in mockups_response.data
                ],
            }
            
            return state_dict
            
        except Exception as e:
            print(f"[SupabaseAdapter] Error loading session {session_id}: {e}")
            return None

    async def save(self, session_id: str, state_dict: Dict[str, Any]) -> None:
        """Save complete project state from dict.
        
        Upserts to all 3 tables:
        1. projects table (main record with JSONB columns)
        2. conversation_messages table (sync all messages)
        3. mockups table (upsert by screen_id)
        """
        try:
            # 1. Upsert main project record
            project_data = {
                "session_id": session_id,
                "project_name": state_dict.get("project_name"),
                "current_phase": state_dict.get("current_phase", "initialization"),
                "agent_selection_mode": state_dict.get("agent_selection_mode", "auto"),
                "selected_agent_id": state_dict.get("selected_agent_id"),
                "agent_interactions": state_dict.get("agent_interactions", {}),
                "requirements": state_dict.get("requirements", {}),
                "decisions": state_dict.get("decisions", []),
                "assumptions": state_dict.get("assumptions", []),
                "architecture": state_dict.get("architecture", {}),
                "roadmap": state_dict.get("roadmap", {}),
                "export_artifacts": state_dict.get("export_artifacts", {}),
            }
            
            self.client.table("projects").upsert(project_data).execute()
            
            # 2. Sync conversation_messages (delete + bulk insert for simplicity)
            # Note: For high-volume production, consider incremental append strategy
            conversation_history = state_dict.get("conversation_history", [])
            
            # Always delete existing messages first (even if list is empty)
            self.client.table("conversation_messages").delete().eq("session_id", session_id).execute()
            
            if conversation_history:
                # Bulk insert new messages
                # Note: We let DB assign timestamps (NOW()) for all messages
                # This means re-saves will update timestamps, but ensures consistency
                message_records = [
                    {
                        "session_id": session_id,
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                        "metadata": msg.get("metadata", {}),
                        # Let DB assign created_at via DEFAULT NOW()
                    }
                    for msg in conversation_history
                ]
                
                self.client.table("conversation_messages").insert(message_records).execute()
            
            # 3. Upsert mockups (identity-based merge by screen_id)
            mockups = state_dict.get("mockups", [])
            for mockup in mockups:
                mockup_data = {
                    "session_id": session_id,
                    "screen_id": mockup.get("screen_id"),
                    "screen_name": mockup.get("screen_name"),
                    "wireframe_spec": mockup.get("wireframe_spec", {}),
                    "excalidraw_scene": mockup.get("excalidraw_scene"),
                    "screenshot_path": mockup.get("screenshot_path"),
                    "user_flow": mockup.get("user_flow"),
                    "interactions": mockup.get("interactions", []),
                    "template_used": mockup.get("template_used", "blank"),
                    "version": mockup.get("version", "1.0"),
                }
                
                # Upsert with explicit conflict resolution on (session_id, screen_id)
                self.client.table("mockups")\
                    .upsert(mockup_data, on_conflict="session_id,screen_id")\
                    .execute()
            
        except Exception as e:
            print(f"[SupabaseAdapter] Error saving session {session_id}: {e}")
            raise

    async def delete(self, session_id: str) -> None:
        """Delete a project session (cascades to messages and mockups)."""
        try:
            self.client.table("projects").delete().eq("session_id", session_id).execute()
        except Exception as e:
            print(f"[SupabaseAdapter] Error deleting session {session_id}: {e}")
            raise

    async def list_sessions(self) -> List[str]:
        """List all session IDs."""
        try:
            response = self.client.table("projects").select("session_id").execute()
            return [row["session_id"] for row in response.data]
        except Exception as e:
            print(f"[SupabaseAdapter] Error listing sessions: {e}")
            return []

    async def get_last_messages(self, session_id: str, n: int = 10) -> List[Dict[str, Any]]:
        """Get the last N conversation messages for a session."""
        try:
            response = (
                self.client.table("conversation_messages")
                .select("role, content, created_at, metadata")
                .eq("session_id", session_id)
                .order("created_at", desc=True)
                .limit(n)
                .execute()
            )
            
            # Return in chronological order (oldest first)
            messages = [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["created_at"],
                }
                for msg in reversed(response.data)
            ]
            
            return messages
            
        except Exception as e:
            print(f"[SupabaseAdapter] Error getting messages for {session_id}: {e}")
            return []

    async def load_state(self, session_id: str) -> Optional[ProjectState]:
        """Load project state as a ProjectState model instance."""
        state_dict = await self.get(session_id)
        if not state_dict:
            return None
        
        try:
            return ProjectState(**state_dict)
        except Exception as e:
            print(f"[SupabaseAdapter] Error parsing ProjectState for {session_id}: {e}")
            return None

    async def save_project_state(self, session_id: str, state: ProjectState) -> None:
        """Save a ProjectState model instance."""
        await self.save(session_id, state.model_dump())


# ============================================================================
# Factory Function
# ============================================================================

def create_supabase_adapter(
    supabase_url: str | None = None,
    supabase_key: str | None = None,
) -> SupabaseAdapter:
    """Create and return a SupabaseAdapter instance.
    
    Args:
        supabase_url: Optional Supabase URL (defaults to env var)
        supabase_key: Optional Supabase key (defaults to env var)
    
    Returns:
        Configured SupabaseAdapter instance
    
    Raises:
        ImportError: If supabase package not installed
        ValueError: If credentials not provided
    """
    return SupabaseAdapter(supabase_url=supabase_url, supabase_key=supabase_key)
