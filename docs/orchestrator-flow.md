# Orchestrator flow: from your prompt to the result

This document describes what happens when you send a message to the dev orchestrator (`python scripts/dev_chat_orchestrator.py`) and how you get a reply back.

---

## 1. Entry point: dev chat

- You run: `python scripts/dev_chat_orchestrator.py`
- The script creates:
  - **InMemoryPersistenceAdapter** (no database)
  - **StateManager** on top of it
  - **MasterOrchestrator** with that state manager and an **AgentRegistry** (real agents)
- A fixed **session_id** is used: `"dev-cli-session"`
- In a loop it:
  - Reads your line as `user_input`
  - Calls `orchestrator.process_request(user_input, session_id)` (auto mode; no manual agent selection)
  - Prints `response["message"]` as **Bot:** and lists **Agent results** (agent_id and status)

So: your prompt is the `user_input`; the “result” you see is the **message** and **agent_results** from that single `process_request` call.

---

## 2. Inside `process_request` (auto mode)

High level: **load state → run graph (classify intent, build plan) → run plan (execute agents) → update state and history → build one message and return.**

---

### Step A – Load state and run the graph

**Load state**

- `state_manager.load(session_id)` loads (or creates) **project_state** for `"dev-cli-session"`: requirements, architecture, roadmap, mockups, `current_phase`, `conversation_history`, etc.

**Graph run**

- `_graph.ainvoke({"user_input": user_input, "session_id": session_id})` runs the LangGraph with three nodes:

**1. load_state**

- Loads project state (or a new session).
- Writes `project_state` (and any error) into graph state.

**2. classify_intent**

- Inputs: `user_input`, `current_phase`, `conversation_history`.
- Calls **IntentClassifier** (rule-based by default, or LLM if `USE_LLM_INTENT=1`).
- Produces **intent**: e.g. `primary_intent`, `requires_agents`, `confidence`, `expand_downstream`.
- **Export override:** if the current message clearly asks for PDF/Markdown/download, the classifier result can be overridden so the exporter runs.

**3. build_plan**

- **ExecutionPlanner** takes intent + project_state.
- If intent is unknown or empty → plan is only **requirements_collector** (cheap path; no full pipeline).
- Otherwise: resolves **required agents** (from `requires_agents`) plus **upstream** dependencies, and optionally **downstream** (if `expand_downstream`).
- Produces an **ExecutionPlan**: ordered list of **Tasks** (each with `agent_id` and `required_context`).

Graph result = `project_state`, **intent**, **plan** (and possibly error). **available_agents** is computed from `project_state` (readiness: phase + unmet_requires).

---

### Step B – Execute the plan (run agents)

For **each task** in the plan, in order:

1. **Blocked?** If required upstream artifacts are missing (e.g. a previous agent failed or was skipped), this task is **not run**; it is recorded as `blocked_dependency` in **agent_results**.
2. **Get agent:** `registry.get_agent(task.agent_id)` (requirements_collector, project_architect, execution_planner, mockup_agent, exporter). If the registry returns `None` → **skipped_unavailable** and continue.
3. **Build context:** `_extract_context(project_state, task.required_context)` — pulls requirements, architecture, roadmap, conversation_history, etc. as needed for that agent.
4. **Run agent:** `_run_agent(task, context, user_input, agent, project_state)`:
   - Wraps the call in **asyncio.wait_for** with **AGENT_TIMEOUT_SECONDS** for that agent.
   - Calls the agent’s API (e.g. `process_message` for requirements, `process` for architect/planner/mockup, `execute` or `process` for exporter) with **user_input** and **context**.
5. The agent returns something like `{ state_delta, content/summary }`. **state_delta** (e.g. `requirements`, `architecture`, `roadmap`, `mockups`, `export_artifacts`) is applied via **state_manager.update(session_id, state_delta)**; **project_state** is updated in memory and (in dev) written back to the in-memory store.
6. **Phase transition:** If this agent has a phase transition (e.g. requirements_collector → requirements_complete), **current_phase** is updated.
7. One entry is appended to **agent_results** (e.g. success with `content` and `state_delta_keys`, or failed_timeout / failed_runtime with error info). If the agent failed or timed out, its “produces” artifacts are added to **blocked_artifacts** so downstream tasks can be marked **blocked_dependency** instead of run.

So: your prompt plus current state drive a **sequence of agent calls**; each agent can **change project state** and produce **content**; the orchestrator collects **results** and **agent_results**.

---

### Step C – Build one message and persist

**Message**

- `_synthesize_response(results, agent_results)` builds the single reply you see:
  - Takes each successful agent’s **content** (or summary).
  - Truncates long content (e.g. 500 chars) and can prefix with the agent name (e.g. `**Requirements Collector:** …`).
  - If there were failures, **issue_summary** (from `_summarize_agent_issues(agent_results)`) is appended to the message (e.g. “Issues: exporter: failed_timeout (…)”).

**Conversation history**

- The turn is appended:  
  `conversation_history += [{ role: "user", content: user_input }, { role: "assistant", content: message }]`  
  and state is saved (in dev, in-memory save).

So the **result** you see as **Bot:** is exactly this **synthesized message** (plus any “Issues: …” for failures).

---

### Step D – Return to dev chat

- **process_request** returns a dict that includes:
  - **message** — the synthesized reply (what the bot says).
  - **agent_results** — list of `{ agent_id, status, content, error?, blocked_by? }` for each task (success, skipped_unavailable, failed_timeout, failed_runtime, blocked_dependency).
  - **project_state** / **state_snapshot** — state after the turn.
  - **intent**, **plan**, **available_agents**, **artifacts**, etc.

- The dev script prints **message** as **Bot:** and then the **Agent results** lines (e.g. `requirements_collector: success`, `exporter: success`).

So: **your prompt** → one **process_request** → **graph** (intent + plan) → **agents run in order** → **state and history updated** → **one message + agent_results** returned → dev chat prints that as the result.

---

## Summary diagram

```
You: "make me a todo app"
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  process_request(user_input, session_id)                         │
│                                                                  │
│  1. Load state (session_id → project_state)                      │
│  2. Graph: load_state → classify_intent → build_plan             │
│     • Intent: e.g. requirements_gathering, requires_agents=[…]   │
│     • Plan: [Task(requirements_collector), …]                     │
│  3. For each task: get agent → extract context → run agent      │
│     • Agent updates state (state_delta)                           │
│     • Phase updated if applicable                                │
│  4. Synthesize one message from all agent contents                │
│  5. Append user + assistant to conversation_history, save        │
│  6. Return { message, agent_results, project_state, … }          │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
Bot: **Requirements Collector:** So far, we're looking at a web-based…
Agent results:
  - requirements_collector: success
```

---

## Files involved

| Role | File |
|------|------|
| Dev chat entry | `scripts/dev_chat_orchestrator.py` |
| Orchestrator | `src/orchestrator/master_agent.py` |
| Graph (load → classify → plan) | `src/orchestrator/graph.py` |
| Intent classification | `src/orchestrator/intent_classifier.py` |
| Execution planning | `src/orchestrator/execution_planner.py` |
| Agent registry | `src/orchestrator/agent_registry.py` |
| State | `src/state/state_manager.py`, `src/state/project_state.py` |
