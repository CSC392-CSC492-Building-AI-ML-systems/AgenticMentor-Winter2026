"""Minimal CLI chat loop for MasterOrchestrator (full application with real sub-agents).

Usage (from project root):

    python -m scripts.dev_chat_orchestrator

Uses the same MasterOrchestrator and AgentRegistry as the full app: real
requirements_collector, project_architect, execution_planner, mockup_agent, exporter.
State is in-memory (no DB). Set GEMINI_API_KEY (or GOOGLE_API_KEY) in .env so
all agents can run; otherwise agents that need the key will be skipped.

The CLI intentionally prints only the raw orchestrator message so the terminal
transcript matches what the frontend user would see.

Optional env:
  USE_LLM_INTENT=1  → use LLM for intent classification (default: rule-based).
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys


def _ensure_project_root_on_path() -> None:
    """Ensure project root is importable as a package root."""
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


_ensure_project_root_on_path()


from src.storage.memory_store import InMemoryPersistenceAdapter
from src.state.state_manager import StateManager
from src.orchestrator.master_agent import MasterOrchestrator


async def main() -> None:
    persistence = InMemoryPersistenceAdapter()
    state_manager = StateManager(persistence)

    #use_llm = os.environ.get("USE_LLM_INTENT", "").strip() in ("1", "true", "yes")
    orchestrator = MasterOrchestrator(state_manager, use_llm=True)
    session_id = "dev-cli-session"

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        response = await orchestrator.process_request(user_input, session_id)
        message = response.get("message") or ""
        print(f"{message}\n")


if __name__ == "__main__":
    asyncio.run(main())

