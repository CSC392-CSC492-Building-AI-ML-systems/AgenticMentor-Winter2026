## Orchestrator – Future Improvements (Post‑MVP)

This file tracks orchestrator improvements we want to make **after** the current minimal fixes are merged and the system is integrated with DB + frontend.

---

## 1. Robustness & Recovery

- **State/plan recovery on “No plan or state”**
  - Detect when we have requirements/architecture in state but `plan.tasks` is empty.
  - Rebuild the plan (and, if needed, advance `current_phase`) instead of returning the generic `"No plan or state."` error, especially after implicit confirmations.

- **Implicit confirmation at orchestrator level**
  - Restore the broader “implicit confirmation” handling (e.g. “yes this works”, “give me tech stack”, “this is good”) to:
    - Mark requirements complete when appropriate.
    - Advance from requirements → architect → planner without requiring exact “continue” phrasing.

- **Safer state loading**
  - Keep the hardened `StateManager.load` behavior (never throw on bad rows; fall back to a fresh `ProjectState`) so a corrupt/old row doesn’t kill the session.

---

## 2. Intent & Routing

- **Status questions routed to orchestrator (not agents)**
  - Treat questions like “what are the requirements currently?”, “what’s the tech stack?”, “where are we?” as **status queries**.
  - Answer via orchestrator using current state (requirements / architecture / roadmap) instead of routing them back into requirements_collector / architect.

- **Multi‑intent and change flows (v2)**
  - Re‑enable richer multi‑intent handling (e.g. “fill that in and give me tech stack and milestones”) where the intent classifier sets `requires_agents` for multiple agents in order and the planner runs them in one turn.
  - For “change X” messages (e.g. “change the tech stack to React”), support:
    - Running the requested agent *and* its downstream dependents (architect → planner → mockup).
    - Clear messaging about what was updated.

---

## 3. Phase Compatibility & Available Agents

- **Do not drop requested agents due to phase**
  - Ensure that explicitly requested agents (from intent or manual mode) are always included in the plan, even if `current_phase` doesn’t list them in `phase_compatibility`; earlier agents should update state/phase first.

- **Clarify available‑agents UX**
  - Keep `available_agents` computed from live state (phase + `requires`), but:
    - Make it clear in the UI copy that availability is “right now”, not permanent.
    - Optionally expose *why* an agent is unavailable (phase vs missing artifacts) more prominently.

---

## 4. Orchestrator Responses & Summaries

- **Execution planner summaries v2**
  - Current change uses the orchestrator to describe the roadmap more richly; later, consider:
    - Moving more of that logic into the planner agent.
    - Allowing a “verbose” mode that lists phase/milestone names in chat when the user explicitly asks.

- **Exporter response shaping**
  - Exporter already produces full documents; we may:
    - Add a short orchestrator summary that highlights where the file was saved and what sections it contains.
    - Avoid ever truncating exporter content when the user explicitly asked for “exported document details”.

---

## 5. Questions & Question‑First Flows

- **Question‑first handling for changes**
  - For messages like “can I use three.js?” or “is it possible to switch to Postgres?”, keep the current question‑first behavior (orchestrator answer, no agents).
  - In v2, make this more systematic:
    - Recognize “can I / can we / is it possible…” patterns.
    - Answer from state + constraints.
    - Offer explicit follow‑up actions (“say ‘yes, switch to X’ to apply this and refresh the plan”).

- **Better separation: status vs action**
  - Clarify in the intent classifier and orchestrator which messages are:
    - Pure status questions → orchestrator only.
    - Edits/changes → route to agents with `expand_downstream` when needed.

---

## 6. Observability & Debuggability

- **Better logs for orchestration decisions**
  - Add structured logs for:
    - Classified intent (primary_intent, requires_agents, expand_downstream).
    - Final `tasks_to_run` and any tasks skipped/blocked (with reasons).
    - Why a message was treated as unknown / general inquiry vs routed to an agent.

- **Surfacing agent issues in UI**
  - Extend the existing “Issues: …” suffix so the frontend can show a dedicated “Agent issues” panel, making timeouts / validation failures more obvious without cluttering the main message.

