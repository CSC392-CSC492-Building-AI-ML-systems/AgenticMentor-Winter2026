"""Pydantic model for the agentic workflow state."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProjectState(BaseModel):
    """Represents the shared state across the agentic workflow."""

    project_id: str = Field(default_factory=lambda: "project-unknown")
    user_intent: str = ""
    requirements: list[str] = Field(default_factory=list)
    architecture: dict[str, Any] = Field(default_factory=dict)
    plan: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    status: str = "initialized"
    updated_at: datetime = Field(default_factory=datetime.utcnow)
