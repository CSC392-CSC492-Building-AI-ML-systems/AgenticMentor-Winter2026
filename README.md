# AgenticMentor

AgenticMentor is a full-stack multi-agent project planning application. The backend exposes a FastAPI API that orchestrates specialized agents for requirements collection, architecture generation, execution planning, mockups, and export. The frontend is a Next.js app that provides authentication, project management, and the chat-driven workspace.

The current stack is built around:

- FastAPI for the backend API
- LangGraph / LangChain for orchestration and agent execution
- Gemini as the primary LLM provider
- Firebase Authentication for user identity
- Supabase for persisted project state
- Next.js for the frontend

## System Overview

At a high level, the application works like this:

1. A user signs in through Firebase in the Next.js frontend.
2. The frontend sends authenticated requests to the FastAPI backend.
3. The backend verifies Firebase ID tokens and loads the user's project state.
4. The master orchestrator selects and runs one or more agents.
5. Results are stored in Supabase when configured, or in memory when database settings are absent.
6. The frontend renders requirements, architecture, plans, mockups, and agent output for the selected project.

## Agent System

The backend uses a master orchestrator to route user requests to the right agent or sequence of agents.

### How requests are routed

When a user sends a message:

1. `MasterOrchestrator` loads the current project state.
2. `IntentClassifier` analyzes the message and maps it to one or more target artifacts and agent IDs.
3. The orchestrator checks the current phase, required upstream artifacts, and any manual agent selection.
4. In auto mode, the normal generation flow moves through:
   `requirements_collector -> project_architect -> execution_planner -> mockup_agent -> exporter`
5. For focused update requests, the orchestrator can run only the relevant agent instead of replaying the full chain.

This means the system can handle both guided end-to-end generation and narrower requests such as “redo only the ERD” or “reorganize the sprints.”

### Requirements Collector

**Role:** gathers, normalizes, and completes product requirements from the conversation.

**How it works:** uses a LangGraph workflow with four main steps: analyze context, update requirements, check completeness, and generate the next question. It merges the latest user input into `RequirementsState`, normalizes list-like fields, and keeps asking follow-up questions until the requirements are considered complete enough to hand off.

### Project Architect

**Role:** turns requirements into the technical architecture for the project.

**How it works:** uses LangGraph plus selective regeneration logic to produce the tech stack, system diagram, ERD/data schema, and deployment strategy. It uses deterministic rules for targeted changes, Mermaid validation for diagrams, Mermaid vector-store retrieval when available for diagram guidance, and fallback stack generation if structured LLM output is missing or invalid.

### Execution Planner

**Role:** converts requirements and architecture into a delivery roadmap.

**How it works:** uses LangGraph to generate or regenerate phases, milestones, implementation tasks, and sprints. It applies cascade rules when only part of the roadmap changes, computes a critical path, collects external resources from tasks, and falls back to default phases, milestones, or tasks when the LLM response cannot be used safely.

### Mockup Agent

**Role:** creates UI wireframes and user-flow outputs for the project.

**How it works:** asks the LLM for a structured `WireframeSpec`, compiles that spec into Excalidraw JSON with `ExcalidrawCompiler`, and writes preview/export artifacts to `outputs/mockups`. If the LLM is unavailable, invalid, or times out, it falls back to a default screen set based on the current requirements.

### Exporter

**Role:** packages the current project artifacts into downloadable documentation.

**How it works:** gathers the current requirements, architecture, roadmap, and mockups; generates an executive summary; compiles everything into Markdown; formats it; and runs the PDF exporter. If PDF generation is unavailable because native dependencies are missing, it falls back to HTML output.

### Typical request routing

- “Help me define the product” or “fill in the details for me” -> Requirements Collector
- “Generate the architecture, tech stack, ERD, or API structure” -> Project Architect
- “Give me phases, milestones, sprints, or implementation tasks” -> Execution Planner
- “Show me wireframes, screens, or user flows” -> Mockup Agent
- “Export this as a PDF or markdown file” -> Exporter

Some requests can trigger more than one agent. For example, a broad architecture-and-roadmap request can run the architect and planner together, while selective regeneration is supported for targeted architecture and planning updates.

## Repository Layout

```text
AgenticMentor-Winter2026/
|-- main.py                     # FastAPI entrypoint and route registration
|-- pyproject.toml              # Python package metadata and optional dev deps
|-- requirements.txt            # Pinned Python dependencies
|-- .env.example                # Example backend environment variables
|-- src/
|   |-- agents/                # Specialized agents
|   |-- auth/                  # Firebase auth helpers and token verification
|   |-- orchestrator/          # Master orchestration, intent routing, execution planning
|   |-- protocols/             # API schemas and internal contracts
|   |-- services/              # LLM settings and custom-key services
|   |-- state/                 # Project state models and persistence wiring
|   |-- storage/               # In-memory persistence implementation
|   |-- tools/                 # Export, diagrams, mockups, validation, vector store helpers
|   `-- utils/                 # Runtime config, prompts, logging, utility helpers
|-- frontend/
|   |-- app/                   # Next.js App Router pages
|   |-- components/            # UI building blocks and feature panels
|   |-- lib/                   # API client, Firebase client, shared frontend helpers
|   |-- public/                # Static frontend assets
|   `-- store/                 # Zustand state stores
|-- migrations/                # Supabase SQL schema and integration docs
|-- scripts/                   # Dev utilities, ingestion tools, verification scripts
|-- tests/                     # Unit, integration, export, db, and vector-store tests
|-- docs/                      # Architecture, deployment, and implementation notes
|-- data/                      # Local data assets, including vector-store inputs
`-- outputs/                   # Generated artifacts during local runs
```

## Core Application Areas

- `src/agents/`
  - `requirements_collector.py`: collects and refines product requirements
  - `project_architect.py`: produces architecture and technical design output
  - `execution_planner_agent.py`: turns approved scope into plans and tasks
  - `mockup_agent.py`: generates UI and wireframe-oriented output
  - `exporter_agent.py`: formats and exports artifacts
- `src/orchestrator/`
  - `master_agent.py`: central orchestration entrypoint
  - `graph.py`, `intent_classifier.py`, `execution_planner.py`: flow control and routing
  - `supabase_adapter.py`: Supabase-backed persistence adapter
- `src/state/`
  - `project_state.py`: canonical state model
  - `state_manager.py`: state load / merge / update logic
  - `persistence.py`: selects Supabase or in-memory storage
- `frontend/app/`
  - `dashboard/`: project overview UI
  - `login/`, `signup/`: Firebase-backed auth flows
  - `project/[id]/`: main project workspace
- `frontend/components/`
  - `chat/`, `console/`: conversational interface
  - `artifacts/`, `panels/`: requirements, architecture, wireframes, execution output
  - `settings/`: LLM settings UI

## Prerequisites

Install the following before local development:

- Python 3.10 or newer
- Node.js 20 or newer
- npm

You will also need service credentials depending on what you want to run:

- Gemini API key for agent execution
- Firebase project for authentication
- Supabase project for persistent storage
- Firecrawl API key if you plan to use the Mermaid ingestion tooling

## Backend Setup

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Python dependencies

Pinned runtime dependencies:

```bash
pip install -r requirements.txt
```

Optional editable install with project metadata:

```bash
pip install -e ".[dev]"
```

### 3. Configure backend environment variables

Copy the example file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Then fill in the values you need.

### 4. Run the backend

```bash
python main.py
```

Or run Uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API defaults to `http://localhost:8000`.

## Frontend Setup

The frontend lives in `frontend/`.

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Configure frontend environment variables

Create a local env file for the frontend, for example `frontend/.env.local`, and set the required values:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_FIREBASE_API_KEY=your_firebase_web_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id
```

### 3. Run the frontend

```bash
npm run dev
```

The frontend defaults to `http://localhost:3000`.

## Configuration Reference

### Backend environment variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | Yes for agent execution | Primary Gemini API key used by the backend |
| `GOOGLE_API_KEY` | Optional fallback | Legacy alias for the same Gemini key |
| `FIRECRAWL_API_KEY` | Conditional | Required for Firecrawl-powered ingestion scripts |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Yes for authenticated backend routes | Path to a Firebase service account JSON file for token verification |
| `FIREBASE_API_KEY` | Yes for email/password auth routes | Firebase web API key used by backend auth REST helpers |
| `SUPABASE_URL` | Recommended for persistence | Enables Supabase-backed project storage |
| `SUPABASE_KEY` | Recommended for persistence | Supabase key used by the persistence adapter |
| `API_HOST` | Optional | FastAPI host, default `0.0.0.0` |
| `API_PORT` | Optional | FastAPI port, default `8000` |
| `API_DEBUG` | Optional | Enables reload/debug-style local behavior |
| `MODEL_NAME` | Optional | Default Gemini model, currently `gemini-2.5-flash` |
| `MODEL_TEMPERATURE` | Optional | Default model temperature |
| `MODEL_MAX_TOKENS` | Optional | Default token cap for model output |
| `ALLOWED_DEFAULT_MODELS` | Optional | Comma-separated or JSON list of app-default Gemini models |
| `SUPPORTED_CUSTOM_MODELS` | Optional | Comma-separated or JSON list of custom-key Gemini models |

Notes:

- The backend loads `.env` automatically through `python-dotenv` and `pydantic-settings`.
- If `SUPABASE_URL` and `SUPABASE_KEY` are not set, persistence falls back to the in-memory adapter.
- Firebase-protected routes require a valid `Authorization: Bearer <id_token>` header.

### Frontend environment variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | Yes | Base URL for the FastAPI backend |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Yes | Firebase web SDK API key |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Yes | Firebase auth domain |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET` | Recommended | Firebase storage bucket |
| `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID` | Recommended | Firebase messaging sender ID |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Yes | Firebase web app ID |

## Local Development Workflow

Run the backend and frontend in separate terminals:

Terminal 1:

```bash
python main.py
```

Terminal 2:

```bash
cd frontend
npm run dev
```

Then:

1. Open `http://localhost:3000`
2. Sign up or log in through the frontend
3. Create a project
4. Send chat messages to drive requirements collection and downstream generation
5. Review outputs in the project workspace

## API Usage

The backend exposes the FastAPI app from `main.py`.

Useful routes include:

- `GET /health`
- `POST /auth/signup/email`
- `POST /auth/login/email`
- `POST /auth/verify-token`
- `GET /auth/me`
- `GET /projects`
- `POST /projects`
- `GET /projects/{project_id}`
- `DELETE /projects/{project_id}`
- `POST /projects/{project_id}/chat`
- `GET /projects/{project_id}/requirements`
- `GET /projects/{project_id}/llm-runtime`
- `GET /projects/{project_id}/llm-settings`
- `POST /projects/{project_id}/llm-settings`
- `POST /projects/{project_id}/llm-settings/verify`

### Health check

```bash
curl http://localhost:8000/health
```

### Example authenticated flow

Create a project:

```bash
curl -X POST http://localhost:8000/projects \
  -H "Authorization: Bearer <firebase_id_token>" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"My Project\",\"description\":\"Planning assistant test\"}"
```

Send a chat message:

```bash
curl -X POST http://localhost:8000/projects/<project_id>/chat \
  -H "Authorization: Bearer <firebase_id_token>" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"I want to build a task manager for students\"}"
```

## Database and Migrations

Supabase is the intended persistence layer for deployed environments.

Apply these migrations in order:

1. `migrations/001_initial_schema.sql`
2. `migrations/002_add_owner_uid.sql`
3. `migrations/003_add_llm_settings.sql`

Useful references:

- `migrations/SUPABASE_INTEGRATION.md`
- `migrations/SCHEMA_VERIFICATION.md`
- `scripts/verify_supabase.py`

To verify a local Supabase configuration:

```bash
python scripts/verify_supabase.py
```

## Deployment

The current repository is set up most naturally for:

- frontend deployment from `frontend/` on Vercel
- backend deployment of `main:app` on a Python host such as Render
- Supabase for persistent project state
- Firebase Authentication for identity
- Gemini for model execution

### 1. Provision external services

Set up:

- a Supabase project
- a Firebase project with Email/Password auth enabled
- a Gemini API key
- optionally a Firecrawl API key if you need ingestion tooling

### 2. Apply database migrations

Run the SQL files in `migrations/` against your Supabase project in the order listed above.

### 3. Deploy the backend

Recommended backend settings:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port 8000`

Set backend environment variables for:

- Gemini
- Firebase service account path
- Firebase API key
- Supabase URL and key
- any API/model overrides you want

If you deploy on Windows and need native PDF export, review `docs/PDF_EXPORT_WINDOWS.md`. Without the required GTK/Pango libraries, the exporter falls back to HTML output.

### 4. Deploy the frontend

Deploy the `frontend/` directory as a Next.js app and set:

- `NEXT_PUBLIC_API_URL` to the deployed backend URL
- all `NEXT_PUBLIC_FIREBASE_*` values from your Firebase web app config

### 5. Validate the deployment

Verify:

- `GET /health` returns successfully
- login and signup work
- project creation works
- chat responses persist across reloads when Supabase is configured
- LLM settings save and verify correctly

## Tests

Run the main Python test suite from the repo root:

```bash
pytest
```

Useful targeted suites and scripts:

- `tests/unit/` for lower-level logic
- `tests/integration/` for orchestrator flows
- `tests/db/` for persistence-heavy scenarios
- `tests/vector_store/` for vector ingestion and retrieval
- `tests/export/` for export behavior
- `scripts/test_3_3_conversation_history.py`
- `scripts/test_3_4_agent_selection.py`

## Developer Utilities

Common utility scripts include:

- `scripts/dev_chat_orchestrator.py` for backend-oriented development flows
- `scripts/ingest_mermaid_docs.py` to ingest Mermaid documentation into the vector store
- `scripts/query_mermaid_store.py` to inspect stored vector data
- `scripts/run_execution_planner.py` to exercise planner behavior directly
- `scripts/install_minimal.py` for minimal environment setup support

## Additional Documentation

Detailed docs live under `docs/`. High-value references include:

- `docs/architecture.md`
- `docs/api_reference.md`
- `docs/deployment-and-gap-plan.md`
- `docs/orchestrator-testing-guide.md`
- `docs/PDF_EXPORT_WINDOWS.md`

## Troubleshooting

### Backend starts, but authenticated routes fail

Check:

- `FIREBASE_SERVICE_ACCOUNT_PATH` points to a valid JSON file
- `FIREBASE_API_KEY` is set
- the frontend is sending a Firebase ID token in the `Authorization` header

### Data is not persisted between restarts

Check:

- `SUPABASE_URL` and `SUPABASE_KEY` are set
- the migrations were applied
- `python scripts/verify_supabase.py` succeeds

### Frontend cannot connect to the API

Check:

- `NEXT_PUBLIC_API_URL` points to the correct backend
- the backend is reachable from the frontend environment
- CORS is not being blocked by your deployment configuration

### PDF export falls back to HTML

That is expected when WeasyPrint's native dependencies are unavailable. See `docs/PDF_EXPORT_WINDOWS.md` for the Windows setup path.
