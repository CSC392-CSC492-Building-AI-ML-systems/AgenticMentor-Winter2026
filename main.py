import uuid
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# CRITICAL: Load .env before importing project modules so the adapter 
# sees the credentials during its initialization phase.
load_dotenv()

from src.protocols.schemas import (
    ProjectCreate,
    ProjectResponse,
    ChatRequest,
    ProjectState,
)
from src.utils.config import settings

# Import the StateManager and MasterOrchestrator for Phase 4
from src.state.persistence import get_default_adapter
from src.state.state_manager import StateManager
from src.orchestrator.master_agent import MasterOrchestrator

# Initialize the adapter, state manager, and orchestrator in the correct order
db_adapter = get_default_adapter()
state_manager = StateManager(db_adapter)
orchestrator = MasterOrchestrator(state_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    print(f"Starting AgenticMentor API on {settings.api_host}:{settings.api_port}")
    yield
    print("Shutting down AgenticMentor API")


app = FastAPI(
    title="AgenticMentor API",
    description="AI-powered multi-agent project generation system",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0"
    }


@app.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(project: ProjectCreate):
    """Create a new project and initialize state."""
    # Align with the DB session_id primary key
    session_id = f"session_{uuid.uuid4().hex[:12]}"
    
    # Initialize state through the StateManager cache/DB
    state = await state_manager.load(session_id)
    
    # Use dotted-path updates to map description to requirements.project_type
    delta = {
        "project_name": project.name,
        "requirements.project_type": project.description,
        "current_phase": "initialization"
    }
    state = await state_manager.update(session_id, delta)

    # Ensure requirements is a dict for the Response model
    req_dict = state.requirements.model_dump() if hasattr(state.requirements, "model_dump") else state.requirements

    return ProjectResponse(
        project_id=state.session_id,
        name=state.project_name,
        description=project.description,
        created_at=state.created_at,
        last_updated=state.updated_at,
        requirements=req_dict,
    )


@app.get("/projects/{session_id}", response_model=ProjectResponse)
async def get_project(session_id: str):
    """Get project state by ID."""
    state = await state_manager.load(session_id)
    
    if not state.project_name: 
        raise HTTPException(status_code=404, detail="Project not found")

    # Recover the description from the JSONB field project_type
    description = state.requirements.project_type if state.requirements else ""
    req_dict = state.requirements.model_dump() if hasattr(state.requirements, "model_dump") else state.requirements

    return ProjectResponse(
        project_id=state.session_id,
        name=state.project_name,
        description=description,
        created_at=state.created_at,
        last_updated=state.updated_at,
        requirements=req_dict,
    )


@app.post("/projects/{session_id}/chat")
async def chat(session_id: str, request: ChatRequest):
    """Route message through Orchestrator to the correct agent."""
    state = await state_manager.load(session_id)
    if not state.project_name:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # Corrected method call to process_request per master_agent definition
        response = await orchestrator.process_request(
            user_input=request.message,
            session_id=session_id
        )
        
        # Reload state to capture agent updates and phase changes
        updated_state = await state_manager.load(session_id)
        
        # Extract metadata about which agent actually handled the task
        agent_used = None
        if response.get("agent_results"):
            agent_used = response["agent_results"][0].get("agent_id")

        return {
            "message": response.get("message", "Processing complete."),
            "current_phase": updated_state.current_phase,
            "agent_used": agent_used,
            "state_snapshot": {
                "requirements_progress": updated_state.requirements.progress if updated_state.requirements else 0.0,
                "has_architecture": bool(updated_state.architecture and updated_state.architecture.tech_stack),
                "mockup_count": len(updated_state.mockups) if updated_state.mockups else 0
            }
        }
        
    except Exception as e:
        print(f"[main] Error in orchestrator flow: {e}")
        raise HTTPException(status_code=500, detail=f"Orchestrator Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host=settings.api_host, 
        port=settings.api_port, 
        reload=settings.api_debug
    )