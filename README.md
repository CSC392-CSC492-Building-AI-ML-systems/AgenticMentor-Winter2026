# Agentic Project Mentor

AI-powered project requirements collection system using LangGraph and Google Gemini.

## Project Structure

```
AgenticMentor-Winter2026/
├── main.py                          # FastAPI application entry point
├── pyproject.toml                   # Project dependencies
├── .env                             # Environment variables
├── .env.example                     # Example environment configuration
├── src/
│   ├── agents/
│   │   ├── requirements_collector.py  # LangGraph-based requirements agent
│   │   ├── base_agent.py
│   │   ├── project_architect.py
│   │   ├── execution_planner_agent.py
│   │   ├── mockup_agent.py
│   │   └── exporter_agent.py
│   ├── core/
│   │   ├── config.py                # Application settings
│   │   └── prompt.py                # LLM prompt templates
│   ├── models/
│   │   └── schemas.py               # Pydantic data models
│   ├── protocols/
│   │   ├── schemas.py               # Validation schemas
│   │   ├── review_protocol.py
│   │   └── metrics.py
│   ├── orchestrator/
│   │   ├── master_agent.py
│   │   ├── intent_classifier.py
│   │   └── execution_planner.py
│   ├── state/
│   │   ├── project_state.py
│   │   ├── state_manager.py
│   │   └── persistence.py
│   ├── tools/
│   │   ├── diagram_generator.py
│   │   ├── markdown_formatter.py
│   │   ├── pdf_exporter.py
│   │   ├── ui_wireframe.py
│   │   ├── validation_tools.py
│   │   └── vector_store.py
│   └── utils/
│       ├── config.py
│       ├── logger.py
│       ├── prompt.py
│       └── token_optimizer.py
├── tests/
│   ├── test_basic.py
│   └── test_api_key.py
└── docs/
    ├── agent_specifications.md
    ├── api_reference.md
    └── architecture.md
```

## Setup

### 1. Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -e .
```

### 3. Configure environment variables

Copy the example environment file and add your API key:

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_api_key_here
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=True
MODEL_NAME=gemini-flash-latest
MODEL_TEMPERATURE=0.7
MODEL_MAX_TOKENS=4096
```

### 4. Run tests

```bash
python tests/test_api_key.py
```

## Running the Application

### Start the server

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on `http://localhost:8000`

## Using the Requirements Collector

### 1. Health Check

```bash
curl http://localhost:8000/health
```

### 2. Create a New Project

```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Project",
    "description": "Project description"
  }'
```

Response will include a `project_id` (e.g., `2799abcf-082b-4020-a5a6-79e35f30f3e8`)

### 3. Start Conversation with Requirements Collector

```bash
curl -X POST http://localhost:8000/projects/7c997f49-d3d6-4c5e-9680-991d55a0322b/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to build a todo app"
  }'
```
### 4. Continue the Conversation

Keep sending messages to the same endpoint. The agent will ask follow-up questions:

```bash
curl -X POST http://localhost:8000/projects/521c736a-4cba-4104-b17e-d56d7c39bbf3/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Its for students who need to track assignments"
  }'
```

```bash
curl -X POST http://localhost:8000/projects/{project_id}/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Key features include task creation, due dates, and priority levels"
  }'
```
