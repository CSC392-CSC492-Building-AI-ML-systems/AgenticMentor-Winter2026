# Orchestrator Refresher

Quick reference for how the orchestrator works and how to test it.

---

## What the orchestrator does

1. **Loads** project state for the session (from StateManager / persistence).
2. **Classifies intent** from the user message + current phase (rule-based or LLM).
3. **Builds an execution plan**: which agents to run, in dependency order (upstream first, then downstream).
4. **Runs each task**: calls the right agent with context (requirements, architecture, etc.), gets back `state_delta` and content.
5. **Updates state**: applies `state_delta`, advances phase (e.g. `requirements_complete` after requirements_collector), appends conversation history, persists.
6. **Returns** a single message to the user plus state snapshot, artifacts, intent, plan, agent results, and available agents (for UI).

---

## Main components

| Component | Role |
|-----------|------|
| **graph.py** | LangGraph: `load_state` → `classify_intent` → `build_plan` → END. No agents run inside the graph. |
| **intent_classifier.py** | Maps user message + `current_phase` → `IntentResult` (primary_intent, requires_agents, confidence). Rule-based (keywords/triggers) or optional LLM. |
| **execution_plan.py** | `Task` (agent_id, required_context), `ExecutionPlan` (list of tasks). |
| **execution_planner.py** | Builds plan from intent: resolves upstream deps (e.g. architect needs requirements), then downstream (e.g. exporter after others). Filters by `phase_compatibility`. Unknown intent → full pipeline. |
| **agent_store.py** | Metadata for each agent: id, requires, produces, phase_compatibility. `FULL_PIPELINE_AGENT_IDS` for unknown intent. |
| **agent_registry.py** | Lazy creation of real agents (requirements_collector, project_architect, execution_planner, mockup_agent, exporter). Returns None if agent init fails (e.g. no API key). |
| **master_agent.py** | Wires graph + registry; `process_request(user_input, session_id)` runs graph, then for each task calls `_run_agent`, applies state_delta and phase, persists, synthesizes message. Handles manual mode (bypass graph, run selected agent + upstream). |

---

## Intent → agents

| Intent | Typical agents in plan |
|--------|-------------------------|
| requirements_gathering | requirements_collector |
| architecture_design | project_architect |
| execution_planning | execution_planner |
| mockup_creation | mockup_agent |
| export | exporter |
| unknown | full pipeline: requirements_collector → project_architect → execution_planner → mockup_agent → exporter |

Phase compatibility (in agent_store and intent_classifier) can **filter** which of these actually get added to the plan (e.g. project_architect only when phase is `requirements_complete` or `architecture_complete`).

---

## Phase transitions (after an agent runs)

- requirements_collector → `requirements_complete`
- project_architect → `architecture_complete`
- execution_planner → `planning_complete`
- mockup_agent → `design_complete`
- exporter → `exportable`

---

## How to test

### Unit tests (no LLM, mock state)

From project root:

```bash
pytest tests/unit/test_orchestrator_graph.py tests/unit/test_intent_classifier.py tests/unit/test_execution_planner.py -v
```

### Agent transition suite (intent → plan, phase compatibility, multi-step)

Verifies each intent produces the right agents in the plan and that transitions (e.g. requirements then architecture then roadmap) yield the expected plans:

```bash
pytest tests/integration/test_orchestrator_agent_transitions.py -v
```

### State transition suite (state maintained, fed, and updated across agents)

Uses **real StateManager + InMemoryPersistenceAdapter** and a **fake agent registry** (no LLM). Ensures project state is correctly maintained, fed to each agent, and updated after each step:

- After each `process_request`, state snapshot has the expected shape (requirements, architecture, roadmap, phase).
- Context fed to each agent includes prior output (e.g. architect receives requirements from step 1; planner receives architecture).
- Phase advances correctly; persisted state survives across requests (reload and assert).

```bash
pytest tests/integration/test_orchestrator_state_transitions.py -v
```

### E2E with real LLM (Gemini)

Tests that call the real API are **skipped** when `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) is not set, so the full suite passes in CI without a key. With the key set, they run real agents and assert on state/messages.

Set `GEMINI_API_KEY` or `GOOGLE_API_KEY` in `.env`, then:

```bash
pytest tests/integration/test_orchestrator_agent_transitions.py tests/integration/test_orchestrator_e2e.py -v
```

- `test_e2e_orchestrator_transition_architecture_then_export` (in agent_transitions) and e2e tests in `test_orchestrator_e2e.py` use the real AgentRegistry and real Gemini-backed agents when the key is set; they are skipped otherwise.
- The rest of the suite (unit, agent transitions with mock state, state transition tests with fake registry) does **not** make API calls and is suitable for CI.

### Dev chat (manual E2E, full app + sub-agents)

Interactive loop with the orchestrator (in-memory state, no DB):

```bash
python -m scripts.dev_chat_orchestrator
```

Uses the same MasterOrchestrator and AgentRegistry as the full application (real sub-agents). Set `GEMINI_API_KEY` in `.env` so architect, mockup, and requirements agents can run; otherwise those tasks are skipped. Optional: `USE_LLM_INTENT=1` for LLM-based intent classification (default is rule-based).

### All orchestrator-related tests

```bash
pytest tests/unit/test_orchestrator_graph.py tests/unit/test_intent_classifier.py tests/unit/test_execution_planner.py tests/integration/test_orchestrator_agent_transitions.py tests/integration/test_orchestrator_e2e.py -v
```

---

## State flow

- **StateManager** loads/saves via a persistence adapter (e.g. InMemoryPersistenceAdapter). It has `load(session_id)`, `update(session_id, delta)`, and a `db` (adapter) plus `cache`.
- **ProjectState** (src.state.project_state) holds: session_id, current_phase, requirements, architecture, roadmap, mockups, conversation_history, etc.
- **state_delta** from each agent is merged (e.g. `requirements`, `architecture`, `roadmap`, `mockups`). Then phase is updated from PHASE_TRANSITION_MAP, conversation history is appended, and state is saved.

---

## Common issues

- **Tests fail with "No module named 'src'"** → Run pytest from project root; conftest.py adds project root to sys.path. Or `pip install -e .`
- **MockStateManager has no attribute 'update' / 'db'** → Unit tests need a mock that implements load, update, db.save, and cache (see test_orchestrator_graph.py).
- **Agent "skipped"** → Registry returns None when the agent fails to init (e.g. missing Gemini key). Check .env and that the agent’s dependencies are installed.
