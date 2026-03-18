### Deployment and Gap Plan

This document summarizes what’s needed to get the app running end‑to‑end in a free‑tier friendly way, and what code/behavior gaps remain in the orchestrator and agents.

---

### A. Code / Behavior Gaps

#### 1. Orchestrator intent & plan hardening

- **Define explicit intents**: `create`, `update`, `inspect`, `export`, `general_inquiry`, each with target artifacts (`requirements`, `architecture`, `roadmap`, `mockups`, `export_artifacts`).
- **Make `IntentClassifier` output structured intents** instead of loosely-typed strings; include `primary_intent`, `target_artifacts`, and confidence.
- **Replace scattered phase logic with a declarative config**:
  - For each phase: allowed intents, allowed agents, required artifacts.
  - For each agent: which intents it can satisfy, which artifacts it can (re)generate, and which phases it is compatible with.
- **Improve “No plan or state.” UX**:
  - Distinguish `no_state` (session not found) vs `no_plan_but_state` (intent understood but invalid for current phase) vs `plan_build_failed` (internal error).
  - Return user‑facing messages that explain why the request can’t run in the current phase and how to fix it (e.g. run Architect in update mode before Planner).

#### 2. Proper support for update / regeneration flows

- **At orchestrator level**:
  - When intent is `update`, compute the **minimal agent set** based on target artifacts:
    - Example: frontend‑only change → `project_architect` (stack + diagrams) and maybe `mockup_agent`.
    - Example: roadmap‑only tweak → `execution_planner` only.
    - Example: stack change that affects delivery plan → `project_architect` + `execution_planner`.
  - Build plans around these minimal sets, instead of always re‑running the full AUTO_FLOW sequence.
- **Align with Architect / Planner selective regen**:
  - Standardize the `user_request` strings the orchestrator sends (e.g. “Regenerate ERD only”, “Change frontend to Next.js only; keep backend and DB”) so they hit deterministic rules in:
    - `ProjectArchitectAgent._deterministic_regen_plan`
    - `ExecutionPlannerAgent._deterministic_regen_plan`
  - Surface “update‑only” actions in manual mode / UI:
    - Examples: “Regenerate ERD only”, “Regenerate tasks + sprints”, “Update tech stack only”.

#### 3. Robustness, retries, and history

- **Agent‑level robustness in `MasterOrchestrator._run_agent`**:
  - Classify errors as transient (LLM 5xx, timeout, connection issues) vs permanent (validation, schema).
  - Add a small retry policy (1–2 retries with exponential backoff) for transient failures before marking `failed_runtime`.
  - Keep the explicit timeout behavior for each agent but surface clearer error reasons to the user (e.g. “Planner LLM timed out; you can retry this step.”).
- **Issue summaries and guidance**:
  - Expand `_summarize_agent_issues` output into short, user‑facing hints:
    - Which agents failed.
    - Whether retrying is likely to help vs needing a different input.
- **Conversation and state hygiene**:
  - Introduce history trimming / summarization:
    - Maintain a running summary in state plus the last N turns for display.
    - Prevent unbounded `conversation_history` growth (token and DB size).
  - Consider adding `project_state_version` / `last_updated_at` to support:
    - Debugging weird transitions.
    - Detecting stale clients.

#### 4. Frontend contract & UX (design only)

- **API contract**:
  - Document the request/response shape for the main orchestrator endpoint:
    - Input: `session_id`, `user_input`, optional `agent_selection_mode`, `selected_agent_id`.
    - Output: `message`, `intent`, `plan`, `available_agents`, `current_step`, `next_step`, `project_state`, `awaiting_user_action`.
  - Optionally generate TypeScript types from Pydantic models, or mirror them manually in `frontend` as a single `types.ts`.
- **Update vs create flows**:
  - Design UX for:
    - Starting a fresh project vs updating an existing one.
    - Choosing “update only X” flows (ERD, tasks, sprints, mockups).
  - Design how errors are displayed:
    - Show plan failure reason and suggested next actions, not just a generic toast.
  - Plan loading / progress UX for long‑running agents (Architect, Planner, Mockups).

---

### B. Deployment / Infrastructure Plan

Assumed targets:

- **Backend**: Render (or similar Python‑friendly free host).
- **Database / persistence**: Supabase (free tier) via `SupabaseAdapter`.
- **Frontend**: Vercel (hosting the `frontend` app).
- **Auth**: Firebase Authentication (email/password + optional providers).
- **LLM**: Gemini via `GEMINI_API_KEY` / `GOOGLE_API_KEY`.
- **Vector store**: local, read‑only index in `data/vector_stores`.

#### 5. Supabase setup

- Create a Supabase project (free tier).
- Run database migrations:
  - Execute `migrations/001_initial_schema.sql` in Supabase SQL editor.
- In backend environment (Render service or equivalent), set:
  - `SUPABASE_URL=<your-project-ref>.supabase.co`
  - `SUPABASE_KEY=<your-anon-public-key>`
- Verify:
  - `get_default_adapter()` selects `SupabaseAdapter` and logs `[persistence] Using SupabaseAdapter (Postgres backend)`.
  - `test_supabase_adapter.py` passes when pointed at the same Supabase project.

#### 6. Gemini configuration

- Create a Gemini API key in Google AI Studio.
- Set environment in backend:
  - `GEMINI_API_KEY=<your-gemini-key>` (or `GOOGLE_API_KEY`).
  - Optional overrides via `Settings` if needed (`MODEL_NAME`, `MODEL_TEMPERATURE`, `MODEL_MAX_TOKENS`), otherwise rely on defaults.
- Sanity‑check locally:
  - Run a simple project through:
    - `ProjectArchitectAgent` (tech stack + diagrams).
    - `ExecutionPlannerAgent` (phases, tasks).

#### 7. Firebase Authentication integration

- In Firebase console:
  - Create a project.
  - Enable Email/Password auth and any social providers you need.
  - Obtain:
    - Web app config (for frontend).
    - Service account JSON (for backend verification).
- Backend:
  - Mount the service account JSON as a secret file (e.g. `/app/firebase-service-account.json`).
  - Set:
    - `FIREBASE_SERVICE_ACCOUNT_PATH=/app/firebase-service-account.json`
    - `FIREBASE_API_KEY=<Firebase-web-API-key>` (if you will use REST/email‑password flows).
- Plan for request handling:
  - Frontend acquires a Firebase ID token and sends it as `Authorization: Bearer <id_token>`.
  - Backend uses `firebase_auth.py` to verify the token and attach a stable `user_id` to each session / `ProjectState`.
  - Later, align this with Supabase RLS policies to get per‑user data isolation.

#### 8. Backend deployment (Render or similar)

- API entrypoint:
  - Use `main.py` (FastAPI app) as the main entrypoint.
  - Ensure there is a route that wraps `MasterOrchestrator.process_request` (e.g. `/orchestrator/process`).
- Render service configuration:
  - Build command: `pip install -r requirements.txt` or `pip install .` depending on how you deploy.
  - Start command (example): `uvicorn main:app --host 0.0.0.0 --port 8000`.
  - Environment variables:
    - `GEMINI_API_KEY` or `GOOGLE_API_KEY`
    - `SUPABASE_URL`, `SUPABASE_KEY`
    - `FIREBASE_SERVICE_ACCOUNT_PATH`, `FIREBASE_API_KEY`
    - Any other settings consumed by `src.utils.config.Settings`.
- Verification:
  - Hit `/health` on the deployed backend.
  - Make a test orchestrator request (e.g. via curl or a simple script) to confirm agents run and state is saved to Supabase.

#### 9. Vector store behavior

- Treat `data/vector_stores` as **read‑only** at runtime:
  - Prebuild the Mermaid vector index locally and commit the index files to the repo.
  - `ProjectArchitectAgent._get_mermaid_store` should:
    - Load the index if present.
    - Skip dynamic writes or re‑embedding on each request.
- On free hosts, disk is often ephemeral:
  - Because the index is baked into the build image, read‑only access is safe.
  - Do not rely on growing the store dynamically for user data in the free‑tier deployment.

#### 10. Frontend deployment (Vercel) and wiring

- Vercel project:
  - Root set to the `frontend` directory.
  - Build/Start commands according to the existing Next.js configuration.
- Frontend environment variables:
  - `NEXT_PUBLIC_API_BASE_URL=https://<your-backend-service>.onrender.com`
  - `NEXT_PUBLIC_FIREBASE_API_KEY`, `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`, etc. from Firebase web config.
- Client behavior:
  - All orchestrator calls use `NEXT_PUBLIC_API_BASE_URL` for API routes.
  - After login, include `Authorization: Bearer <id_token>` in requests.
  - Use orchestrator response fields (`message`, `current_step`, `next_step`, `available_agents`) to drive the UI.

#### 11. End‑to‑end validation

- From the deployed frontend:
  - Create/sign into a user account with Firebase Auth.
  - Start a new project session and describe a project.
  - Walk through:
    - Requirements → Architect → Planner → Mockups → Exporter (where applicable).
  - Verify:
    - Supabase `projects`, `conversation_messages`, and `mockups` tables have the expected rows.
    - Orchestrator phases and `available_agents` behave as in local development.
    - Error cases (invalid agent selection, missing state, LLM timeouts) surface clear, actionable messages.

