# Orchestrator Agent: Current Truth

This document is the up-to-date overview of the orchestrator based on the current implementation in `src/orchestrator/` and the earlier design intent in `docs/project-info.md` and `docs/orchestrator-agent.md`.

It describes what the orchestrator actually does today, how it operates, why each major behavior exists, and where the implementation differs from the older plan.

## Executive Summary

The orchestrator is the control layer for AgenticMentor. Its job is to:

- load the project/session state
- decide what the user is asking for
- determine which specialist agent(s) are relevant
- run agents in a safe order
- persist outputs back into canonical project state
- expose UI-friendly metadata about what happened and what can happen next

In the current codebase, it is not a fully autonomous multi-agent pipeline runner. It is a checkpointed coordinator.

That distinction matters:

- In `auto` mode, it usually plans a larger workflow but executes only one step per user turn.
- After a successful auto step, it saves the next recommended agent and waits for explicit user confirmation such as `continue`.
- In `manual` mode, it bypasses intent classification and runs only the selected agent plus any missing upstream dependencies.

So the real behavior is "plan broadly, execute conservatively".

## Main Files and Their Roles

### `src/orchestrator/graph.py`

Defines a small LangGraph pipeline with three nodes:

1. `load_state`
2. `classify_intent`
3. `build_plan`

This graph does not execute agents. It only produces orchestrator inputs:

- `project_state`
- `intent`
- `plan`
- `error`

Why this exists:

- keeps request interpretation separate from agent execution
- makes the orchestration entry flow easy to test
- allows async state loading and async intent analysis cleanly

### `src/orchestrator/intent_classifier.py`

Classifies the user request into a `primary_intent`, a list of `requires_agents`, a `confidence`, and optionally `expand_downstream`.

It supports two modes:

- rule-based matching
- optional Gemini structured-output classification if configured

Current supported intents:

- `requirements_gathering`
- `architecture_design`
- `mockup_creation`
- `execution_planning`
- `export`
- `general_inquiry`
- `unknown`

Why this exists:

- prevents every user message from triggering the full pipeline
- allows narrow requests like "just the tech stack" to stay narrow
- allows status questions to be answered from project state without running agents
- supports later UI/manual workflows without changing the core contract

Important current truth:

- The classifier has explicit export override logic, so file-format requests prefer `export`.
- `unknown` does not mean "run everything". The planner may still build a fallback plan, but `MasterOrchestrator` short-circuits execution and answers contextually for `unknown` and `general_inquiry`.

### `src/orchestrator/execution_planner.py`

Builds an ordered `ExecutionPlan` from the intent and project state.

It uses two dependency passes:

- `_resolve_upstream()`: prepend agents needed to create missing prerequisites
- `_resolve_downstream()`: append agents that naturally follow from newly produced artifacts

It relies on `AGENT_STORE` metadata for:

- `requires`
- `produces`
- `phase_compatibility`

Why this exists:

- centralizes dependency logic instead of scattering it across agents
- lets the system infer missing prerequisites automatically
- keeps plan generation metadata-driven

Important current truth:

- downstream expansion is optional and controlled by `expand_downstream`
- exporter is excluded from automatic downstream fan-out because it declares `requires=["*"]`
- if the intent is empty or `unknown`, the planner falls back to `requirements_collector`
- that fallback plan is not always executed, because `MasterOrchestrator` may decide to answer without running agents

### `src/orchestrator/agent_store.py`

Defines the static registry metadata for all known orchestrated agents.

Current agents:

- `requirements_collector`
- `project_architect`
- `execution_planner`
- `mockup_agent`
- `exporter`

Each entry describes:

- id
- name
- description
- interaction mode
- whether regeneration is selective
- whether the agent is expensive
- required artifacts
- produced artifacts
- phase compatibility

Why this exists:

- provides one source of truth for orchestration metadata
- drives dependency resolution
- drives the UI agent picker
- lets the orchestrator compute agent availability without instantiating agents

### `src/orchestrator/agent_registry.py`

Lazy-loads actual agent implementations and caches them.

Why this exists:

- avoids constructing every agent for every request
- lets unavailable agents fail gracefully to `None`
- keeps model/client wiring out of most orchestration logic

Important current truth:

- some agents depend on Gemini-backed clients and may be unavailable if config is missing
- unimplemented or unavailable agents are not fatal; the orchestrator records `skipped_unavailable`

### `src/orchestrator/master_agent.py`

This is the real orchestrator.

It wraps everything else and is responsible for:

- auto vs manual mode behavior
- continue/checkpoint flow
- calling agents
- applying state deltas
- phase transitions
- summarizing each completed step
- persisting conversation history
- returning UI-facing response data

This file contains the real operational policy of the system.

### `src/orchestrator/supabase_adapter.py`

Provides a persistence adapter that reconstructs and saves orchestrator state using Supabase tables.

Why this matters to the orchestrator:

- the orchestrator depends on durable state across turns
- conversation history, mockups, and project artifacts are persisted separately and reassembled into canonical `ProjectState`

## Canonical State the Orchestrator Depends On

The orchestrator works against `src/state/project_state.py`, which is the actual shared source of truth.

Key orchestrator-relevant fields:

- `current_phase`
- `requirements`
- `architecture`
- `roadmap`
- `mockups`
- `export_artifacts`
- `conversation_history`
- `agent_selection_mode`
- `selected_agent_id`
- `awaiting_user_action`
- `last_completed_agent_id`
- `next_recommended_agent_id`
- `last_auto_plan_agent_ids`

Why this matters:

- the orchestrator is stateful across turns
- "continue" only works because the next step is stored in state
- the UI can reconstruct workflow status from state alone

## How a Request Actually Flows

### 1. Auto Mode Entry

`MasterOrchestrator.process_request()` starts by loading state.

Then one of three things happens:

### Case A: Manual mode

If `agent_selection_mode="manual"` and `selected_agent_id` is provided:

- the graph is skipped entirely
- the orchestrator validates the selected agent against current readiness
- it builds a plan from the selected agent plus upstream dependencies only
- it persists manual-mode flags to state

Why this exists:

- supports UI-driven "run this agent now" behavior
- gives users precise control
- avoids unwanted downstream expansion

### Case B: Explicit continue

If the user says something like `continue`, and state says the workflow is waiting on user confirmation:

- the graph is skipped
- the orchestrator creates a single-task plan for `next_recommended_agent_id`
- downstream expansion is disabled

Why this exists:

- enforces one-step-at-a-time progression
- gives users a review checkpoint between major deliverables
- keeps expensive agents from running automatically after every success

### Case C: Normal auto routing

Otherwise the orchestrator invokes the LangGraph:

- `load_state`
- `classify_intent`
- `build_plan`

Why this exists:

- standardizes the routing path
- makes the load/classify/plan sequence composable and testable

### 2. General Inquiry and Unknown Short-Circuit

After the graph returns, `MasterOrchestrator` checks for `unknown` and `general_inquiry`.

If the message is treated as a contextual question rather than an execution request:

- no agent is run
- the orchestrator generates a state-based reply
- conversation history is still persisted

If an LLM is available, it phrases the answer. Otherwise it uses a deterministic fallback summary.

Why this exists:

- avoids expensive agent runs for status questions
- makes the orchestrator usable as a conversational guide, not only a router
- fixes an older behavior where ambiguous input could cascade into unnecessary work

Important current truth:

- the execution planner may still have produced a fallback plan internally
- the orchestrator intentionally does not execute that plan for this branch

### 3. Plan Validation and Recovery

If a plan is empty but requirements already exist while the phase is still `initialization`, the orchestrator performs a small recovery step:

- it updates the phase to `requirements_complete`
- it rebuilds the plan

Why this exists:

- protects the continue flow when state and phase drift out of sync
- keeps the workflow moving even if earlier turns left phase behind artifacts

### 4. Task Execution Policy

The orchestrator does not always execute the entire plan.

Current rule:

- `auto` mode executes only the first planned task
- `manual` mode executes the full manually constructed plan, which usually means the selected agent plus any missing upstream prerequisites

This is one of the most important current-truth behaviors.

Why it exists:

- creates explicit checkpoints after each major deliverable
- reduces accidental cost and latency
- lets users review requirements before architecture, architecture before roadmap, and so on

### 5. Context Extraction

Before each agent run, the orchestrator extracts only the required state fragments.

Why this exists:

- avoids passing full state unnecessarily
- keeps agent inputs relevant
- matches the dependency metadata in `AGENT_STORE`

Special case:

- `requires=["*"]` gets the full state

### 6. Running Agents

`_run_agent()` is an adapter layer over agent-specific APIs.

Current agent call styles are not uniform:

- `requirements_collector` uses `process_message(user_input, requirements_state, history)`
- `project_architect` uses `process(payload)`
- `execution_planner` uses `process(payload)`
- `mockup_agent` uses `process(payload)`
- `exporter` may use `execute(...)` or `process(...)`

Why this exists:

- normalizes multiple agent interfaces into one orchestrator contract: `{ "state_delta": ..., "content": ... }`

It also performs format translation:

- converts canonical requirements into the collector's schema
- merges collector output back into canonical requirements without wiping unrelated fields
- normalizes mockup entries into the canonical mockup shape

Why these translations are needed:

- the orchestrator is the boundary between heterogeneous agents and a single canonical state model

### 7. Failure Handling

Each agent task is protected by:

- registry lookup
- dependency blocking checks
- per-agent timeout via `asyncio.wait_for`
- runtime exception capture

Possible task statuses include:

- `success`
- `blocked_dependency`
- `skipped_unavailable`
- `failed_timeout`
- `failed_runtime`

Why this exists:

- prevents one bad agent run from crashing the whole turn
- gives the frontend precise execution feedback
- allows degraded behavior when agents are missing or misconfigured

Blocked artifacts are tracked so downstream tasks do not run if prerequisites failed earlier in the same execution batch.

### 8. State Deltas and Persistence

Agents do not mutate state directly. They return deltas.

The orchestrator applies those deltas through `StateManager.update()`, which:

- loads the canonical state
- merges top-level and dotted-path deltas
- revalidates Pydantic models where needed
- persists the updated result
- refreshes cache

Why this exists:

- keeps state changes centralized
- preserves canonical structure
- reduces accidental agent-side corruption of shared state

Important current truth:

- list merging is append-oriented by default
- mockups are a special case and are merged by stable identity
- conversation history is also a special case and is written directly to persistence to avoid duplicate append behavior

### 9. Phase Transitions

After a successful agent run, the orchestrator may advance `current_phase`.

Current map:

- `requirements_collector` -> `requirements_complete`
- `project_architect` -> `architecture_complete`
- `execution_planner` -> `planning_complete`
- `mockup_agent` -> `design_complete`
- `exporter` -> `exportable`

Special rule:

- requirements only advances when `_requirements_ready_for_handoff()` says the requirements are complete

Why this exists:

- phases are used as soft gates for later agents
- requirements gathering is intentionally allowed to be iterative before handoff

### 10. Checkpointing and Next-Step Guidance

After a successful auto-mode task, the orchestrator computes:

- `last_completed_agent_id`
- `next_recommended_agent_id`
- `awaiting_user_action`
- `last_auto_plan_agent_ids`

It also returns:

- `current_step`
- `next_step`

These are UI-facing workflow objects, not just internal state.

Why this exists:

- the frontend needs to render "what just happened" and "what comes next"
- the system wants the user to review outputs before continuing
- this turns the orchestrator into a guided workflow rather than a black-box pipeline

The default auto sequence is:

1. `requirements_collector`
2. `project_architect`
3. `execution_planner`
4. `mockup_agent`
5. `exporter`

Important current truth:

- downstream planning can suggest a broader set of tasks
- the orchestrator still prefers this checkpointed next-step sequence for auto continuation

### 11. Step Summaries and User-Facing Messaging

For successful auto steps, the orchestrator generates a single-step summary.

If an LLM is configured, it uses the LLM to produce a concise UI-oriented explanation of:

- what was produced
- what the frontend should now render
- what the user should do next

If no LLM is available, it uses deterministic summaries tailored to each agent.

Why this exists:

- raw agent outputs are inconsistent in tone and structure
- the frontend needs a clean post-step message
- the user needs explicit next-step guidance

Current message policy:

- for `execution_planner`, the orchestrator prefers its own summary over raw agent text
- for conversational agents like `requirements_collector`, it prefers the agent's own content when useful
- issue summaries are appended if any task failed or was skipped

### 12. Available Agents Metadata

The orchestrator computes `available_agents` for the UI on every normal path.

Each entry includes:

- phase compatibility
- unmet requirements
- which upstream agent would unblock it
- whether it is currently available
- whether it is expensive
- whether it supports selective regeneration

Why this exists:

- supports manual mode selection
- makes the UI explain why an agent is disabled
- exposes orchestration readiness without forcing the frontend to replicate business logic

### 13. Conversation History Handling

At the end of the turn, the orchestrator appends:

- the user message
- the final assistant message

It then persists them directly through the persistence adapter and refreshes cache.

Why it bypasses `StateManager.update()` here:

- the generic state merge logic extends lists
- using it for history would risk duplicate entries across turns or reruns

This is an intentional special case.

## What Each Agent Is Used For in the Current Flow

### Requirements Collector

Purpose:

- gather or refine project goals, users, features, constraints, budget, and timeline
- fill the canonical `requirements` fragment

Why it matters:

- everything else depends on having enough project definition
- it is the cheapest safe fallback when the system is unsure what to do

### Project Architect

Purpose:

- turn requirements into tech stack, diagrams, schema, API shape, and deployment strategy

Why it matters:

- roadmap and mockups both benefit from architecture context
- it is the main bridge from idea to implementation design

### Execution Planner

Purpose:

- produce phases, milestones, implementation tasks, and related roadmap data

Why it matters:

- turns design artifacts into an actionable build plan
- provides the main project-management output

### Mockup Agent

Purpose:

- generate UI screen artifacts and interactions

Why it matters:

- gives the user a design-facing deliverable
- helps connect requirements and architecture to user experience

### Exporter

Purpose:

- bundle the state into downloadable output artifacts

Why it matters:

- converts internal planning state into shareable deliverables
- separates "generate planning artifacts" from "package them for delivery"

## Most Important Differences From the Older Plan Docs

This is where the current code diverges most clearly from the earlier documents.

### 1. The orchestrator is not currently running a broad multi-agent pipeline by default

Older framing suggested more autonomous pipeline execution.

Current truth:

- auto mode usually executes one task only
- it then waits for explicit confirmation before proceeding

### 2. Unknown intent does not fan out into the full pipeline

Older docs mention unknown/unrecognized input as if it could still trigger broad routing.

Current truth:

- ambiguous or status-like messages are answered contextually
- no agent needs to run for that branch

### 3. Parallel execution is part of the vision, not the current runtime behavior

The older project overview discusses sequential or parallel execution.

Current truth:

- the current `MasterOrchestrator` task loop is sequential
- there is no parallel agent execution path in `src/orchestrator/`

### 4. The graph is narrower than the old description may imply

Current truth:

- LangGraph handles only load -> classify -> plan
- actual execution, phase updates, summaries, continue checkpoints, and persistence happen in `master_agent.py`

### 5. The orchestrator is now UI-aware

Current truth:

- it returns `available_agents`
- it returns `current_step` and `next_step`
- it stores manual/auto mode state
- it stores continuation metadata

This is a more product-facing orchestrator than the earlier generic architecture writeups suggested.

## Design Strengths of the Current Implementation

- Metadata-driven planning via `AGENT_STORE`
- Clear separation between classify/plan and execute/persist
- Safe checkpointed workflow for expensive generation steps
- Good degraded behavior when agents are unavailable
- Strong frontend support through readiness and step metadata
- Canonical state ownership stays with the orchestrator/state manager boundary

## Current Limitations

- agent interfaces are inconsistent, so `_run_agent()` contains orchestration-specific adapters
- parallel execution is not implemented
- some agent availability depends on external model configuration
- the planner can build plans that the orchestrator later intentionally does not execute for conversational branches
- phase gating is useful but still somewhat coarse

## Bottom Line

The orchestrator today is a stateful workflow controller, not just a router.

It combines:

- intent understanding
- dependency-aware planning
- one-step checkpointed execution
- phase management
- state persistence
- UI readiness metadata
- guided continuation logic

Its most important behavior is that it plans like a pipeline, but executes like a reviewed wizard. That is the clearest description of its current operating model.
