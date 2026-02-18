import sys
from pathlib import Path

# So "from src.*" works when run as script or from another dir
_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from datetime import datetime

from src.storage.memory_store import default_memory_adapter
from src.protocols.schemas import ProjectState, ChatMessage, MessageRole


async def test_save_and_load_project_state():
    session_id = "test-session-1"

    state = ProjectState(
        project_id=session_id,
        name="Test",
        description="desc",
        conversation_history=[],
        created_at=datetime.now(),
        last_updated=datetime.now(),
    )

    await default_memory_adapter.save(session_id, state.model_dump())

    loaded = await default_memory_adapter.get(session_id)
    assert loaded is not None
    assert loaded.get("project_id") == session_id


async def test_get_last_messages():
    session_id = "test-session-2"
    now = datetime.now()
    messages = [
        ChatMessage(role=MessageRole.USER, content="one", timestamp=now),
        ChatMessage(role=MessageRole.ASSISTANT, content="two", timestamp=now),
        ChatMessage(role=MessageRole.USER, content="three", timestamp=now),
    ]

    state = ProjectState(
        project_id=session_id,
        name="T2",
        description="desc",
        conversation_history=messages,
        created_at=now,
        last_updated=now,
    )

    await default_memory_adapter.save(session_id, state.model_dump())

    last = await default_memory_adapter.get_last_messages(session_id, n=2)
    assert len(last) == 2


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
