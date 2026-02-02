from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uuid
from datetime import datetime

from src.models.schemas import (
    ProjectCreate,
    ProjectResponse,
    ChatRequest,
    ChatResponse,
    ProjectState,
)
from src.core.config import settings


# In-memory storage (will be moved to separate module in Phase 3)
projects_store: dict[str, ProjectState] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    print(f"Starting AgenticMentor API on {settings.api_host}:{settings.api_port}")
    yield
    print("Shutting down AgenticMentor API")


app = FastAPI(
    title="AgenticMentor API",
    description="Project Requirements Agent",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
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
        "version": "0.1.0",
    }


@app.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(project: ProjectCreate):
    """Create a new project and return project_id."""
    project_id = str(uuid.uuid4())

    project_state = ProjectState(
        project_id=project_id,
        name=project.name,
        description=project.description,
    )

    projects_store[project_id] = project_state

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
    if project_id not in projects_store:
        raise HTTPException(status_code=404, detail="Project not found")

    project_state = projects_store[project_id]

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
    if project_id not in projects_store:
        raise HTTPException(status_code=404, detail="Project not found")

    # TODO: Wire up to LangGraph agent in Phase 2
    # For now, return a mock response

    return ChatResponse(
        message="Thank you! I'll start by understanding your project. What type of application or system are you looking to build?",
        state={
            "requirements": projects_store[project_id].requirements.model_dump(),
        },
        artifacts={
            "decisions": projects_store[project_id].decisions,
            "assumptions": projects_store[project_id].assumptions,
        },
    )


@app.get("/projects/{project_id}/requirements")
async def get_requirements(project_id: str):
    """Get current requirements state for a project."""
    if project_id not in projects_store:
        raise HTTPException(status_code=404, detail="Project not found")

    return projects_store[project_id].requirements


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )
