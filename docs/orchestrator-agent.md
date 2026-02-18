# Orchestrator Agent

The **Master Orchestrator** is the central coordinator of AgenticMentor. It receives every user message, classifies intent, builds an execution plan, runs the appropriate specialist agents in dependency order, persists state, and returns a structured response.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Full Request Flow](#full-request-flow)
3. [Intent → Agent Mapping](#intent--agent-mapping)
4. [Agent Store](#agent-store)
5. [Dependency Resolution](#dependency-resolution)
6. [Phase Transitions](#phase-transitions)
7. [Conversation History](#conversation-history)
8. [Auto / Manual Agent Selection](#auto--manual-agent-selection)
9. [Response Shape](#response-shape)
10. [Extending the Orchestrator](#extending-the-orchestrator)

---

## Architecture Overview

```
User Request
     │
     ▼
┌─────────────────────────────────────────┐
│           MasterOrchestrator            │
│                                         │
│  LangGraph Flow:                        │
│    load_state → classify_intent         │
│             → build_plan               │
│                                         │
│  Agent Loop:                            │
│    for task in plan.tasks:              │
│      agent = AgentRegistry.get_agent()  │
│      result = _run_agent()              │
│      StateManager.update()              │
│      PHASE_TRANSITION_MAP check         │
│                                         │
│  Post-loop:                             │
│    conversation_history persisted       │
│    response synthesized                 │
└─────────────────────────────────────────┘
     │
     ▼
Structured Response
```

**Key components:**

| Component | File | Responsibility |
|---|---|---|
| `MasterOrchestrator` | `src/orchestrator/master_agent.py` | Coordinates the full request lifecycle |
| `IntentClassifier` | `src/orchestrator/intent_classifier.py` | Rule-based or LLM-powered intent detection |
| `ExecutionPlanner` | `src/orchestrator/execution_planner.py` | Builds ordered task list with upstream + downstream deps |
| `AgentRegistry` | `src/orchestrator/agent_registry.py` | Lazy-loads and caches agent instances |
| `AGENT_STORE` | `src/orchestrator/agent_store.py` | Static metadata for all agents |
| `StateManager` | `src/state/state_manager.py` | Atomic state load/update with in-memory cache |
| `ProjectState` | `src/state/project_state.py` | Pydantic model — single source of truth |

---

## Full Request Flow

### Auto Mode (default)

```
process_request(user_input, session_id)
  │
  ├─ 1. LangGraph: load_state(session_id)
  │        └─ StateManager.load() → ProjectState
  │
  ├─ 2. LangGraph: classify_intent(user_input, current_phase)
  │        └─ IntentClassifier.analyze_async()
  │             ├─ LLM path (if Gemini key set): structured output via LangChain
  │             └─ Rule-based path (fallback): keyword + phase matching
  │
  ├─ 3. LangGraph: build_plan(intent, project_state)
  │        └─ ExecutionPlanner.plan()
  │             ├─ _resolve_upstream()   — prepend missing dependency agents
  │             └─ _resolve_downstream() — append agents that need new artifacts
  │
  ├─ 4. Agent loop (for each task in plan):
  │        ├─ AgentRegistry.get_agent(agent_id)
  │        ├─ _extract_context(project_state, required_context)
  │        ├─ _run_agent(task, context, user_input, agent)
  │        ├─ StateManager.update(session_id, state_delta)
  │        └─ PHASE_TRANSITION_MAP → StateManager.update(current_phase)
  │
  ├─ 5. _synthesize_response(results) → message string
  │
  └─ 6. Persist conversation_history (user + assistant turns)
         └─ db.save() + cache update
```

### Manual Mode

When `agent_selection_mode="manual"` and `selected_agent_id` is provided, steps 1–3 are replaced:

```
process_request(..., agent_selection_mode="manual", selected_agent_id="project_architect")
  │
  ├─ StateManager.load(session_id)
  ├─ _resolve_upstream([selected_agent_id], project_state)  ← upstream deps only
  ├─ Build ExecutionPlan directly (no graph, no downstream expansion)
  ├─ Persist {agent_selection_mode, selected_agent_id} to state
  └─ Continue at step 4 (agent loop) as normal
```

---

## Intent → Agent Mapping

| User Intent | `primary_intent` | Agents Triggered |
|---|---|---|
| Describing goals, features, constraints | `requirements_gathering` | `requirements_collector` |
| Asking for tech stack, diagrams, APIs | `architecture_design` | `project_architect` |
| Asking for UI, wireframes, screens | `mockup_creation` | `mockup_agent` |
| Asking for roadmap, timeline, milestones | `execution_planning` | `execution_planner` |
| Asking to export, download, generate docs | `export` | `exporter` |
| Unrecognised | `unknown` | Full pipeline |

Intent classification uses **keyword + phase matching** by default. When a Gemini API key is configured, it uses **LangChain structured output** (`ChatGoogleGenerativeAI.with_structured_output`) for higher accuracy.

---

## Agent Store

All agents are defined in `AGENT_STORE` (`src/orchestrator/agent_store.py`). This is the single source of truth for dependency resolution and the UI agent picker.

| Agent ID | Name | Requires | Produces | Phase Compatibility |
|---|---|---|---|---|
| `requirements_collector` | Requirements Collector | — | `requirements` | `initialization`, `discovery`, `*` |
| `project_architect` | Project Architect | `requirements` | `architecture` | `requirements_complete`, `architecture_complete` |
| `execution_planner` | Execution Planner Agent | `architecture` | `roadmap` | `architecture_complete` |
| `mockup_agent` | Mockup Agent | `requirements`, `architecture` | `mockups` | `requirements_complete` |
| `exporter` | Exporter | `*` (all) | `export` | `*` |

---

## Dependency Resolution

`ExecutionPlanner.plan()` runs two passes:

### Upstream (`_resolve_upstream`)

Ensures all artifacts an agent *requires* are produced before it runs. If `project_architect` is requested but `requirements` is missing from state, `requirements_collector` is prepended automatically.

### Downstream (`_resolve_downstream`)

After building the upstream-resolved list, finds all agents whose `requires` overlap with artifacts *produced* by the current plan and appends them. Repeats until stable (handles chains).

**Example:** User asks for architecture → `project_architect` is planned → it produces `architecture` → `execution_planner` requires `architecture` → `execution_planner` is automatically appended.

> **Note:** Agents with `requires: ["*"]` (exporter) are excluded from auto-downstream expansion.

---

## Phase Transitions

After each agent completes, `PHASE_TRANSITION_MAP` is checked and `current_phase` is updated atomically:

| Agent | → Phase |
|---|---|
| `requirements_collector` | `requirements_complete` |
| `project_architect` | `architecture_complete` |
| `execution_planner` | `planning_complete` |
| `mockup_agent` | `design_complete` |
| `exporter` | `exportable` |

Full lifecycle: `initialization → discovery → requirements_complete → architecture_complete → planning_complete → design_complete → exportable`

---

## Conversation History

At the end of every `process_request` call (happy path only), two entries are appended to `ProjectState.conversation_history`:

```python
{"role": "user",      "content": user_input}
{"role": "assistant", "content": synthesized_message}
```

History is persisted by writing directly to `db.save()` and updating the in-memory cache — bypassing `StateManager`'s list-extend merge to prevent duplicate entries across turns.

---

## Auto / Manual Agent Selection

### Auto (default)

Standard flow: intent classification → execution planning → agent loop.

```python
response = await orchestrator.process_request(
    "Design the architecture",
    session_id,
)
```

### Manual

Bypasses intent classification and downstream expansion. Only the selected agent and its upstream dependencies run. Useful for UI-driven "run this agent now" buttons.

```python
response = await orchestrator.process_request(
    "Re-run architect",
    session_id,
    agent_selection_mode="manual",
    selected_agent_id="project_architect",
)
```

The selection is persisted to `ProjectState.agent_selection_mode` and `ProjectState.selected_agent_id`.

---

## Response Shape

Every `process_request` call returns:

```python
{
    "message": str,                  # synthesized user-facing response
    "state_snapshot": dict,          # full ProjectState.model_dump()
    "artifacts": list[dict],         # raw agent results (legacy, use agent_results)
    "intent": dict,                  # {primary_intent, requires_agents, confidence}
    "plan": ExecutionPlan,           # the plan that was executed
    "project_state": ProjectState,   # live ProjectState object
    "agent_results": list[dict],     # per-agent: {agent_id, agent_name, status, content, state_delta_keys}
    "available_agents": list[dict],  # all AGENT_STORE agents: {agent_id, agent_name, description, phase_compatibility}
}
```

**`agent_results` status values:**

| Status | Meaning |
|---|---|
| `"success"` | Agent ran and returned a result |
| `"skipped"` | `AgentRegistry.get_agent()` returned `None` (not yet implemented) |
| `"error"` | `_run_agent()` raised an exception |

---

## Extending the Orchestrator

### Adding a new agent

**1. Register in `AGENT_STORE`** (`src/orchestrator/agent_store.py`):

```python
{
    "id": "my_new_agent",
    "name": "My New Agent",
    "description": "What it does.",
    "requires": ["architecture"],      # artifacts it needs
    "produces": ["my_artifact"],       # artifacts it creates
    "phase_compatibility": ["architecture_complete"],
}
```

**2. Add a phase transition** (`src/orchestrator/master_agent.py`):

```python
PHASE_TRANSITION_MAP: dict[str, str] = {
    ...
    "my_new_agent": "my_phase_complete",
}
```

**3. Wire the agent class** in `AgentRegistry._create_agent`:

```python
if agent_id == "my_new_agent":
    from src.agents.my_new_agent import MyNewAgent
    return MyNewAgent(state_manager=self._state_manager)
```

**4. Add an adapter branch** in `MasterOrchestrator._run_agent`:

```python
if agent_id == "my_new_agent":
    raw = await agent.process({"architecture": context.get("architecture"), "user_request": user_input})
    return {"state_delta": raw.get("state_delta") or {}, "content": raw.get("summary") or ""}
```

**5. Add intent mapping** in `intent_classifier.py` if the agent has a new intent:

```python
INTENT_PATTERNS["my_intent"] = {
    "keywords": ["keyword1", "keyword2"],
    "phase_compatibility": ["architecture_complete"],
    "triggers": ["trigger phrase"],
}
INTENT_TO_AGENTS["my_intent"] = ["my_new_agent"]
```

Downstream resolution, phase transitions, conversation history, `agent_results`, and `available_agents` all work automatically once the agent is in `AGENT_STORE`.
