# Orchestrator changes – how to test & group concerns

## 1. Group concerns vs what we did

| Concern (from DB/orchestrator team) | Addressed? | How |
|-------------------------------------|------------|-----|
| **Method mismatches** (Architect/Planner/Mockup use `.process()`, Requirements/Exporter use `. _generate()`) | ✅ No code change needed | Orchestrator already handles per-agent in `_run_agent`: `process_message()` for requirements_collector, `process()` for architect/planner/mockup, `execute()` for exporter. |
| **Initialization errors** (Architect & Mockup need `state_manager` in init) | ✅ Already correct | `AgentRegistry._create_agent()` passes `state_manager` to architect, mockup, and execution_planner. |
| **Commit timing** (data committed before next agent starts) | ✅ Orchestrator side done | We `await self.state.update(session_id, state_delta)` after each agent. **DB team:** ensure your `StateManager.update()` (or Supabase write) is awaited and completes before returning. |
| **“Skipping” bug / empty data** | ✅ Mitigated | Same init/method handling; variable agents + `expand_downstream` so we run requested + downstream when appropriate; no unnecessary single-agent limit. |
| **Orchestrator overwriting agent output** (e.g. “5 features” instead of collector’s questions) | ✅ Fixed | For `interaction_mode == "conversational"` (e.g. requirements_collector) we use the agent’s **content** as the message when non-empty; summary only for functional agents. |
| **General inquiry** (chit-chat / “where are we?”) | ✅ Fixed | When intent is `unknown`, we **don’t run any agent**; orchestrator replies from context (LLM or deterministic fallback). |
| **Smooth flow req → exporter** (pause when it makes sense, multi when it makes sense) | ✅ Fixed | Variable agents from intent; single ask → 1 agent then pause; compound ask → multiple in one turn; `expand_downstream` → run full plan so nothing is stale. |

So: **all raised problems are either already satisfied in code or explicitly fixed**; only commit timing needs to be verified in the persistence layer.

---

## 2. How to test

### 2.1 Unit tests (no API key)

From project root:

```bash
# Orchestrator graph + unknown intent
python -m pytest tests/unit/test_orchestrator_graph.py -v

# Intent classifier (rule-based when no LLM)
python -m pytest tests/unit/test_intent_classifier.py -v

# Execution planner (plan shape, unknown → requirements_collector)
python -m pytest tests/unit/test_execution_planner.py -v
```

**What they cover:** unknown intent returns contextual message and no agent run (`test_unknown_intent_no_agent_run_contextual_message`), plan shape, export intent, manual/auto paths (with mocks).

### 2.2 Integration tests (may need GEMINI_API_KEY for some)

```bash
# All orchestrator-related integration tests
python -m pytest tests/integration/test_orchestrator_full.py tests/integration/test_orchestrator_state_transitions.py tests/integration/test_orchestrator_agent_transitions.py tests/integration/test_orchestrator_downstream.py -v
```

### 2.3 Manual testing with dev chat (full flow, real agents + LLM)

Requires **GEMINI_API_KEY** (or GOOGLE_API_KEY) in `.env`. Orchestrator is created with `use_llm=True` so intent and general-inquiry/multi-agent synthesis use the LLM.

```bash
python -m scripts.dev_chat_orchestrator
```

**Scenarios to try:**

| Scenario | What to type | What to check |
|----------|----------------|---------------|
| **General inquiry (no agent)** | After some progress, say: `asdf` or `where are we?` or `what do we have?` | Reply is a short status (phase, what’s done); **no** requirements collector questions. |
| **Conversational content (no overwrite)** | New session: `I want a todo app` | Reply is the **requirements collector’s actual questions**, not “I have 5 features…”. |
| **Single ask → one agent, then pause** | `give me the tech stack` (after requirements exist) | Only architect runs; message is architect summary; next step suggested (e.g. “say continue”). |
| **Compound ask → multiple in one turn** | `make me a todo app and also give me a tech stack` (or after req: `tech stack and roadmap`) | Multiple agents run in one turn; one combined message; no “continue” in the middle. |
| **Stale refresh (expand_downstream)** | After you have architecture + roadmap: `change the tech stack to use React` | Architect runs **and** planner (and mockup if in plan); reply reflects updated chain, nothing stale. |
| **Manual mode** | `/manual` then pick e.g. `project_architect` | Only that agent runs; next turn back to auto. |

### 2.4 With DB (Supabase) end-to-end

Once the DB branch is merged and `StateManager` uses Supabase:

- Run the same dev-chat scenarios; state should persist across restarts.
- Confirm with DB team that `state.update()` is awaited so the next agent always sees the latest state (no empty snapshots).

---

## 3. Are the changes appropriate?

- **General inquiry short-circuit:** Appropriate — avoids running an agent on chit-chat and gives a clear, contextual reply.
- **Conversational agent content over summary:** Appropriate — users see the real collector questions instead of a generic summary.
- **Variable agents from intent:** Appropriate — one or many agents per turn based on what the user asked; LLM decides.
- **expand_downstream → full plan:** Appropriate — “change X” refreshes downstream so nothing is stale.
- **LLM for general reply and multi-agent synthesis:** Appropriate — better UX; fallbacks keep behavior defined if the LLM fails.
- **Intent prompt (variable requires_agents, change/update → expand_downstream):** Appropriate — aligns orchestration with user intent and freshness.

No unnecessary or risky changes; all are scoped to orchestrator behavior and intent/routing.
