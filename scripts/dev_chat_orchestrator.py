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
from src.orchestrator.agent_store import AGENT_STORE


async def main() -> None:
    persistence = InMemoryPersistenceAdapter()
    state_manager = StateManager(persistence)

    #use_llm = os.environ.get("USE_LLM_INTENT", "").strip() in ("1", "true", "yes")
    orchestrator = MasterOrchestrator(state_manager, use_llm=True)
    session_id = "dev-cli-session"

    manual_agent_id: str | None = None
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
        if user_input.startswith("/manual"):
            # Enter manual mode selection for the next turn.
            # Use current state to show only agents that are ready.
            project_state = await state_manager.load(session_id)
            available = orchestrator._get_available_agents(project_state)  # type: ignore[attr-defined]
            ready_agents = [a for a in available if a.get("is_available")]
            print("Manual mode: agents (ready now marked with '*'):")
            for entry in available:
                marker = "*" if entry.get("is_available") else " "
                print(f"  {marker} {entry['agent_id']}: {entry.get('agent_name', '')}")
            chosen = input("Enter agent_id to run (or leave blank to cancel): ").strip()
            if not chosen:
                manual_agent_id = None
                print("Manual mode cancelled; continuing in auto mode.\n")
            else:
                ids = {a["agent_id"] for a in available}
                if chosen not in ids:
                    print(f"Unknown agent_id '{chosen}'. Staying in auto mode.\n")
                    manual_agent_id = None
                else:
                    manual_agent_id = chosen
                    print(f"Next message will run in manual mode with '{manual_agent_id}'.\n")
            continue

        if manual_agent_id:
            response = await orchestrator.process_request(
                user_input,
                session_id,
                agent_selection_mode="manual",
                selected_agent_id=manual_agent_id,
            )
            # Manual mode is one-shot; reset to auto afterwards.
            manual_agent_id = None
        else:
            response = await orchestrator.process_request(user_input, session_id)
        message = response.get("message") or ""
        print(f"{message}\n")
        available_agents = response.get("available_agents") or []
        ready = [a for a in available_agents if a.get("is_available")]
        if ready:
            print("Available agents now:")
            for a in ready:
                print(f"  - {a['agent_id']}: {a.get('agent_name', '')}")
            print()


if __name__ == "__main__":
    asyncio.run(main())

