
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

class ProjectState(BaseModel):
    """
    Single source of truth for project plan
    """
    # Metadata
    session_id: str
    project_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    current_phase: str = "initialization"  # State machine phase
    
    # Requirements Layer
    requirements: Requirements = Field(default_factory=Requirements)
    
    # Architecture Layer
    architecture: Architecture = Field(default_factory=Architecture)
    
    # Design Layer
    mockups: List[Mockup] = Field(default_factory=list)
    
    # Execution Layer
    roadmap: Roadmap = Field(default_factory=Roadmap)
    
    # Metadata
    conversation_history: List[dict] = Field(default_factory=list)
    agent_interactions: Dict[str, int] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True

class Requirements(BaseModel):
    functional: List[str] = []
    non_functional: List[str] = []
    constraints: List[str] = []
    user_stories: List[UserStory] = []
    gaps: List[str] = []  # Identified by RequirementsCollector

class Architecture(BaseModel):
    tech_stack: Dict[str, str] = {}  # {"frontend": "React", ...}
    data_schema: Optional[str] = None  # Mermaid ER diagram
    system_diagram: Optional[str] = None  # Mermaid architecture
    api_design: List[APIEndpoint] = []
    deployment_strategy: Optional[str] = None

class Mockup(BaseModel):
    screen_name: str
    wireframe_code: str  # ASCII or SVG
    user_flow: Optional[str] = None  # Mermaid flowchart
    interactions: List[str] = []

class Roadmap(BaseModel):
    milestones: List[Milestone] = []
    sprints: List[Sprint] = []
    critical_path: Optional[str] = None  # Mermaid Gantt chart