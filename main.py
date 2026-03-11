from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uuid
from datetime import datetime

from src.protocols.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectStateResponse,
    ChatRequest,
    ChatResponse,
    AgentResult,
    AvailableAgent,
    RequirementsState,
    FirebaseUser,
    EmailPasswordSignUpRequest,
    EmailPasswordLoginRequest,
    TokenVerificationRequest,
    TokenResponse,
)
from src.utils.config import settings
from src.storage.memory_store import default_memory_adapter
from src.state.state_manager import StateManager
from src.orchestrator.master_agent import MasterOrchestrator
from src.state.project_state import ProjectState as OrchestratorState
from src.auth.firebase_auth import (
    get_current_user,
    signup_with_email_password,
    login_with_email_password,
    verify_id_token_payload,
)

# Module-level singletons initialised in lifespan
state_manager: StateManager | None = None
orchestrator: MasterOrchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global state_manager, orchestrator
    print(f"Starting AgenticMentor API on {settings.api_host}:{settings.api_port}")
    state_manager = StateManager(default_memory_adapter)
    orchestrator = MasterOrchestrator(state_manager)
    yield
    print("Shutting down AgenticMentor API")


app = FastAPI(
    title="AgenticMentor API",
    description="AI-powered multi-agent project planning system",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_orchestrator() -> MasterOrchestrator:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    return orchestrator


def _get_state_manager() -> StateManager:
    if state_manager is None:
        raise HTTPException(status_code=503, detail="State manager not ready")
    return state_manager


def _requirements_to_schema(req_dict: dict) -> RequirementsState:
    """Map orchestrator Requirements dict to the API RequirementsState schema."""
    return RequirementsState(
        project_type=req_dict.get("project_type"),
        target_users=req_dict.get("target_users") or [],
        key_features=req_dict.get("functional") or req_dict.get("key_features") or [],
        technical_constraints=req_dict.get("constraints") or req_dict.get("technical_constraints") or [],
        business_goals=req_dict.get("business_goals") or [],
        timeline=req_dict.get("timeline"),
        budget=req_dict.get("budget"),
        is_complete=bool(req_dict.get("is_complete", False)),
        progress=float(req_dict.get("progress") or 0.0),
    )


def _orch_state_to_full_response(
    project_id: str,
    orch_state: OrchestratorState,
    available_agents: list[dict] | None = None,
) -> ProjectStateResponse:
    req = orch_state.requirements.model_dump() if orch_state.requirements else {}
    arch = orch_state.architecture.model_dump() if orch_state.architecture else {}
    roadmap = orch_state.roadmap.model_dump() if orch_state.roadmap else {}
    mockups = [m.model_dump() if hasattr(m, "model_dump") else m for m in (orch_state.mockups or [])]
    history = [
        h if isinstance(h, dict) else h.model_dump()
        for h in (orch_state.conversation_history or [])
    ]
    return ProjectStateResponse(
        project_id=project_id,
        name=orch_state.project_name or project_id,
        description=None,
        created_at=orch_state.created_at,
        last_updated=orch_state.updated_at,
        current_phase=orch_state.current_phase,
        requirements=req,
        architecture=arch,
        roadmap=roadmap,
        mockups=mockups,
        conversation_history=history,
        available_agents=available_agents or [],
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.2.0",
    }


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/auth/signup/email", response_model=TokenResponse, status_code=201)
async def auth_signup_email(request: EmailPasswordSignUpRequest) -> TokenResponse:
    data = await signup_with_email_password(email=request.email, password=request.password)
    return TokenResponse(
        id_token=data.get("idToken"),
        refresh_token=data.get("refreshToken"),
        expires_in=int(data.get("expiresIn")) if data.get("expiresIn") is not None else None,
        user_id=data.get("localId"),
        email=data.get("email"),
    )


@app.post("/auth/login/email", response_model=TokenResponse)
async def auth_login_email(request: EmailPasswordLoginRequest) -> TokenResponse:
    data = await login_with_email_password(email=request.email, password=request.password)
    return TokenResponse(
        id_token=data.get("idToken"),
        refresh_token=data.get("refreshToken"),
        expires_in=int(data.get("expiresIn")) if data.get("expiresIn") is not None else None,
        user_id=data.get("localId"),
        email=data.get("email"),
    )


@app.post("/auth/verify-token", response_model=FirebaseUser)
async def auth_verify_token(request: TokenVerificationRequest) -> FirebaseUser:
    return await verify_id_token_payload(request.id_token)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@app.get("/projects")
async def list_projects(
    current_user: FirebaseUser = Depends(get_current_user),
):
    """List all project IDs with basic metadata."""
    session_ids = await default_memory_adapter.list_sessions()
    result = []
    for sid in session_ids:
        raw = await default_memory_adapter.get(sid)
        if raw:
            result.append({
                "project_id": sid,
                "project_name": raw.get("project_name") or sid,
                "current_phase": raw.get("current_phase", "initialization"),
                "created_at": raw.get("created_at"),
            })
    return result


@app.post("/projects", response_model=ProjectStateResponse, status_code=201)
async def create_project(
    project: ProjectCreate,
    current_user: FirebaseUser = Depends(get_current_user),
):
    """Create a new project and return its full initial state."""
    sm = _get_state_manager()
    orch = _get_orchestrator()

    project_id = str(uuid.uuid4())
    initial_state = OrchestratorState(
        session_id=project_id,
        project_name=project.name,
    )
    await default_memory_adapter.save(project_id, initial_state.model_dump())

    available_agents = orch._get_available_agents(initial_state)
    return _orch_state_to_full_response(project_id, initial_state, available_agents)


@app.get("/projects/{project_id}", response_model=ProjectStateResponse)
async def get_project(
    project_id: str,
    current_user: FirebaseUser = Depends(get_current_user),
):
    """Get full project state by ID."""
    sm = _get_state_manager()
    orch = _get_orchestrator()

    orch_state = await sm.load(project_id)
    if orch_state is None or orch_state.session_id != project_id:
        raise HTTPException(status_code=404, detail="Project not found")

    available_agents = orch._get_available_agents(orch_state)
    return _orch_state_to_full_response(project_id, orch_state, available_agents)


@app.post("/projects/{project_id}/chat", response_model=ChatResponse)
async def chat(
    project_id: str,
    request: ChatRequest,
    current_user: FirebaseUser = Depends(get_current_user),
):
    """Send a message to the orchestrator and get a multi-agent response."""
    sm = _get_state_manager()
    orch = _get_orchestrator()

    # Verify project exists
    existing = await default_memory_adapter.get(project_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        result = await orch.process_request(
            user_input=request.message,
            session_id=project_id,
            agent_selection_mode=request.agent_selection_mode,
            selected_agent_id=request.selected_agent_id,
        )
    except Exception as e:
        print(f"[chat] Orchestrator error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Orchestrator error: {str(e)}") from e

    state_snapshot = result.get("state_snapshot") or {}
    raw_agent_results = result.get("agent_results") or []
    raw_available_agents = result.get("available_agents") or []

    agent_results = [AgentResult(**ar) for ar in raw_agent_results]
    available_agents = [AvailableAgent(**aa) for aa in raw_available_agents]

    return ChatResponse(
        message=result.get("message") or "",
        state=state_snapshot,
        artifacts={},
        agent_results=agent_results,
        available_agents=available_agents,
        current_phase=state_snapshot.get("current_phase", "initialization"),
    )


@app.get("/projects/{project_id}/requirements", response_model=RequirementsState)
async def get_requirements(
    project_id: str,
    current_user: FirebaseUser = Depends(get_current_user),
):
    """Get current requirements state for a project."""
    sm = _get_state_manager()
    orch_state = await sm.load(project_id)
    if orch_state is None or orch_state.session_id != project_id:
        raise HTTPException(status_code=404, detail="Project not found")

    req = orch_state.requirements.model_dump() if orch_state.requirements else {}
    return _requirements_to_schema(req)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )
