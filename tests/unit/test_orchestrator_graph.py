"""Unit tests for orchestrator LangGraph and MasterOrchestrator."""
import pytest

from src.orchestrator.graph import build_orchestrator_graph, OrchestratorState
from src.orchestrator.intent_classifier import IntentClassifier
from src.orchestrator.execution_planner import ExecutionPlanner
from src.orchestrator.master_agent import MasterOrchestrator
from src.state.project_state import ProjectState, Requirements


@pytest.fixture
def mock_state_manager():
    """In-memory state manager for tests."""
    class MockStateManager:
        def __init__(self):
            self._store = {}

        async def load(self, session_id: str):
            if session_id not in self._store:
                self._store[session_id] = ProjectState(
                    session_id=session_id,
                    current_phase="initialization",
                    requirements=Requirements(),
                )
            return self._store[session_id]

    return MockStateManager()


@pytest.fixture
def intent_classifier():
    return IntentClassifier(llm=None)


@pytest.fixture
def execution_planner():
    return ExecutionPlanner()


@pytest.fixture
def compiled_graph(mock_state_manager, intent_classifier, execution_planner):
    return build_orchestrator_graph(
        mock_state_manager, intent_classifier, execution_planner
    )


@pytest.mark.asyncio
async def test_graph_load_state_classify_build_plan(compiled_graph, mock_state_manager):
    """Graph ainvoke: load_state -> classify_intent -> build_plan; state has intent and plan."""
    initial: OrchestratorState = {
        "user_input": "I want to clarify our goals",
        "session_id": "test-session-1",
    }
    result = await compiled_graph.ainvoke(initial)
    assert "intent" in result
    assert result["intent"]["primary_intent"] == "requirements_gathering"
    assert "requirements_collector" in result["intent"]["requires_agents"]
    assert "plan" in result
    assert len(result["plan"].tasks) >= 1
    assert result["plan"].tasks[0].agent_id == "requirements_collector"
    assert "project_state" in result
    assert result["project_state"].session_id == "test-session-1"
    assert result.get("error") is None


@pytest.mark.asyncio
async def test_graph_architecture_intent():
    """User asks for architecture in requirements_complete -> plan has project_architect."""
    from src.state.project_state import ArchitectureDefinition

    async def load_s2(_sid):
        return ProjectState(
            session_id="s2",
            current_phase="requirements_complete",
            requirements=Requirements(functional=["API"]),
            architecture=ArchitectureDefinition(),
        )

    class MockSM:
        async def load(self, sid):
            return await load_s2(sid) if sid == "s2" else ProjectState(session_id=sid)

    graph = build_orchestrator_graph(MockSM(), IntentClassifier(llm=None), ExecutionPlanner())
    result = await graph.ainvoke({
        "user_input": "generate the architecture",
        "session_id": "s2",
    })
    assert result["intent"]["primary_intent"] == "architecture_design"
    agent_ids = [t.agent_id for t in result["plan"].tasks]
    assert "project_architect" in agent_ids


@pytest.mark.asyncio
async def test_master_orchestrator_process_request(mock_state_manager):
    """MasterOrchestrator.process_request returns intent, plan, project_state."""
    orch = MasterOrchestrator(mock_state_manager, use_llm=False)
    out = await orch.process_request("I want to clarify our goals", "s1")
    assert "intent" in out
    assert out["intent"]["primary_intent"] == "requirements_gathering"
    assert "plan" in out
    assert len(out["plan"].tasks) >= 1
    assert "project_state" in out
    assert out.get("error") is None


@pytest.mark.asyncio
async def test_master_orchestrator_export_intent(mock_state_manager):
    """Process_request with export message -> intent export, plan has exporter."""
    orch = MasterOrchestrator(mock_state_manager, use_llm=False)
    out = await orch.process_request("export the document to PDF", "s1")
    assert out["intent"]["primary_intent"] == "export"
    agent_ids = [t.agent_id for t in out["plan"].tasks]
    assert "exporter" in agent_ids


@pytest.mark.asyncio
async def test_unknown_intent_gets_full_pipeline_fallback(mock_state_manager):
    """When intent is unknown (gibberish input), plan defaults to full pipeline so we still get a useful plan."""
    orch = MasterOrchestrator(mock_state_manager, use_llm=False)
    out = await orch.process_request("xyzzz qqq nothing matches", "s1")
    assert out["intent"]["primary_intent"] == "unknown"
    assert len(out["plan"].tasks) >= 1
    agent_ids = [t.agent_id for t in out["plan"].tasks]
    assert "requirements_collector" in agent_ids
    assert "exporter" in agent_ids
