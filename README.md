# AgenticMentor - AI Project Mentor

An intelligent AI mentor system that helps users define software project requirements.

## Project Structure

```
AgenticMentor-Winter2026/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── agent/               # Agent implementation
│   │   └── __init__.py
│   ├── api/                 # API routes
│   │   └── __init__.py
│   ├── core/                # Configuration and prompts
│   │   ├── __init__.py
│   │   └── config.py
│   └── models/              # Data models
│       └── __init__.py
├── pyproject.toml           # Project dependencies
├── .env.example             # Environment variables template
├── .gitignore
└── README.md
```

## Setup
1. **Install Python 3.11+**

2. **Clone the repository**
   ```bash
   cd /Applications/dev/AgenticMentor-Winter2026
   ```
3. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -e .
   ```

5. **Configure environment (optional for now)**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY when needed
   ```


## Running the Application
```bash
python -m src.main
```

Or with uvicorn:
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

