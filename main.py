from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uuid
from datetime import datetime

from src.protocols.schemas import (
    ProjectCreate,
    ProjectResponse,
    ChatRequest,
    ChatResponse,
    ProjectState,
    RequirementsState,
    ChatMessage,
    MessageRole,
)
from src.utils.config import settings
from src.agents.requirements_collector import get_agent
from src.storage.memory_store import default_memory_adapter


projects_store: dict[str, ProjectState] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    print(f"Starting AgenticMentor API on {settings.api_host}:{settings.api_port}")
    yield
    print("Shutting down AgenticMentor API")


app = FastAPI(
    title="AgenticMentor API",
    description="AI-powered project requirements collection system",
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
    """Create a new project and return project_id."""
    project_id = str(uuid.uuid4())
    
    project_state = ProjectState(
        project_id=project_id,
        name=project.name,
        description=project.description,
        requirements=RequirementsState(),
        decisions=[],
        assumptions=[],
        conversation_history=[],
        created_at=datetime.now(),
        last_updated=datetime.now(),
    )

    # Persist the created project via the in-memory adapter
    await default_memory_adapter.save(project_id, project_state.model_dump())

    return ProjectResponse(
        project_id=project_state.project_id,
        name=project_state.name,
        description=project_state.description,
        created_at=project_state.created_at,
        last_updated=project_state.last_updated,
        requirements=project_state.requirements,
    )


@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get project state by ID."""
    state_dict = await default_memory_adapter.get(project_id)
    if not state_dict:
        raise HTTPException(status_code=404, detail="Project not found")

    project_state = ProjectState(**state_dict)

    return ProjectResponse(
        project_id=project_state.project_id,
        name=project_state.name,
        description=project_state.description,
        created_at=project_state.created_at,
        last_updated=project_state.last_updated,
        requirements=project_state.requirements,
    )


@app.post("/projects/{project_id}/chat", response_model=ChatResponse)
async def chat(project_id: str, request: ChatRequest):
    """Send a message and get agent response."""
    state_dict = await default_memory_adapter.get(project_id)
    if not state_dict:
        raise HTTPException(status_code=404, detail="Project not found")

    project_state = ProjectState(**state_dict)
    user_message = ChatMessage(
        role=MessageRole.USER,
        content=request.message,
        timestamp=datetime.now()
    )
    project_state.conversation_history.append(user_message)

    agent = get_agent()
    
    try:
        result = await agent.process_message(
            user_message=request.message,
            current_requirements=project_state.requirements,
            conversation_history=project_state.conversation_history
        )
        
        project_state.requirements = result["requirements"]
        project_state.decisions.extend(result["decisions"])
        project_state.assumptions.extend(result["assumptions"])
        project_state.last_updated = datetime.now()

        assistant_message = ChatMessage(
            role=MessageRole.ASSISTANT,
            content=result["response"],
            timestamp=datetime.now()
        )
        project_state.conversation_history.append(assistant_message)

        # Persist updated state
        await default_memory_adapter.save(project_id, project_state.model_dump())

        return ChatResponse(
            message=result["response"],
            state={
                "requirements": result["requirements"].model_dump(),
                "is_complete": result["is_complete"],
                "progress": result["progress"]
            },
            artifacts={
                "decisions": result["decisions"],
                "assumptions": result["assumptions"]
            }
        )
        
    except Exception as e:
        print(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}") from e


@app.get("/projects/{project_id}/requirements", response_model=RequirementsState)
async def get_requirements(project_id: str):
    """Get current requirements state for a project."""
    state_dict = await default_memory_adapter.get(project_id)
    if not state_dict:
        raise HTTPException(status_code=404, detail="Project not found")

    project_state = ProjectState(**state_dict)
    return project_state.requirements


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )