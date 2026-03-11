"""Pydantic schemas for output validation."""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr
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
    pending_confirmation: bool = False  # True when we filled defaults; ask user to confirm before proceeding
    
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
    agent_selection_mode: str = "auto"          # "auto" | "manual"
    selected_agent_id: Optional[str] = None     # required when mode is "manual"


class AgentResult(BaseModel):
    """Result from a single agent execution."""
    agent_id: str
    agent_name: str
    status: str  # "success" | "failed_timeout" | "failed_runtime" | "skipped_unavailable" | "blocked_dependency"
    content: str = ""
    state_delta_keys: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    blocked_by: Optional[List[str]] = None


class AvailableAgent(BaseModel):
    """Agent availability entry returned to the UI agent picker."""
    agent_id: str
    agent_name: str
    description: str = ""
    interaction_mode: str = "functional"
    is_phase_compatible: bool
    unmet_requires: List[str] = Field(default_factory=list)
    blocked_by: List[str] = Field(default_factory=list)
    is_available: bool
    expensive: bool = False
    supports_selective_regen: bool = False


class ChatResponse(BaseModel):
    """Standardized response for chat interactions."""
    message: str
    state: Dict[str, Any]
    artifacts: Dict[str, Any]
    agent_results: List[AgentResult] = Field(default_factory=list)
    available_agents: List[AvailableAgent] = Field(default_factory=list)
    current_phase: str = "initialization"


class ProjectStateResponse(BaseModel):
    """Full project state returned to the frontend (GET /projects/{id})."""
    project_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    last_updated: datetime
    current_phase: str = "initialization"
    requirements: Dict[str, Any] = Field(default_factory=dict)
    architecture: Dict[str, Any] = Field(default_factory=dict)
    roadmap: Dict[str, Any] = Field(default_factory=dict)
    mockups: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    available_agents: List[Dict[str, Any]] = Field(default_factory=list)


class FirebaseUser(BaseModel):
    """Representation of an authenticated Firebase user."""
    uid: str
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    provider_id: Optional[str] = None
    claims: Dict[str, Any] = Field(default_factory=dict)


class EmailPasswordSignUpRequest(BaseModel):
    """Request body for signing up with email/password."""
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class EmailPasswordLoginRequest(BaseModel):
    """Request body for logging in with email/password."""
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class TokenVerificationRequest(BaseModel):
    """Request body for verifying an existing Firebase ID token."""
    id_token: str = Field(min_length=10)


class TokenResponse(BaseModel):
    """Standardised response for authentication tokens returned by Firebase REST API."""
    id_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    user_id: Optional[str] = None
    email: Optional[EmailStr] = None
