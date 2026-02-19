"""Canonical state models shared by all agents."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class UserStory(BaseModel):
    """Simple user story representation."""

    role: str
    goal: str
    reason: Optional[str] = None


class APIEndpoint(BaseModel):
    """API endpoint contract used in architecture planning."""

    method: str
    path: str
    description: str


class Milestone(BaseModel):
    """Roadmap milestone."""

    name: str
    description: Optional[str] = None
    target_date: Optional[str] = None


class Phase(BaseModel):
    """A phase in the project execution plan (e.g. Setup, Core Build, Integration)."""

    name: str
    description: Optional[str] = None
    order: int = 0


class ImplementationTask(BaseModel):
    """Single implementation task with dependencies and optional external resources."""

    id: str = Field(description="Unique task id for dependency references")
    title: str
    description: Optional[str] = None
    phase_name: Optional[str] = None
    milestone_name: Optional[str] = None
    depends_on: List[str] = Field(default_factory=list, description="Ids of tasks that must complete first")
    external_resources: List[str] = Field(default_factory=list, description="Docs, APIs, or tools to use")
    order: int = 0


class Sprint(BaseModel):
    """Sprint container for execution planning."""

    name: str
    goal: Optional[str] = None
    tasks: List[str] = Field(default_factory=list)


class Requirements(BaseModel):
    """Requirements state fragment."""

    functional: List[str] = Field(default_factory=list)
    non_functional: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    user_stories: List[UserStory] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)


class ArchitectureDefinition(BaseModel):
    """Architecture state fragment produced by the architect agent."""

    tech_stack: Dict[str, str] = Field(default_factory=dict)
    tech_stack_rationale: Optional[str] = None  # LLM explanation for stack choices
    data_schema: Optional[str] = None
    system_diagram: Optional[str] = None
    api_design: List[APIEndpoint] = Field(default_factory=list)
    deployment_strategy: Optional[str] = None


class Mockup(BaseModel):
    """Design artifact produced by the mockup agent."""

    screen_name: str
    wireframe_code: str
    user_flow: Optional[str] = None
    interactions: List[str] = Field(default_factory=list)


class Roadmap(BaseModel):
    """Execution planning fragment: phases, milestones, ordered tasks, dependencies, resources."""

    phases: List[Phase] = Field(default_factory=list)
    milestones: List[Milestone] = Field(default_factory=list)
    implementation_tasks: List[ImplementationTask] = Field(default_factory=list)
    sprints: List[Sprint] = Field(default_factory=list)
    critical_path: Optional[str] = None
    external_resources: List[str] = Field(default_factory=list, description="Project-level external resources")


class ProjectState(BaseModel):
    """Single source of truth for the full project plan."""

    session_id: str
    project_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    current_phase: str = "initialization"
    requirements: Requirements = Field(default_factory=Requirements)
    architecture: ArchitectureDefinition = Field(default_factory=ArchitectureDefinition)
    mockups: List[Mockup] = Field(default_factory=list)
    roadmap: Roadmap = Field(default_factory=Roadmap)
    conversation_history: List[dict] = Field(default_factory=list)
    agent_interactions: Dict[str, int] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


# Backward-compatible alias used in earlier docs/code.
Architecture = ArchitectureDefinition