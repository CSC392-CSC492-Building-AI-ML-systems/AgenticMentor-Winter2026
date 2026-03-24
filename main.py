import uuid
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# CRITICAL: Load .env before importing project modules so the adapter 
# sees the credentials during its initialization phase.
load_dotenv()

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
    LLMSettingsRequest,
    LLMSettingsResponse,
    LLMSettingsVerifyRequest,
    LLMVerifyResponse,
)
from src.utils.config import settings
from src.state.state_manager import StateManager
from src.orchestrator.master_agent import MasterOrchestrator
from src.state.project_state import ProjectState as OrchestratorState
from src.auth.firebase_auth import (
    get_current_user,
    signup_with_email_password,
    login_with_email_password,
    verify_id_token_payload,
)
from src.services.llm_custom_key_store import (
    delete_all_for_user,
    delete_custom_key,
    get_custom_key,
    set_custom_key,
)
from src.services.llm_settings_service import (
    now_iso,
    public_llm_runtime_view,
    sanitize_llm_settings,
    verify_gemini_key_model,
)

from src.state.persistence import get_default_adapter

# Module-level singletons (initialised once at startup)
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_orchestrator() -> MasterOrchestrator:
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    return orchestrator


def _get_state_manager() -> StateManager:
    return state_manager


async def _assert_project_owner(project_id: str, current_user: FirebaseUser) -> None:
    """Ensure the requested project belongs to the current user."""
    raw = await _get_state_manager().db.get(project_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Project not found")
    if (raw.get("owner_uid") or "") != (current_user.uid or ""):
        raise HTTPException(status_code=404, detail="Project not found")


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
        export_artifacts=orch_state.export_artifacts.model_dump() if orch_state.export_artifacts else {},
        llm_settings=sanitize_llm_settings(
            getattr(orch_state, "llm_settings", None),
            owner_uid=getattr(orch_state, "owner_uid", None),
            project_id=project_id,
        ),
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

@app.get("/auth/me", response_model=FirebaseUser)
async def auth_me(current_user: FirebaseUser = Depends(get_current_user)) -> FirebaseUser:
    """Debug helper: return the currently authenticated Firebase user."""
    return current_user


@app.post("/auth/clear-llm-keys", status_code=204)
async def auth_clear_llm_keys(current_user: FirebaseUser = Depends(get_current_user)) -> None:
    """Drop all in-memory Gemini keys for this user (call before logout)."""
    delete_all_for_user(current_user.uid or "")


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@app.get("/projects")
async def list_projects(
    current_user: FirebaseUser = Depends(get_current_user),
):
    """List all project IDs with basic metadata."""
    sm = _get_state_manager()
    session_ids = await sm.db.list_sessions(owner_uid=current_user.uid)
    result = []
    for sid in session_ids:
        raw = await sm.db.get(sid)
        if raw:
            reqs = raw.get("requirements") or {}
            display_name = (
                reqs.get("app_name")
                or reqs.get("project_type")
                or raw.get("project_name")
                or sid
            )
            result.append({
                "project_id": sid,
                "project_name": display_name,
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
    orch = _get_orchestrator()

    project_id = str(uuid.uuid4())
    initial_state = OrchestratorState(
        session_id=project_id,
        owner_uid=current_user.uid,
        project_name=project.name,
    )
    await _get_state_manager().db.save(project_id, initial_state.model_dump())

    available_agents = orch._get_available_agents(initial_state)
    return _orch_state_to_full_response(project_id, initial_state, available_agents)


@app.get("/projects/{project_id}", response_model=ProjectStateResponse)
async def get_project(
    project_id: str,
    current_user: FirebaseUser = Depends(get_current_user),
):
    """Get full project state by ID."""
    orch = _get_orchestrator()
    await _assert_project_owner(project_id, current_user)

    orch_state = await _get_state_manager().load(project_id)
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
    orch = _get_orchestrator()

    await _assert_project_owner(project_id, current_user)

    try:
        result = await orch.process_request(
            user_input=request.message,
            session_id=project_id,
            agent_selection_mode=request.agent_selection_mode,
            selected_agent_id=request.selected_agent_id,
            owner_uid=current_user.uid,
        )
    except Exception as e:
        print(f"[chat] Orchestrator error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Orchestrator error: {str(e)}") from e

    orch_state_after = await _get_state_manager().load(project_id)
    llm_rt = public_llm_runtime_view(orch_state_after, owner_uid=current_user.uid)

    state_snapshot = result.get("state_snapshot") or {}
    # Never expose raw custom API key to frontend.
    if isinstance(state_snapshot, dict) and "llm_settings" in state_snapshot:
        llm_settings = state_snapshot.get("llm_settings")
        if isinstance(llm_settings, dict):
            llm_settings.pop("custom_api_key", None)
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
        llm_runtime=llm_rt,
    )


@app.get("/projects/{project_id}/llm-runtime")
async def get_llm_runtime_ephemeral(
    project_id: str,
    current_user: FirebaseUser = Depends(get_current_user),
) -> dict:
    """Effective model/key source for this project (no secrets). For console UI."""
    await _assert_project_owner(project_id, current_user)
    orch_state = await _get_state_manager().load(project_id)
    if orch_state is None or orch_state.session_id != project_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return public_llm_runtime_view(orch_state, owner_uid=current_user.uid)


@app.get("/projects/{project_id}/llm-settings", response_model=LLMSettingsResponse)
async def get_llm_settings(
    project_id: str,
    current_user: FirebaseUser = Depends(get_current_user),
):
    await _assert_project_owner(project_id, current_user)
    orch_state = await _get_state_manager().load(project_id)
    if orch_state is None or orch_state.session_id != project_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return LLMSettingsResponse(
        **sanitize_llm_settings(
            getattr(orch_state, "llm_settings", None),
            owner_uid=current_user.uid,
            project_id=project_id,
        )
    )


@app.post("/projects/{project_id}/llm-settings", response_model=LLMSettingsResponse)
async def set_llm_settings(
    project_id: str,
    request: LLMSettingsRequest,
    current_user: FirebaseUser = Depends(get_current_user),
):
    await _assert_project_owner(project_id, current_user)
    orch_state = await _get_state_manager().load(project_id)
    if orch_state is None or orch_state.session_id != project_id:
        raise HTTPException(status_code=404, detail="Project not found")

    uid = current_user.uid or ""

    # Backfill owner_uid on older rows so key lookup via project_state stays consistent.
    owner_patch: dict = {}
    if uid and not (getattr(orch_state, "owner_uid", None) or "").strip():
        owner_patch["owner_uid"] = uid

    if request.mode == "default":
        delete_custom_key(uid, project_id)
        delta = {
            **owner_patch,
            "llm_settings": {
                "mode": "default",
                "model": request.model,
                "verified": False,
                "verified_at": None,
            },
        }
    else:
        new_key = (request.custom_api_key or "").strip() if request.custom_api_key is not None else ""
        mem_before = (get_custom_key(uid, project_id) or "").strip()
        if new_key:
            set_custom_key(uid, project_id, new_key)
            # Same key as already in memory (e.g. client resends after Verify). Do not wipe DB flags.
            if mem_before and new_key == mem_before:
                delta = {
                    **owner_patch,
                    "llm_settings": {
                        "mode": "custom",
                        "model": request.model,
                    },
                }
            else:
                delta = {
                    **owner_patch,
                    "llm_settings": {
                        "mode": "custom",
                        "model": request.model,
                        "verified": False,
                        "verified_at": None,
                    },
                }
        else:
            mem = get_custom_key(uid, project_id)
            if mem:
                # Do not send verified/verified_at: merge keeps existing flags. Avoids wiping
                # verification after "Verify" when user hits Save without re-pasting the key
                # (race or stale read could set verified=False while key is already in memory).
                delta = {
                    **owner_patch,
                    "llm_settings": {
                        "mode": "custom",
                        "model": request.model,
                    },
                }
            else:
                delta = {
                    **owner_patch,
                    "llm_settings": {
                        "mode": "custom",
                        "model": request.model,
                        "verified": False,
                        "verified_at": None,
                    },
                }

    updated = await _get_state_manager().update(project_id, delta)
    return LLMSettingsResponse(
        **sanitize_llm_settings(
            getattr(updated, "llm_settings", None),
            owner_uid=uid,
            project_id=project_id,
        )
    )


@app.post("/projects/{project_id}/llm-settings/verify", response_model=LLMVerifyResponse)
async def verify_llm_settings(
    project_id: str,
    request: LLMSettingsVerifyRequest,
    current_user: FirebaseUser = Depends(get_current_user),
):
    await _assert_project_owner(project_id, current_user)
    orch_state = await _get_state_manager().load(project_id)
    if orch_state is None or orch_state.session_id != project_id:
        raise HTTPException(status_code=404, detail="Project not found")

    valid, message = await verify_gemini_key_model(request.custom_api_key, request.model)
    runtime = None
    if valid:
        uid = current_user.uid or ""
        set_custom_key(uid, project_id, (request.custom_api_key or "").strip())
        owner_patch: dict = {}
        if uid and not (getattr(orch_state, "owner_uid", None) or "").strip():
            owner_patch["owner_uid"] = uid
        updated = await _get_state_manager().update(
            project_id,
            {
                **owner_patch,
                "llm_settings": {
                    "mode": "custom",
                    "model": request.model,
                    "verified": True,
                    "verified_at": now_iso(),
                },
            },
        )
        runtime = public_llm_runtime_view(updated, owner_uid=uid)
    return LLMVerifyResponse(valid=valid, message=message, runtime=runtime)


@app.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    current_user: FirebaseUser = Depends(get_current_user),
):
    """Delete a project and all its data."""
    await _assert_project_owner(project_id, current_user)
    delete_custom_key(current_user.uid or "", project_id)
    await _get_state_manager().db.delete(project_id)


@app.get("/projects/{project_id}/requirements", response_model=RequirementsState)
async def get_requirements(
    project_id: str,
    current_user: FirebaseUser = Depends(get_current_user),
):
    """Get current requirements state for a project."""
    await _assert_project_owner(project_id, current_user)
    orch_state = await _get_state_manager().load(project_id)
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
        reload_excludes=["venv/*", ".venv/*", "*.pyc", "__pycache__/*"],
    )