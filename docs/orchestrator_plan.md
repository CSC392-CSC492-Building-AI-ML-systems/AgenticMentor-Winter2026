# Orchestrator Agent — Branches and Implementation Detail

Use **three branches** so the whole orchestrator works end-to-end. Base each on `develop` (or `project-architect-agent/initialization`). Merge Branch 1 before starting Branch 2; merge Branch 2 before starting Branch 3.

**Branch names (descriptive):**

- **Branch 1:** `orchestrator-agent/intent-plan-persistence` — classify + plan + persistence; no agents run.
- **Branch 2:** `orchestrator-agent/registry-and-execution` — registry, run agents, core loop, synthesis.
- **Branch 3:** `orchestrator-agent/downstream-phase-history` — downstream on change, phase, conversation history, docs/tests.

---

## Branch 1: `orchestrator-agent/intent-plan-persistence`

**Purpose:** Intent classification, execution plan model, planner, and persistence. No agent execution yet.

**Base:** `develop`

---

### 1.1 IntentClassifier — What and how

**What:** A class that takes the user’s message and current project phase and returns which intent (and which agents) should handle the request.

**Where:** `src/orchestrator/intent_classifier.py` (add the class; keep existing `INTENT_PATTERNS`).

**Output shape:** A small dataclass or TypedDict, e.g.:

```python
class IntentResult(TypedDict):
    primary_intent: str       # e.g. "requirements_gathering", "architecture_design"
    requires_agents: list[str]  # e.g. ["requirements_collector"] or ["project_architect"]
    confidence: float         # 0.0–1.0
```

**How — rule-based path:**

1. Normalize `user_input` (e.g. `.lower()`, strip).
2. For each intent in `INTENT_PATTERNS`:
   - Check if any `keywords` or `triggers` appear in `user_input`.
   - Check `phase_compatibility`: if it’s `["*"]` or if `project_state.current_phase` is in the list, the intent is allowed.
3. Pick the best match (e.g. most keyword hits, or first match). If none, return `primary_intent="unknown"`, `requires_agents=[]`, `confidence=0.0`.
4. Map intent → agent(s): e.g. `requirements_gathering` → `["requirements_collector"]`, `architecture_design` → `["project_architect"]`, `export` → `["exporter"]`. Use a fixed mapping dict or derive from AGENT_STORE later.

**How — LLM path (optional):**

1. Build a prompt: “User said: «user_input». Current phase: «phase». Available intents: requirements_gathering, architecture_design, mockup_creation, execution_planning, export. Which intent and which agents (by id) should handle this? Return JSON: primary_intent, requires_agents (list), confidence.”
2. Call LLM with structured output (e.g. Pydantic model or JSON mode); parse into `IntentResult`.
3. Optionally include AGENT_STORE descriptions in the prompt so the LLM can pick agent ids directly.

**Checklist:** [ ] Rule-based classify. [ ] Optional LLM classify. [ ] Return `IntentResult` (or equivalent).

---

### 1.2 Task and ExecutionPlan — What and how

**What:** Data structures that represent “run this agent with this context” and “an ordered list of such tasks.”

**Where:** New file `src/orchestrator/execution_plan.py` (or add to `execution_planner.py`).

**Task:**

```python
@dataclass
class Task:
    agent_id: str              # e.g. "project_architect"
    input: Any                 # optional override; often None (orchestrator builds from context + user_input)
    required_context: list[str]  # e.g. ["requirements", "architecture"] — state keys to extract
    tools: list[str]           # optional; e.g. ["generate_mermaid"] for architect
```

**ExecutionPlan:**

```python
@dataclass
class ExecutionPlan:
    tasks: list[Task]

    def add_task(self, agent_id: str, required_context: list[str], input: Any = None, tools: list[str] = None):
        self.tasks.append(Task(agent_id=agent_id, input=input, required_context=required_context or [], tools=tools or []))
```

**Checklist:** [ ] Define `Task`. [ ] Define `ExecutionPlan` with `add_task()`.

---

### 1.3 AGENT_STORE — What and how

**What:** A single list (or dict) that describes each agent: id, name, description, what it requires from state, what it produces, and which phases it’s allowed in.

**Where:** New file `src/orchestrator/agent_store.py` (or next to `execution_plan.py`).

**Shape (per entry):**

```python
AGENT_STORE = [
    {
        "id": "requirements_collector",
        "name": "Requirements Collector",
        "description": "Asks structured questions to gather goals, constraints, features. Updates requirements state.",
        "requires": [],
        "produces": ["requirements"],
        "phase_compatibility": ["initialization", "discovery", "*"],
    },
    {
        "id": "project_architect",
        "name": "Project Architect",
        "description": "Turns requirements into tech stack, system/ER diagrams, API and data model.",
        "requires": ["requirements"],
        "produces": ["architecture"],
        "phase_compatibility": ["requirements_complete", "architecture_complete"],
    },
    {
        "id": "execution_planner",
        "name": "Execution Planner Agent",
        "description": "Creates phases, milestones, and implementation steps from architecture.",
        "requires": ["architecture"],
        "produces": ["roadmap"],
        "phase_compatibility": ["architecture_complete"],
    },
    {
        "id": "mockup_agent",
        "name": "Mockup Agent",
        "description": "Generates UI wireframes and Figma-ready layouts.",
        "requires": ["requirements", "architecture"],
        "produces": ["mockups"],
        "phase_compatibility": ["requirements_complete"],
    },
    {
        "id": "exporter",
        "name": "Exporter",
        "description": "Bundles all artifacts into Markdown, PDF, or GitHub-ready docs.",
        "requires": ["*"],
        "produces": ["export"],
        "phase_compatibility": ["*"],
    },
]
```

**How:** Use as a constant or function that returns the list. The planner and (optionally) the intent classifier read from it to get `requires` and to map intent → agent ids.

**Checklist:** [ ] Define `AGENT_STORE` with all five agents. [ ] Use `requires` / `produces` in planner.

---

### 1.4 ExecutionPlanner.plan(intent, project_state) — What and how

**What:** Given the classified intent and current project state, produce an ordered list of tasks (which agents to run and with what `required_context`). Resolve dependencies: if the user asked for an agent whose `requires` are missing, prepend upstream agents.

**Where:** `src/orchestrator/execution_planner.py` (replace or extend the stub).

**How:**

1. **Intent → initial agent(s):** From `intent.requires_agents` (or from a mapping `primary_intent` → agent ids), get the list of agents the user is asking for (e.g. `["project_architect"]`).
2. **Dependency resolution:** For each requested agent, look up its `requires` in AGENT_STORE. For each required artifact (e.g. `requirements`), check if `project_state` has it (e.g. `state.requirements` and non-empty). If missing, find which agent **produces** that artifact and prepend it to the list (avoid duplicates and keep order). Repeat until the list is closed (e.g. requirements_collector has `requires=[]`, so it’s the root).
3. **Build ExecutionPlan:** For each agent id in the resolved list, get `required_context` from AGENT_STORE (`requires` for that agent). Add a `Task(agent_id=..., required_context=...)` to the plan. Order = dependency order (upstream first).
4. **Phase (optional):** If you want to enforce phase, filter out agents whose `phase_compatibility` doesn’t include `project_state.current_phase` (or `"*"`).

**Checklist:** [ ] Map intent → agent ids. [ ] Resolve dependencies (prepend upstream if requires missing). [ ] Build `ExecutionPlan` with correct `required_context` per task.

---

### 1.5 Persistence adapter — What and how

**What:** An async adapter so `StateManager` can load and save project state by `session_id`. No database required for Branch 1; in-memory (or file) is enough.

**Where:** e.g. `src/state/persistence.py` (extend or replace the placeholder) or `src/orchestrator/persistence_memory.py`.

**Interface:** `StateManager` calls:

- `await self.db.get(session_id)` → returns `dict | None` (state as a dict, or None if new session).
- `await self.db.save(session_id, state_dict)` → persists the dict.

So the adapter must implement:

```python
class InMemoryOrchestratorAdapter:
    def __init__(self):
        self._store: dict[str, dict] = {}

    async def get(self, session_id: str) -> dict | None:
        return self._store.get(session_id)

    async def save(self, session_id: str, state_dict: dict) -> None:
        self._store[session_id] = state_dict
```

**How:** Instantiate this (or a file-based version that reads/writes JSON per session_id). Pass it into `StateManager(adapter)`. No need to run agents yet; you only need to be able to load/save state in tests and later in the core loop.

**Checklist:** [ ] Implement async `get(session_id)` and `save(session_id, state_dict)`. [ ] Wire to `StateManager`.

---

### 1.6 Unit tests — What and how

**IntentClassifier:**

- Inputs: e.g. `("I want to build a task app", "initialization")` → expect `primary_intent="requirements_gathering"`, `requires_agents` containing `requirements_collector`.
- Inputs: e.g. `("generate the architecture", "requirements_complete")` → expect `architecture_design`, `project_architect`.
- Input with wrong phase or no match → expect `unknown` or fallback.

**ExecutionPlanner.plan():**

- Intent `architecture_design`, state with empty requirements → plan should have at least `requirements_collector` then `project_architect`.
- Intent `architecture_design`, state with requirements already set → plan can be just `project_architect`.
- Intent `export`, state with requirements + architecture → plan might be just `exporter` (and `required_context` for exporter includes full state or `["*"]`).

**Checklist:** [ ] Intent tests. [ ] Planner tests (with and without dependencies).

---

**Branch 1 merge when:** Intent classification and execution planning are testable in isolation; no agent is invoked; persistence can load/save state.

---

## Branch 2: `orchestrator-agent/registry-and-execution`

**Purpose:** Registry, context extraction, agent execution adapter, core loop, and response synthesis so one full request runs and updates state.

**Base:** `develop` (after Branch 1 merged)

---

### 2.1 Agent registry — What and how

**What:** A way to get an agent instance by `agent_id` (e.g. `"project_architect"`, `"requirements_collector"`). Other agents can be stubbed (return `None` or a no-op stub).

**Where:** e.g. `src/orchestrator/agent_registry.py` or inside `master_agent.py`.

**How:**

- Keep a dict or factory: `agent_id` → constructor or singleton. For `project_architect`, instantiate `ProjectArchitectAgent` (with LLM client from config if needed). For `requirements_collector`, instantiate `RequirementsAgent` (or get from existing `get_agent()` if it’s a singleton).
- `get_agent(agent_id: str) -> BaseAgent | Any | None`: return the instance or None so the orchestrator can skip unimplemented agents.
- Lazy init is fine (create on first `get_agent` call and cache).

**Checklist:** [ ] `get_agent(agent_id)` implemented. [ ] At least `requirements_collector` and `project_architect` registered and returning real agents.

---

### 2.2 _extract_context(project_state, required_context) — What and how

**What:** Given the current `ProjectState` (or its dict form) and a list of keys/paths (e.g. `["requirements", "architecture"]`), return a dict of those fragments. This is what the orchestrator passes as “context” when building each agent’s input.

**Where:** Method on `MasterOrchestrator` or a standalone helper in `src/orchestrator/`.

**How:**

- If `required_context` is `["*"]`, return the full state (e.g. `project_state.model_dump()` or a dict of top-level keys).
- Otherwise for each key in `required_context`:
  - If the key has no dot (e.g. `"requirements"`), get `getattr(project_state, key, None)` (or `project_state.model_dump()[key]`).
  - If the key has dots (e.g. `"architecture.tech_stack"`), traverse with getattr or dict lookup.
- Return a dict: `{ key: value for each key in required_context }`. Missing keys can be `None` or omitted.

**Checklist:** [ ] Support list of top-level keys. [ ] Support `"*"` for full state. [ ] Optionally support dotted paths.

---

### 2.3 Agent execution adapter — What and how

**What:** Turn a `Task` + extracted context + `user_input` into the actual call to the agent, and normalize the agent’s return value into a common shape: `state_delta` (dict) and `content` (or summary) for synthesis.

**Where:** Method(s) on `MasterOrchestrator` (e.g. `_run_agent(task, context, user_input)` or `_build_input_and_run`).

**How — build input per agent:**

- **project_architect:** Input = `{ "requirements": context.get("requirements"), "existing_architecture": context.get("architecture"), "user_request": user_input }`. If your architect expects `state` or a different shape, adapt (e.g. pass `requirements` from context and optional `existing_architecture` for selective regen).
- **requirements_collector:** Either `process_message(user_input, context.get("requirements"), context.get("conversation_history", []))` or `execute(input=user_input, context=context, tools=[])`. Match the agent’s actual API.
- **exporter (later):** Input = full context or `context` when `required_context` was `["*"]`.

**How — call agent:**

- If the agent has `process(input_data)`, call `await agent.process(input_data)`.
- If the agent has `execute(input, context, tools)`, call `await agent.execute(input, context, tools)`.
- Capture the raw result (dict or `AgentOutput`).

**How — normalize output:**

- Architect returns e.g. `{ "architecture": {...}, "state_delta": { "architecture": {...} }, "summary": "..." }`. Extract `state_delta`; if the agent only returns `architecture`, build `state_delta = { "architecture": result["architecture"] }`.
- Requirements collector may return a different shape; map it to `state_delta` (e.g. `{ "requirements": ... }`) and a short `content` or summary for the user.
- Return a small struct: `{ "state_delta": dict, "content": str or None }` so the core loop can call `StateManager.update(session_id, state_delta)` and pass `content` to the synthesizer.

**Checklist:** [ ] Build architect input from context + user_input. [ ] Build requirements input. [ ] Call agent (process or execute). [ ] Normalize to state_delta + content.

---

### 2.4 MasterOrchestrator.process_request(user_input, session_id) — What and how

**What:** The main entry point: load state, classify intent, build plan, run each task (extract context → run agent → update state), synthesize response, return a single response object.

**Where:** `src/orchestrator/master_agent.py` (replace the pseudocode).

**How (step by step):**

1. **Load state:** `project_state = await self.state_manager.load(session_id)`.
2. **Classify intent:** `intent = self.intent_classifier.analyze(user_input, project_state)` (or `analyze(user_input, project_state.current_phase)` if your classifier only needs phase).
3. **Build plan:** `plan = self.execution_planner.plan(intent, project_state)`.
4. **Loop over plan.tasks:**  
   For each task:  
   a. `agent = self.registry.get_agent(task.agent_id)`; if None, skip.  
   b. `context = self._extract_context(project_state, task.required_context)`.  
   c. Run agent via adapter: `result = await self._run_agent(task, context, user_input)` (or inline the adapter logic).  
   d. `state_delta = result["state_delta"]`. If non-empty, `project_state = await self.state_manager.update(session_id, state_delta)` (and optionally re-read into a local variable so the next task sees updated state).  
   e. Append `result` to a list `results`.
5. **Synthesize:** `message = self._synthesize_response(results)`.
6. **Return:** `{ "message": message, "state_snapshot": project_state.model_dump() or current state dict, "artifacts": [...] }` as needed by the API.

**Checklist:** [ ] Load → classify → plan → for each task: get agent, extract context, run, update state. [ ] Pass updated state into next task. [ ] Synthesize and return.

---

### 2.5 _synthesize_response(results) — What and how

**What:** Turn the list of agent results (each with `content` or summary) into one user-facing string (e.g. “Architecture generated.” or “Requirements updated. Here’s a summary: …”).

**How:** Concatenate short summaries from each result, or pick the “main” one (e.g. the last agent’s content). If an agent returned a `summary` field, use that. Keep it short (one or two sentences) so the UI can show it; optional link to artifacts or “view architecture in the artifact panel.”

**Checklist:** [ ] Implement; return a single string.

---

### 2.6 Integration test — What and how

**What:** One end-to-end test: create a session, seed state (e.g. minimal requirements), send one message (e.g. “generate architecture”), run the orchestrator, assert response and that state now has architecture (and optionally that requirements are unchanged).

**Where:** e.g. `tests/integration/test_orchestrator.py` or under `tests/orchestrator/`.

**How:** Use in-memory persistence; create session_id; optionally call `StateManager.update(session_id, { "requirements": {...} })` to seed; call `orchestrator.process_request("generate architecture", session_id)`; load state again and assert `state.architecture` is present and non-empty; assert `response["message"]` is non-empty.

**Checklist:** [ ] One E2E test that runs orchestrator and asserts state update.

---

**Branch 2 merge when:** A single user message runs through the orchestrator and updates state; integration test passes.

---

## Branch 3: `orchestrator-agent/downstream-phase-history`

**Purpose:** When the user asks to change something, run downstream agents so dependent artifacts stay in sync; add phase transitions, conversation history, and docs/tests.

**Base:** `develop` (after Branch 2 merged)

---

### 3.1 Downstream dependency resolution — What and how

**What:** When the execution plan includes an agent that **produces** an artifact (e.g. `project_architect` produces `architecture`), append any agents that **require** that artifact so they re-run with the new data (e.g. execution_planner agent, exporter).

**Where:** Inside `ExecutionPlanner.plan()` or a post-step in the orchestrator that “expands” the plan.

**How:**

- After building the initial list of tasks from intent (and upstream dependency resolution), determine which artifacts will be **modified** this turn. E.g. if `project_architect` is in the plan, then `architecture` will be updated.
- For each artifact that will be modified, find all agents in AGENT_STORE whose `requires` include that artifact (e.g. `execution_planner` requires `architecture`). Append those agents to the task list if not already present, in dependency order (e.g. execution_planner before exporter if exporter needs roadmap).
- Avoid duplicates and keep a valid topological order (any agent that produces X runs before any agent that requires X).

**Checklist:** [ ] After building plan, find “artifacts modified” by this plan. [ ] Find agents that require those artifacts; append to plan in order.

---

### 3.2 Phase transitions — What and how

**What:** Update `project_state.current_phase` after certain intents or agent runs (e.g. after requirements_collector marks requirements complete → `requirements_complete`; after architect runs → `architecture_complete`), and persist it.

**Where:** In the orchestrator core loop, after running an agent (or after the full plan). Alternatively in the execution adapter when a specific agent reports “complete.”

**How:**

- Define a small mapping: intent or agent_id → suggested next phase (e.g. `requirements_gathering` + requirements complete → `requirements_complete`; after `project_architect` runs → `architecture_complete`).
- After each agent run (or at end of plan), if the intent or the agent suggests a phase transition, call `StateManager.update(session_id, { "current_phase": "requirements_complete" })` (or similar). Use the same delta mechanism so it’s persisted.

**Checklist:** [ ] Map intent/agent to next phase. [ ] Call update with current_phase when appropriate.

---

### 3.3 Conversation history — What and how

**What:** Append the user message and the orchestrator’s synthesized response to `project_state.conversation_history` (or equivalent) so future turns can use it (e.g. for requirements collector or for context).

**Where:** In `process_request`, after synthesizing the response and before returning.

**How:**

- Build two entries: e.g. `{ "role": "user", "content": user_input }` and `{ "role": "assistant", "content": message }`.
- Call `StateManager.update(session_id, { "conversation_history": existing_list + [user_msg, assistant_msg] })`. If your state model uses a list and `_apply_delta` appends, ensure you’re not duplicating; otherwise read state, append, and update with the full new list (if your merge logic supports that).

**Checklist:** [ ] Append user and assistant messages to conversation_history. [ ] Persist via StateManager.update.

---

### 3.4 Tests — What and how

**What:** An integration test that a “change” request (e.g. “change the backend to Node.js”) runs the architect and then the execution planner agent (if implemented), and state has updated architecture and optionally updated roadmap.

**How:** Seed state with requirements and architecture; call `process_request("change the backend to Node.js", session_id)`; assert state.architecture reflects the change; if execution_planner agent is implemented, assert state.roadmap or similar is updated.

**Checklist:** [ ] Test change request → architect + downstream; assert state.

---

### 3.5 Documentation — What and how

**What:** A short doc that describes the orchestrator flow, intent → agent mapping, agent store, dependency resolution, and how to add new intents/agents.

**Where:** `docs/orchestrator-agent.md` (or a section in `docs/project-info.md`).

**Contents (suggested):**

- High-level flow: load state → classify intent → build plan (with upstream and downstream resolution) → run tasks (extract context, run agent, update state) → synthesize response.
- Table or list: intent → agents; agent id → requires, produces.
- How to add a new intent (add pattern or LLM prompt; add mapping to agents).
- How to add a new agent (add to AGENT_STORE; register in registry; implement adapter input/output for that agent).

**Checklist:** [ ] Doc added/updated with flow, mapping, and extension guide.

---

**Branch 3 merge when:** Downstream resolution works, phase and conversation history are updated, tests and docs are in place.

---

## Summary table

| Branch | Base | Merge when |
|--------|------|------------|
| `orchestrator-agent/intent-plan-persistence` | develop | Intent + plan + persistence + unit tests; no agent runs. |
| `orchestrator-agent/registry-and-execution` | develop (after Branch 1) | Full request runs and updates state; integration test passes. |
| `orchestrator-agent/downstream-phase-history` | develop (after Branch 2) | Downstream on change, phase, history, docs, tests. |

After all three are merged, the orchestrator works end-to-end: user message → intent (rule or LLM) → plan (with dependency resolution) → run agents in order (context from state, state updated from outputs) → synthesize response; and when the user changes something, dependent agents are re-run so the plan stays consistent.

---

## Agent continuity, UI visibility, and agent selection mode (design)

These behaviors are **not** fully covered by the three branches above. Add them in Branch 3 or a small follow-up so the frontend and multi-turn flows work as expected.

### 1. Two modes: Auto vs Manual agent selection

**Requirement:** The user can choose between:

- **Auto** — The orchestrator **auto-detects** which agent(s) to run from the user’s message (intent classification → plan → run). Default behavior.
- **Manual** — The user turns off auto and **selects** which agent to talk to. The UI shows only **appropriate and available** agents (based on dependencies and phase); the orchestrator runs only the selected agent (plus any required upstream).

**Why this helps:** In manual mode there is no “agent replaced mid-task” from re-classification — the user explicitly chose that agent. In auto mode, the current intent-based flow applies.

### 2. Available agents (for manual mode)

When the user is in **manual** mode, the frontend must show a list of agents they **can** select. Availability is driven by **dependencies** (and optionally phase):

- For each agent in AGENT_STORE, the agent is **available** if:
  - **Phase:** `project_state.current_phase` is in that agent’s `phase_compatibility` (or compatibility is `["*"]`).
  - **Dependencies:** For each key in the agent’s `requires`, the project state has that artifact present and non-empty (e.g. `requirements` filled for project_architect).
- Example: If there are no requirements yet, only `requirements_collector` (and maybe `exporter` if it has `requires: ["*"]`) might be available; `project_architect` becomes available once requirements exist.

**API:** Expose a way for the frontend to get the list of available agents for the current session, e.g.:

- **Option A:** Include in every chat response: `"available_agents": [ { "id": "requirements_collector", "name": "Requirements Collector" }, ... ]` (only those that pass phase + dependency checks).
- **Option B:** Separate endpoint, e.g. `GET /sessions/{session_id}/available-agents`, returning the same list.

The frontend uses this list to render the manual agent selector (dropdown, cards, etc.) and only allows choosing from these agents.

### 3. State and request shape for Auto vs Manual

- **State (or session prefs):**
  - `agent_selection_mode: "auto" | "manual"` — which mode the user is in.
  - `selected_agent_id: str | None` — when mode is `"manual"`, which agent the user chose (null if they haven’t picked yet or just switched to manual).
- **Request:** Chat request body can include:
  - `agent_selection_mode: "auto" | "manual"` (optional; if omitted, use value from state).
  - `selected_agent_id: "requirements_collector" | null` (when in manual mode; when in auto, ignore).
- **Orchestrator behavior:**
  - **Auto:** Ignore `selected_agent_id`. Classify intent → build plan (with dependency resolution) → run plan. Same as today.
  - **Manual:** Do **not** classify intent for routing. Build a plan that runs **only** the `selected_agent_id` (and prepend any upstream agents whose outputs that agent’s `requires` need, if not already in state). Run that plan. If `selected_agent_id` is null (e.g. user just switched to manual), return a message like “Choose an agent” and include `available_agents`; do not run any agent.

**Checklist (Branch 3 or follow-up):** [ ] Add `agent_selection_mode` and `selected_agent_id` to state/request. [ ] Implement “available agents” (phase + dependency check). [ ] Expose `available_agents` in response or dedicated endpoint. [ ] When mode is manual, plan = selected agent (+ required upstream only). [ ] Frontend: Auto/Manual toggle and selector of available agents when manual.

### 4. Agents being “replaced” mid-task (auto mode)

**Problem:** In **auto** mode, each turn re-classifies intent, so the user can be mid–requirements flow and the next message might route elsewhere (“replaced” mid-task).

**Approach:** In **manual** mode this is avoided because the user explicitly chose the agent. In auto mode you can optionally add a “continuation” hint (e.g. `last_agent_id` + prefer same agent when confidence is low and flow is incomplete); see optional refinement in docs. The two-mode design already gives users a way to stay with one agent by switching to manual and selecting that agent.

### 5. UI: show which agent is working and what they returned

**Current gap:** The planned return shape is `{ "message", "state_snapshot", "artifacts" }`. That does **not** expose which agents ran or what each agent returned, so the UI cannot show “Requirements Collector returned: …” or “Project Architect returned: …”.

**Execution plan:** The `ExecutionPlan` is internal (list of `Task`s). It is not returned to the client. The core loop keeps a `results` list (state_delta + content per run) but does not attach agent identity in the response.

**Changes to support the UI:**

- **Response shape:** Extend the return value of `process_request` to include a list of per-agent results, for example:

  ```python
  # In addition to message, state_snapshot, artifacts (and when implemented: available_agents):
  "agent_results": [
      {
          "agent_id": "requirements_collector",
          "agent_name": "Requirements Collector",
          "content": "Here are the next questions...",
          "state_delta_keys": ["requirements"],
          "status": "completed"
      },
      {
          "agent_id": "project_architect",
          "agent_name": "Project Architect",
          "content": "Architecture generated.",
          "state_delta_keys": ["architecture"],
          "status": "completed"
      }
  ]
  ```

  Build this list in the core loop: for each task run, append `{ agent_id, agent_name, content, state_delta_keys, status }` (agent_id/name from the task and AGENT_STORE; content from the normalized adapter output; state_delta_keys from the keys of the applied delta).

- **“Currently working”:** With a single synchronous HTTP request, the backend only sends one response after **all** tasks finish. So the UI cannot show “Agent X is working” in real time unless you add:
  - **Streaming (SSE/WebSocket):** Before running each task, emit “agent_started: requirements_collector”; after each task, emit “agent_completed: requirements_collector” and the snippet for that agent. Then the frontend can show a live “Requirements Collector is working” and “Requirements Collector returned: …”.
  - **Without streaming:** The frontend can only show a generic “Processing…” until the response arrives; then it can show “What ran” and “What they returned” from `agent_results`.

**Checklist (Branch 3 or follow-up):** [ ] Add `agent_results` to the response. [ ] Optionally add streaming events for “agent started” / “agent completed” if the UI needs live “who is working.”