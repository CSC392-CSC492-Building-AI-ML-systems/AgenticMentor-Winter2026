# Orchestrator Cleanup Plan – General Inquiry + Req→Exporter Flow

**Status:** Task A, Task B, variable agents, and LLM-first orchestrator implemented.

- **Variable agents:** Number of agents per turn is decided by the intent classifier (LLM when configured): `requires_agents` can be 0 (unknown), 1 (single step then pause), or 2+ (run those in one turn then pause). No fixed "compound only" logic.
- **LLM-first:** (1) Intent: LLM prompt asks for variable-length `requires_agents` and judgment. (2) General inquiry: when intent is unknown, orchestrator uses LLM to generate a contextual reply (fallback: deterministic summary). (3) Multi-agent message: when 2+ agents run in one turn, LLM synthesizes one coherent message (fallback: `_synthesize_response`).

This plan addresses the two items from the orchestrator team after DB integration:

1. **General inquiries** → Orchestrator answers from context (no agent run).
2. **Smooth flow** from Requirements Collector through to Exporter (no skipping, no overwriting agent output).

Both items are **valid**. Evidence and implementation steps are below.

---

## 1. General inquiry → Orchestrator answers from context

### Validity

- **Current behavior:** When intent is `unknown` (chit-chat, unclear, or general question), `ExecutionPlanner.plan()` still builds a plan with `agent_ids = ["requirements_collector"]` (see `execution_planner.py` ~124–127). So we run the requirements collector instead of answering from context.
- **Desired behavior:** For general inquiries, **do not run any agent**. Have the orchestrator produce a short reply from loaded `project_state` (and optionally recent conversation), e.g. “Here’s where we are: … Say ‘continue’ for the next step or ask to change something.”

### Implementation steps

| Step | Action | Where |
|------|--------|--------|
| 1.1 | **Short-circuit when intent is `unknown`:** In `MasterOrchestrator.process_request()`, after `graph_result` is computed, if `intent.get("primary_intent") == "unknown"` (and optionally low confidence), **do not build/run a plan**. Instead: load `project_state`, build a short contextual message (phase, what’s complete, what’s next), set `message` to that, and return early with empty `plan` and no agent execution. | `src/orchestrator/master_agent.py` |
| 1.2 | **Optional:** Add a small helper, e.g. `_build_general_inquiry_response(project_state, user_input)`, that summarizes current phase, deliverables present, and suggests “continue” or “change X”. Keep it deterministic or use a very short LLM call; avoid running any specialist agent. | Same file or a small `orchestrator/response_builder` module |
| 1.3 | **Tests:** Add a test that when intent is `unknown`, no agent is invoked and the response is a contextual summary (no requirements_collector run). | `tests/unit/` or `tests/integration/` |

### Design note

- The graph can stay as-is (classify → build_plan). The change is in `process_request()`: after `graph_result`, if intent is `unknown`, skip the “run plan” block and use the new response path.

---

## 2. Smooth flow Req → Architect → Planner → Mockup → Exporter

### Validity

- **DB team:** Manual flow (Collector → Architect → Planner → Mockup → Exporter) works when agents are called explicitly; issues are in **automatic hand-off** (skipping, empty data, overwriting).
- **Method naming:** Orchestrator already handles differences: `requirements_collector` uses `process_message()`, others use `process()` or `execute()`. No change required for method names; the real issues are (a) when we show a **summary instead of the agent’s actual reply**, and (b) ensuring **state is committed before the next agent** (DB layer must await writes; orchestrator already awaits `state.update()` after each agent).

### Sub-issues and fixes

#### 2.1 Orchestrator overwriting agent output (e.g. requirements_collector’s questions)

- **Current behavior:** In auto mode, after a single successful step we always set `message = summary_text` from `_summarize_single_step()` (see `master_agent.py` ~338–365). So the user sees the orchestrator’s summary (e.g. “I have 5 features…”) instead of the agent’s real content (e.g. the collector’s next questions).
- **Desired behavior:** For **conversational** agents (e.g. `requirements_collector`), the user-facing message should be the **agent’s content** when present. Use the summary only when content is empty or when we explicitly want a checkpoint summary (e.g. after architect/planner/mockup).

| Step | Action | Where |
|------|--------|--------|
| 2.1.1 | In the auto-mode success path, when setting `message`: if `executed.get("agent_id") == "requirements_collector"` and `executed.get("content")` is non-empty, set `message = executed["content"]` (and optionally append a one-line “Say ‘continue’ when ready” if there’s a `next_agent_id`). | `master_agent.py` (~365) |
| 2.1.2 | Optionally generalize: for any agent with `interaction_mode == "conversational"` (from `AGENT_STORE`), prefer `executed.get("content")` over `summary_text` when content is non-empty. | Same place + `agent_store.py` (already has `interaction_mode`) |
| 2.1.3 | **Tests:** Assert that after a requirements_collector step in auto mode, the returned `message` contains the collector’s reply (e.g. questions) and not only a generic “I have N features” summary. | `tests/integration/` or `tests/unit/` |

#### 2.2 Skipping / empty data (agents not running or seeing stale state)

- **Causes (from DB team):** (1) Method/init mismatches – already handled per-agent in `_run_agent` and registry. (2) Architect/Mockup need `state_manager` in init – **already done** in `AgentRegistry._create_agent()`. (3) Commit timing – next agent must see committed state.
- **Orchestrator responsibility:** We already do `project_state = await self.state.update(session_id, state_delta)` after each agent. No change needed **unless** the state manager’s `update()` does not await the DB write. If Supabase persistence is async, ensure `StateManager.update()` (or equivalent) **awaits** the write before resolving.
- **Action:** Confirm with DB team that `state.update()` is awaited and completes before returning. If not, fix in persistence layer; orchestrator keeps awaiting `update()`.

#### 2.3 Flow order and phase transitions

- **Current:** `AUTO_FLOW_SEQUENCE` and `PHASE_TRANSITION_MAP` already define req → architect → planner → mockup → exporter. Execution planner’s `_resolve_upstream` / `_resolve_downstream` handle dependencies.
- **Action:** Add or run an **integration test** that runs the full auto flow (one turn per agent, e.g. “continue” or minimal prompts) and asserts: each agent runs in order, state_deltas are applied, and phase advances (e.g. `requirements_complete` → `architecture_complete` → …). This guards against regressions and validates hand-off with real state_manager (in-memory or test DB).

---

## 3. Order of work (recommended)

1. **General inquiry (1.1–1.3)** – Small, clear change; unblocks “orchestrator answers from context” without touching agent chain.
2. **Don’t overwrite conversational agent output (2.1.1–2.1.3)** – Fixes the “5 features” vs actual questions issue; minimal code, high impact.
3. **Commit timing (2.2)** – Verify with DB team; fix in persistence if needed.
4. **E2E flow test (2.3)** – Protects the full req→exporter flow after merges.

---

## 4. Out of scope for this plan

- **DB schema / conversation_messages:** Handled by DB team; orchestrator just keeps appending to conversation and state as it does today.
- **Unifying all agents to `.process()` or `._generate()`:** Not required for this cleanup; orchestrator already branches per agent in `_run_agent`. Standardizing agent interfaces can be a separate refactor.
- **Manual flow:** Already working per DB team; no change needed for manual mode.

---

## 5. References

- `src/orchestrator/master_agent.py` – `process_request`, `_run_agent`, `_summarize_single_step`, auto-mode message assignment.
- `src/orchestrator/execution_planner.py` – `plan()`, unknown intent → `requirements_collector`.
- `src/orchestrator/agent_registry.py` – Agent creation with `state_manager` for architect/mockup/planner.
- `src/orchestrator/agent_store.py` – `AGENT_STORE`, `interaction_mode`, `FULL_PIPELINE_AGENT_IDS`.
- DB team: `tests/db/test_manual_orchestration.py` (if present on their branch) for reference on individual agent calls and state hand-offs.
