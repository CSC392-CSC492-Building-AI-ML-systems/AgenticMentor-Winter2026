# Orchestrator deep dive: what can hinder flow

## 1. Phase compatibility – what it does and “do agents before still run?”

**Where:** `execution_planner.py` – when building the plan we iterate over `resolved` (agents in dependency order) and **add a task only if** the agent’s `phase_compatibility` includes the current phase (or it’s explicitly requested – see below).

**When we filter (skip) an agent by phase:**

- We **do not** run that agent this turn – it never gets a task in the plan.
- **Agents that were already added to the plan still run.** The phase check is done per agent when building the plan. So if the plan ends up as `[requirements_collector, project_architect]` and we later added a phase filter that would have dropped architect, we’d still only have `[requirements_collector]` in the plan – so only the collector runs. The “agents before” are exactly the ones that made it into the plan; there is no overwriting of an already-run agent.

**Fix in place:** Agents that are in **`intent.requires_agents`** (explicitly requested) are **always added** to the plan, even if the current phase is not in their `phase_compatibility`. We rely on running earlier tasks first so state (and phase) are updated before later tasks run. So e.g. “fill in and give me tech stack and milestones” now gets plan `[requirements_collector, project_architect, execution_planner]` and all three run in sequence; phase no longer drops architect/planner.

---

## 2. Other areas that could hinder (and what we did)

### 2.1 Rule-based intent classifier – phase filter (fixed)

**Where:** `intent_classifier.py` – in the rule-based path we used to **skip** any intent whose `phase_compatibility` didn’t include the current phase before scoring. So in phase `"initialization"` we never considered `architecture_design` / `execution_planning` / `mockup_creation`, and “give me tech stack” could be classified as requirements or unknown.

**Fix:** Removed that phase filter in the rule-based loop. We now score all intents by keywords; the best match wins. So “give me tech stack” can return `architecture_design` and `requires_agents = ["project_architect"]` even in initialization. The execution planner then adds upstream (e.g. requirements_collector) and, thanks to the requested-agents bypass, still includes architect in the plan.

### 2.2 Blocked artifacts (intentional – no change)

**Where:** `master_agent.py` – when we **skip** an agent (unavailable, timeout, failure), we add its **produced** artifacts to `blocked_artifacts`. Later tasks whose `required_context` includes one of those artifacts are **not run** and get status `blocked_dependency`.

**Why it’s correct:** We only add to `blocked_artifacts` when we **did not** run an agent (e.g. registry returned None, or the agent threw). So “agents before” that **ran** normally do **not** block; only skipped/failed producers block downstream. This avoids running e.g. mockup_agent when architect was skipped and there is no architecture.

### 2.3 Downstream expansion and phase (intentional – no change)

**Where:** `execution_planner.py` – `_resolve_downstream` adds agents that consume artifacts produced by the current plan. Those **downstream** agents are not in `requested_ids`, so they are still subject to the phase filter.

**Why it’s correct:** When the user says “give me tech stack” with `expand_downstream=true`, we want architect (and maybe planner) but we don’t want to always add mockup/exporter in initialization. So downstream-added agents are only included when the current phase already allows them. Explicitly requested agents are not filtered (as in §1).

### 2.4 Upstream resolution and “has artifact” (intentional – no change)

**Where:** `execution_planner.py` – `_resolve_upstream` prepends an agent if the state doesn’t yet have one of its required artifacts (e.g. architect needs `requirements`; we prepend requirements_collector if state has no meaningful requirements). Emptiness is decided by `_state_has_artifact` (non-empty dict/list or model with some non-default value).

**Why it’s correct:** So we don’t run architect with no requirements; we run collector first. No change needed.

### 2.5 Context extraction (intentional – no change)

**Where:** `master_agent.py` – `_extract_context(project_state, task.required_context)` builds the context dict from current state. It does **not** require artifacts to be “complete”; it just passes whatever is in state. So if requirements are partial, architect still runs with that.

**Why it’s correct:** Allows running architect after a first pass of requirements; no extra blocking.

---

## 3. Summary table

| Area | Can hinder? | Change |
|------|-------------|--------|
| Execution planner: phase filter | Yes – was dropping requested agents | Bypass phase for agents in `intent.requires_agents` |
| Intent classifier (rule-based): phase filter | Yes – in init never returned architect/planner/mockup | Removed phase filter; score all intents |
| Blocked artifacts | No – only set when an agent is skipped/failed | None |
| Downstream expansion + phase | No – intentional for non-requested agents | None |
| Upstream resolution | No – ensures deps exist | None |
| Context extraction | No – passes current state | None |

So the two places that were actively hindering the orchestrator were (1) the execution planner’s phase filter for requested agents, and (2) the rule-based intent classifier’s phase filter. Both are fixed; the rest of the logic is intentional and left as is.

---

## 4. Is the orchestrator smooth and using sub-agents as a team?

**Short answer: Yes, for the flows we designed for.** It routes by user need, runs one or many agents per turn, passes state between them, and avoids running agents on chit-chat. A few caveats below.

### What works well (team-based and smooth)

| Behavior | How it works |
|----------|----------------|
| **User need → right agents** | Intent (LLM or rule-based) sets `requires_agents`; planner adds upstream deps and optionally downstream; requested agents are never dropped by phase. |
| **Single ask → one agent, then pause** | `n_requested = len(requires_agents)`; we run `planned_tasks[:n_requested]`. So “give me tech stack” → plan may be [collector, architect], we run 1 task (collector if first, or architect if requirements already done), then suggest “continue”. |
| **Compound ask → multiple in one turn** | “Tech stack and roadmap” → `requires_agents = [project_architect, execution_planner]`; plan gets upstream (collector if needed) + those; we run up to `n_requested` or full plan when `expand_downstream`. So several agents run in sequence, state updates between them, one combined message. |
| **Change/update → refresh downstream** | “Change tech stack to React” → `expand_downstream=True`; we run full plan so architect + planner (and mockup if in plan) run; no stale artifacts. |
| **General inquiry → no agent** | Unknown intent short-circuits: orchestrator replies from context (LLM or fallback); no sub-agent runs. |
| **Conversational content** | For `interaction_mode == "conversational"` (e.g. requirements_collector) we show the agent’s content, not a generic summary, so the “team” speaks through the right agent. |
| **State handoff** | After each agent we `await state.update(session_id, state_delta)` and advance phase when applicable; next agent sees updated state. |
| **Recovery** | No plan/state → reload, optional implicit confirmation + phase, rebuild plan; only then show “try again” if still empty. |

So the orchestrator **does** use sub-agents as a team based on user needs: it decides who runs, in what order, and how many this turn; it chains them with shared state and synthesizes a single reply.

### Caveats (not broken, but worth knowing)

1. **“Give me tech stack” in a fresh session**  
   Plan is [requirements_collector, project_architect]; `n_requested = 1` → we run only the collector first. User asked for “tech stack” but we correctly gate on requirements. The reply is the collector’s questions + “say continue.” Optional polish: prepend a one-liner like “To get to the tech stack we need a few details first” when the first task is not in `requires_agents`.

2. **LLM vs rule-based intent**  
   With no API key, intent is rule-based. Compound intents like “fill that in and tech stack and milestones” are handled by the compound-detection path or keyword scoring; we relaxed the rule-based phase filter so “give me tech stack” in init still returns architecture_design. So non-LLM flows are usable; LLM gives better nuance for complex phrasing.

3. **Manual mode**  
   User picks one agent; we build plan from that agent + upstream only. No downstream expansion. So manual is “run this one agent (and deps),” which is intentional.

4. **Blocked/failed agents**  
   If an agent is skipped or fails, its produced artifacts are marked blocked and downstream tasks don’t run. The reply includes an issue summary. So the team “stops” at the failure; no silent overwrite or wrong chain.

### Conclusion

The orchestrator is **smooth and team-based** for: general inquiry (no agent), single or compound asks (variable agents), state handoff between agents, conversational vs functional content, and change/refresh downstream. Remaining caveats are about clarity when we run an upstream agent first (“tech stack” → collector) and about LLM vs rule-based intent; they don’t break the flow. For a final “truly seamless” feel, the only optional improvement is the one-liner when the first task is upstream of what the user asked for.

For a final "truly seamless" feel, the only optional improvement is the one-liner when the first task is upstream of what the user asked for.

---

## 5. Update an agent in the middle (after all agents have run)

**Scenario:** Full pipeline has already run (requirements → architect → planner → mockup). User says e.g. "change the tech stack to React" or "update the roadmap."

**What happens:**

1. **Intent**  
   Classifier sets the requested agent (e.g. `project_architect`) and **`expand_downstream = True`** for change/update phrasing (per intent prompt and rules).

2. **Plan**  
   - **Upstream:** `_resolve_upstream([project_architect], state)` → usually just `[project_architect]` because state already has `requirements`; we don't re-add requirements_collector.  
   - **Downstream:** `_resolve_downstream([project_architect], state)` adds every agent that **consumes** what the middle agent **produces**: architect produces `architecture` → execution_planner (requires architecture) and mockup_agent (requires requirements + architecture) get added. Repeated until stable, so we get e.g. `[project_architect, execution_planner, mockup_agent]`.  
   - **Exporter** has `requires: ["*"]`; the planner skips auto-adding it in downstream expansion, so the plan does **not** include exporter. User can ask for "export" in a follow-up if they want a new document.

3. **Execution**  
   Because `expand_downstream` is True, we run the **full plan**: `tasks_to_run = planned_tasks`. So we run **architect → execution_planner → mockup_agent** in one turn. After each agent we `await state.update(session_id, state_delta)` and advance phase, so the next agent sees the updated state (e.g. new architecture, then new roadmap, then new mockups). We do **not** re-run requirements_collector.

**Summary:** Updating an agent in the middle runs **that agent plus all downstream agents** in sequence; upstream agents are not re-run because their artifacts are already in state. The chain stays consistent