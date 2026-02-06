"""Pydantic schemas for output validation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    """Represents the result of validating an agent output."""

    valid: bool
    message: str = ""


class MermaidLLMResponse(BaseModel):
    """Structured Mermaid response expected from LLM diagram generation."""

    diagram_type: Literal["system", "erd"] = Field(
        description="The requested Mermaid diagram type."
    )
    mermaid_code: str = Field(
        min_length=1,
        description="Raw Mermaid code only, no markdown fences.",
    )
