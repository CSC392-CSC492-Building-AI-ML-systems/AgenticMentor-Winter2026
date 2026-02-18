"""Minimal CLI chat loop for MasterOrchestrator.

Usage (from project root):

    python -m scripts.dev_chat_orchestrator

This uses an in-memory persistence adapter, so state lives only
for the lifetime of the process.
"""

from __future__ import annotations

import asyncio
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

    # use_llm=False → intent classifier runs in pure rule-based mode.
    orchestrator = MasterOrchestrator(state_manager, use_llm=False)
    session_id = "dev-cli-session"

    print("Dev chat with MasterOrchestrator")
    print("Type 'exit' or 'quit' to end.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        response = await orchestrator.process_request(user_input, session_id)
        message = response.get("message") or ""
        print(f"Bot: {message}\n")


if __name__ == "__main__":
    asyncio.run(main())

