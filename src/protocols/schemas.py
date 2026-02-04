"""Pydantic schemas for output validation."""

from __future__ import annotations

from pydantic import BaseModel


class ValidationResult(BaseModel):
    """Represents the result of validating an agent output."""

    valid: bool
    message: str = ""
