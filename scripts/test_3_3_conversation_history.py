"""
Standalone test for Part 3.3 — Conversation History.
Runs with plain `python scripts/test_3_3_conversation_history.py`.
No pytest-asyncio, no real LLM. Uses a mock registry that returns a
fake requirements_collector so at least one agent "runs" and produces
a result, exercising the full happy path of process_request.
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.state.project_state import ProjectState, Requirements
from src.state.state_manager import StateManager
from src.storage.memory_store import InMemoryPersistenceAdapter
from src.orchestrator.master_agent import MasterOrchestrator


# ---------------------------------------------------------------------------
# Minimal fake agent that mimics requirements_collector's process_message API
# ---------------------------------------------------------------------------
class FakeRequirementsCollector:
    async def process_message(self, user_input, requirements_state, history):
        return {
            "response": "Got it! Tell me more.",
            "requirements": None,  # no state delta — keeps test simple
        }


class FakeRegistry:
    def get_agent(self, agent_id):
        if agent_id == "requirements_collector":
            return FakeRequirementsCollector()
        return None  # all other agents skipped


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
async def test_history_appended_after_one_turn():
    session_id = "test-history-1"
    persistence = InMemoryPersistenceAdapter()
    state_manager = StateManager(persistence)

    # Seed state in initialization phase so requirements_collector is eligible
    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    orchestrator = MasterOrchestrator(
        state_manager,
        agent_registry=FakeRegistry(),
        use_llm=False,
    )

    response = await orchestrator.process_request("I want to build a task app", session_id)

    # Reload state from persistence to confirm it was saved
    state_dict = await persistence.get(session_id)
    history = state_dict.get("conversation_history", [])

    assert len(history) == 2, f"Expected 2 history entries, got {len(history)}: {history}"
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "I want to build a task app"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == response["message"]
    print(f"  PASS: 1 turn → 2 history entries. Message: '{response['message']}'")


async def test_history_grows_across_turns():
    session_id = "test-history-2"
    persistence = InMemoryPersistenceAdapter()
    state_manager = StateManager(persistence)

    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    orchestrator = MasterOrchestrator(
        state_manager,
        agent_registry=FakeRegistry(),
        use_llm=False,
    )

    await orchestrator.process_request("First message", session_id)
    await orchestrator.process_request("Second message", session_id)

    state_dict = await persistence.get(session_id)
    history = state_dict.get("conversation_history", [])

    assert len(history) == 4, f"Expected 4 history entries after 2 turns, got {len(history)}: {history}"
    assert history[0]["content"] == "First message"
    assert history[2]["content"] == "Second message"
    print(f"  PASS: 2 turns → 4 history entries (no duplicates).")


async def test_history_no_duplicates_on_reload():
    """Ensure loading state between turns doesn't cause double-appending."""
    session_id = "test-history-3"
    persistence = InMemoryPersistenceAdapter()

    seed = ProjectState(session_id=session_id, current_phase="initialization")
    await persistence.save(session_id, seed.model_dump())

    # Turn 1 — fresh orchestrator
    sm1 = StateManager(persistence)
    orch1 = MasterOrchestrator(sm1, agent_registry=FakeRegistry(), use_llm=False)
    await orch1.process_request("Hello", session_id)

    # Turn 2 — new orchestrator instance (simulates server restart / new request)
    sm2 = StateManager(persistence)
    orch2 = MasterOrchestrator(sm2, agent_registry=FakeRegistry(), use_llm=False)
    await orch2.process_request("World", session_id)

    state_dict = await persistence.get(session_id)
    history = state_dict.get("conversation_history", [])

    assert len(history) == 4, f"Expected exactly 4 entries, got {len(history)}: {history}"
    print(f"  PASS: No duplicates across separate orchestrator instances.")


async def main():
    print("\n=== Part 3.3 — Conversation History Tests ===\n")
    tests = [
        test_history_appended_after_one_turn,
        test_history_grows_across_turns,
        test_history_no_duplicates_on_reload,
    ]
    passed = 0
    for test in tests:
        name = test.__name__
        print(f"Running {name}...")
        try:
            await test()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {e}")
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")

    print(f"\n{'='*45}")
    print(f"Results: {passed}/{len(tests)} passed")
    if passed < len(tests):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
