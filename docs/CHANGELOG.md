# Changelog

## Unreleased

### 2026-03-06 – Orchestrator hardening (through Commit 6 + manual mode / availability)

Baseline: branch at/after 587107c; only unrelated dirty file is `tests/integration/test_output.txt`. The dev-chat architect/mockup flow does not block this plan; remaining code changes are scheduled from that branch state.

**What is in place:**

- **Routing and cheap fallback**
  - Intent rules: file/export request → exporter only (no broad “generate” as export); “fill in / pick for me” → requirements first; narrow request → one agent with `expand_downstream=false`. Current-message export override when user clearly asks for PDF/Markdown/download.
  - Unknown/empty intent → route only to `requirements_collector`, not full pipeline. Execution planner skips downstream expansion when `expand_downstream` is false.

- **Conversation ownership and requirements translation**
  - Orchestrator owns user dialogue and final reply synthesis. Requirements collector receives normalized history and returns canonical state updates plus optional next-question text.
  - Rich requirements preserved: `_collector_state_to_requirements_delta` and `_requirements_to_collector_state` map between canonical `Requirements` (functional, constraints, business_goals, target_users, timeline, budget, is_complete, progress) and collector `RequirementsState` without dropping fields.

- **State merge semantics**
  - Mockups merged by stable identity (`screen_id` / `screen_name`) in `StateManager._merge_mockups` so regenerating the same screen updates it instead of duplicating.
  - Roadmap persisted as a single fragment; `_merged_value` re-validates Pydantic models so nested state stays typed.

- **Export and mockup deliverable persistence**
  - `ExportArtifacts` in project state: `saved_path`, `generated_formats`, `exported_at`, `history`. Exporter agent writes these into `state_delta`; later turns can answer where exports live and what format was generated.

- **Reliability and timeouts**
  - Per-agent time budgets (`AGENT_TIMEOUT_SECONDS`). Structured agent statuses: `skipped_unavailable`, `failed_timeout`, `failed_runtime`, `blocked_dependency`. Downstream agents skipped when required upstream artifacts failed (`_is_blocked_by_dependency`). User-facing failure summary via `_summarize_agent_issues` in the response message.

- **Manual mode and availability**
  - `_get_available_agents()` is readiness-aware: returns all store entries with `is_available`, `is_phase_compatible`, `unmet_requires`, `blocked_by`. Manual mode runs selected agent plus upstream only (no hidden downstream expansion). UI can show which agents are selectable in the current state.

- **Export reflects requirement removals**
  - Requirements collector merge: list fields `key_features`, `technical_constraints`, `business_goals`, `target_users` are **replaced** by the LLM’s list (not unioned) so corrections like “no user authentication” remove items. Exporter executive-summary prompt restricted to what is in the provided requirements (no adding authentication if not listed). UPDATE prompt instructs returning full corrected list when user removes or corrects something.

**Remaining (scheduled from branch state, not from live dev chat):**

- **Commit 7 – Regression and confidence pass:** Explicit coverage for ambiguous/low-confidence follow-up staying on requirements_collector; mockup twice same screen_id → single stored screen in orchestrator flow; regression that issue summaries remain visible on agent failure; tighten any stale test expectations.
- **Commit 8 – Manual mode and availability hardening:** Replace any remaining assertions that `available_agents` equals raw store with readiness-aware expectations; manual-mode test that selected agent + upstream only run; readiness test for agents blocked by missing upstream artifacts. Keep `tests/integration/test_output.txt` out of commits unless intentionally refreshing that fixture.

### 2026-02-08 – Project Architect improvements

- **Integration test: full output to files**
  - Writes to `test_output/`: `architect_full_output_<timestamp>_<label>.txt`, `system_diagram_*.mmd`, `erd_diagram_*.mmd`
  - `test_output/` added to `.gitignore`

- **Test scenarios**
  - `SIMPLE_REQUIREMENTS` and `COMPLEX_REQUIREMENTS`; run mode `simple` | `complex` | `both` (default: `both`)
  - Complex: B2B SaaS, SSO, RBAC, audit log, REST+GraphQL, webhooks, 10k users, Kubernetes

- **Prompts**
  - Tech stack: specific frameworks + optional `explanation` (rationale)
  - System diagram: pipe-only edge labels `-->|label|`, quoted node labels for parens, no parens in edge labels
  - ERD: all entities/relationships from requirements

- **Tech stack rationale**
  - `ArchitectureDefinition.tech_stack_rationale`; parsed from LLM `explanation`/`rationale`/`reasoning`; shown in summary and output files

- **Mermaid**
  - `_sanitize_mermaid_flowchart()`: quote node labels with `( )`, strip parens from edge labels
  - `src/utils/mermaid_validator.py`: compile with `npx @mermaid-js/mermaid-cli`; return `(success, error_message)`; if invalid, retry once with error in prompt (optional: requires Node/npx)

- **Progress logs**
  - `[1/4]` … `[4/4]` and `[diagram] Validating … (mmdc)` in `process()` so progress is visible during runs

### 2026-02-08 – Mermaid RAG (vector store + ingestion)

- **Vector store (Option C metadata)**
  - `VectorStore`: per-chunk metadata (`add`/`add_text` with `metadata`), `query_with_metadata()`, `query_text_with_metadata(..., meta_filter=...)`
  - Persist: `{store_name}.index`, `_texts.json`, `_metadata.json` under `data/vector_stores/` (gitignored)

- **Mermaid docs ingestion**
  - `data/mermaid_docs/sources.json`: config list of `{url, diagram_type}` (flowchart, erd, syntax); add more pages without code changes
  - `scripts/ingest_mermaid_docs.py`: Firecrawl scrape of each URL → chunk (by `##` + size) → embed (sentence-transformers `all-MiniLM-L6-v2`) → save to store `mermaid`
  - `src/utils/chunk_markdown.py`: shared chunking for RAG
  - `scripts/query_mermaid_store.py`: quick check that store is queryable (flowchart/erd filter + previews)

- **Architect RAG (initial + retry)**
  - ProjectArchitectAgent lazily loads mermaid store; injects top-3 RAG snippets into system and ERD diagram prompts (meta_filter by diagram_type).
  - On diagram validation retry: queries store with parse error message (`query_override`), injects error-relevant snippets into correction prompt; query capped at 300 chars.

- **Tests**
  - `tests/vector_store/test_mermaid_ingest.py`: chunking, sources config, mock ingest pipeline, store query with metadata, architect RAG when store exists
  - `test_architect_rag_snippets_query_override_error_message`: store queried with error text and snippets returned
  - `test_architect_rag_snippets_query_override_truncated_to_300`: long query_override truncated to 300 chars
  - `tests/vector_store/test_vector_store.py`: FAISS add/query/save/load and metadata

- **Dependencies**
  - `firecrawl-py` for scrape; `faiss-cpu`, `sentence-transformers` (existing)

### 2026-02-15 – Selective regeneration (diagrams) and session fixes

- **Selective regen: pass existing diagram for fresh output**
  - **Issue:** Step 2 (ERD-only) failed when new ERD matched old one; test required `erd_changed`. With same requirements the model often returned the same ERD.
  - **Cause:** Diagram generation did not receive the existing ERD/system diagram, so the model had no signal to produce a different diagram.
  - **Fix:** `_generate_mermaid_diagram()` now accepts optional `existing_diagram`. When set (selective regen), prompt includes current diagram and asks for an *improved or alternative version* so the result is a fresh take, not a copy. Capped at 2000 chars.
  - `_system_diagram_node` and `_data_schema_node` pass `existing.get("system_diagram")` and `existing.get("data_schema")` when regenerating.
  - Integration test Step 2 pass condition reverted to require `erd_changed` (new diagram must differ).

- **RAG and user context**
  - Mermaid RAG query uses only (a) fixed string per diagram type (`"erDiagram entities relationships attributes"` or `"flowchart TD ..."`), or (b) on retry the validator error (`query_override`). User/project context is not passed into the RAG query.
  - User context (requirements, etc.) is passed only in LLM prompts where needed (tech stack, diagrams, deployment); not to RAG. Requirements text capped (e.g. 2800 in state, 1500 on diagram retry).

- **Selective regen coverage**
  - Deterministic rules: "only/just" + ERD / system diagram / tech stack / deployment → single artifact; "backend/database/frontend" + change verbs → subset (e.g. backend → tech_stack + deployment_strategy). LLM impact analysis for other combinations.
  - Diagrams get fresh take via `existing_diagram`; tech stack changes when `user_request` implies change (e.g. "change backend to X"); deployment rule-based from tech_stack + requirements.

- **Merge develop into project-architect-agent/initialization**
  - Resolved conflicts in `.env.example`, `pyproject.toml`, `src/protocols/schemas.py` (accept both / merge content).
  - `.env.example` was "deleted by them" (develop); kept file with `git checkout --ours .env.example` and `git add .env.example`.
  - Concluded merge with commit; push to `origin project-architect-agent/initialization`.

- **Docs and process**
  - Issue and PR text for Project Architect Agent (LangGraph, selective regen, Mermaid RAG); PR links issue with `Closes #N`. Labels/type optional.
  - System Card scored against rubric (8/10); Uncertainty & Reliability completed; suggestions for higher score (decision points, stakeholder map, current vs planned data).
  - Orchestrator: can start in parallel; branch from `project-architect-agent/initialization` if it will use architect; after architect PR merges, merge `develop` into orchestrator branch then open PR.

### 2026-02-18 – Orchestrator Branch 1 (intent, plan, LangGraph)

- **Orchestrator Branch 1 — intent, plan, LangGraph (no agent execution yet)**
  - **IntentClassifier** (`src/orchestrator/intent_classifier.py`): rule-based + optional LangChain LLM; `IntentResult`; `analyze()` / `analyze_async()`.
  - **ExecutionPlan / Task** (`execution_plan.py`), **AGENT_STORE** (`agent_store.py`) with five agents and `FULL_PIPELINE_AGENT_IDS` for unknown-intent fallback.
  - **ExecutionPlanner**: dependency resolution, phase filter, full-pipeline fallback when intent unknown; fix for `requires=["*"]` recursion.
  - **LangGraph** (`graph.py`): load_state → classify_intent → build_plan → END.
  - **MasterOrchestrator**: optional Gemini LLM, `process_request()` runs graph, returns intent/plan/state (no agent execution yet).

- **Orchestrator unit tests** (`tests/unit/`): intent classifier, execution planner, graph + MasterOrchestrator (incl. unknown-intent fallback, optional LLM test).

- **Test fixes**
  - **conftest.py**: load `.env` from project root for tests.
  - **test_memory_store.py**: project root on `sys.path`, runnable as script via `pytest.main`; removed `test_run_async_tests`.
  - **test_project_architect.py**: `IntegrationTestReport` (not `TestReport`), single `datetime` import.
  - **pyproject.toml**: already had pytest, pytest-asyncio, `asyncio_mode = "auto"`.

### 2026-02-18 – Orchestrator Branch 2 (registry, execution, chat)

- **Agent registry and execution loop**
  - Added `AgentRegistry` (`src/orchestrator/agent_registry.py`) to lazily construct and cache concrete agents (e.g. `requirements_collector`, `project_architect`) behind stable ids.
  - Updated `MasterOrchestrator` (`master_agent.py`) to depend on `AgentRegistry` instead of raw `AGENT_STORE` metadata.
  - Extended `process_request()` to: run the LangGraph, iterate the `ExecutionPlan` tasks, call each agent with extracted context, apply `state_delta` via `StateManager.update()`, and return a synthesized `message` plus `state_snapshot` and `artifacts`.
  - Implemented `_extract_context`, `_run_agent`, and `_synthesize_response` helpers to normalize agent inputs/outputs (including mapping between `RequirementsState` and `ProjectState.requirements` and handling `ProjectArchitectAgent`'s `state_delta`/`architecture` outputs).
  - **process_request response shape:** Response now also includes `intent`, `plan`, and `project_state` (from the graph result) on every return path so existing unit tests (`test_master_orchestrator_process_request`, `test_master_orchestrator_export_intent`, `test_unknown_intent_gets_full_pipeline_fallback`) continue to pass without change.

- **End-to-end orchestrator test and dev chat**
  - Added `tests/integration/test_orchestrator_e2e.py`: seeds requirements + phase into in-memory persistence, runs `MasterOrchestrator.process_request("generate architecture", session_id)`, and asserts that architecture is present in state and the response message is non-empty.
  - Introduced `scripts/dev_chat_orchestrator.py`: minimal CLI loop using `InMemoryPersistenceAdapter` + `StateManager` so you can chat with the orchestrator and exercise the full multi-agent flow manually.

- **Requirements collector robustness**
  - Updated `RequirementsAgent` (`requirements_collector.py`) to normalize list-shaped fields when merging LLM JSON into `RequirementsState`, so that single-string values like `"students"` are coerced into `["students"]` for `target_users` and similar fields and no longer trigger validation errors.
  - Parse LLM response as JSON: strip markdown code fences (e.g. ` ```json ... ``` `) before `json.loads()` in update and completion-check nodes so the agent always returns a consistent structure for the orchestrator.

- **Environment example**
  - Updated `.env.example` to include `GEMINI_API_KEY` alongside `GOOGLE_API_KEY`, documenting the expected Gemini configuration for orchestrator E2E tests and live runs.

### 2026-02-26 – Exporter agent: markdown, PDF, tests

- **Exporter agent**
  - Markdown helpers: `_requirements_to_markdown`, `_architecture_to_markdown`, `_roadmap_to_markdown`, `_mockups_to_markdown`; `compile_markdown_document`, `build_export_markdown`.
  - Roadmap: phases, `implementation_tasks`, sprints, `critical_path`.
  - Mockups: `wireframe_code` (fenced block), interactions.
  - Executive summary via LLM; `metadata.saved_path` set to HTML path when PDF is not written.

- **PDF exporter**
  - Export uses raw Excalidraw JSON and Mermaid in code blocks (no client-side rendering).
  - Line wrap in PDF/HTML: `pre-wrap`, `overflow-wrap`, table wrapping.
  - WeasyPrint first; then Playwright (Chromium) in a thread (asyncio-safe); then HTML fallback.

- **Docs**
  - `docs/PDF_EXPORT_WINDOWS.md`: WeasyPrint on Windows (MSYS2, Pango, env vars).

- **Tests**
  - Exporter agent: fixes for `build_export_markdown` and agent return shape; coverage for phases/tasks/sprints/critical_path and wireframes/interactions.
  - `tests/unit/test_pdf_exporter.py`: accept either PDF or HTML when Playwright succeeds; assert raw code in fallback.
  - `tests/export/export_test.py`: UTF-8 stdout wrapper for Windows.
