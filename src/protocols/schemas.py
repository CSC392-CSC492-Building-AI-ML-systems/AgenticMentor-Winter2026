"""Pydantic schemas for output validation."""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
from typing import Literal

class MermaidLLMResponse(BaseModel):
        """Structured Mermaid response expected from LLM diagram generation."""
        diagram_type: Literal["system", "erd"] = Field(
            description="The requested Mermaid diagram type."
        )
        mermaid_code: str = Field(
            min_length=1,
            description="Raw Mermaid code only, no markdown fences.",
        )

class ValidationResult(BaseModel):
        """Represents the result of validating an agent output."""
        valid: bool
        message: str = ""


class MessageRole(str, Enum):
    """Message roles in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Single chat message."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ProjectCreate(BaseModel):
    """Request model for creating a new project."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class RequirementsState(BaseModel):
    """Structured requirements state."""
    project_type: Optional[str] = None
    target_users: Optional[List[str]] = None
    key_features: List[str] = Field(default_factory=list)
    technical_constraints: List[str] = Field(default_factory=list)
    business_goals: List[str] = Field(default_factory=list)
    timeline: Optional[str] = None
    budget: Optional[str] = None
    is_complete: bool = False
    progress: float = 0.0  # 0.0 to 1.0
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_type": "web application",
                "target_users": ["students", "teachers"],
                "key_features": ["user authentication", "dashboard"],
                "technical_constraints": ["must use Python", "cloud hosted"],
                "business_goals": ["launch in 3 months"],
                "timeline": "3 months",
                "budget": "$10,000",
                "is_complete": False,
                "progress": 0.6
            }
        }


class ProjectState(BaseModel):
    """Complete project state including requirements and metadata."""
    project_id: str
    name: str
    description: Optional[str] = None
    requirements: RequirementsState = Field(default_factory=RequirementsState)
    decisions: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    conversation_history: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)


class ProjectResponse(BaseModel):
    """Response model for project operations."""
    project_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    last_updated: datetime
    requirements: RequirementsState


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    """Standardized response for chat interactions."""
    message: str
    state: Dict[str, Any]
    artifacts: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "What type of application are you building?",
                "state": {
                    "requirements": {
                        "is_complete": False,
                        "progress": 0.1
                    }
                },
                "artifacts": {
                    "decisions": [],
                    "assumptions": []
                }
            }
        }
    