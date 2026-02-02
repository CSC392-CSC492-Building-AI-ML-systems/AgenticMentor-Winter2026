AgenticMentor-Winter2026/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── agent/               # Agent implementation
│   │   ├── __init__.py
│   │   └── requirements_agent.py
│   ├── api/                 # API routes
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── core/                # Configuration and prompts
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── prompts.py
│   └── models/              # Data models
│       ├── __init__.py
│       └── schemas.py
├── pyproject.toml           # Project dependencies
├── .env.example             # Environment variables template
├── .gitignore
└── README.md

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
5. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
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

