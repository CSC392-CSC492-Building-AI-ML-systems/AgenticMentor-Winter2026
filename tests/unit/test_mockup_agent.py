"""Unit tests for MockupAgent: fallback mode and timeout behavior."""

from __future__ import annotations

import asyncio
import logging

import pytest

from src.agents.mockup_agent import MockupAgent
from src.models.mockup_contract import MockupAgentRequest


def _minimal_request() -> dict:
    """Minimal MockupAgentRequest payload for tests."""
    return MockupAgentRequest(
        version="1.0",
        requirements={
            "project_name": "Test Project",
            "functional": ["Feature A", "Feature B"],
            "constraints": [],
        },
        architecture={"tech_stack": {"frontend": "Web", "backend": "API"}},
        platform="web",
    ).model_dump()


@pytest.mark.asyncio
async def test_mockup_agent_fallback_returns_valid_response():
    """MockupAgent with no LLM (fallback) must return valid wireframe spec and state_delta."""
    agent = MockupAgent(state_manager=None, llm_client=None)
    response = await agent.process(_minimal_request())

    assert response is not None
    assert "wireframe_spec" in response
    assert "excalidraw_json" in response
    assert "state_delta" in response
    assert "mockups" in response["state_delta"]

    spec = response["wireframe_spec"]
    assert spec.get("version") == "1.0"
    assert spec.get("project_name")
    assert isinstance(spec.get("screens"), list)
    assert len(spec["screens"]) >= 1

    assert response["excalidraw_json"].get("type") == "excalidraw"
    assert "elements" in response["excalidraw_json"]


@pytest.mark.asyncio
async def test_mockup_agent_timeout_falls_back_to_default_spec(caplog):
    """When LLM times out, MockupAgent must fall back to default spec and still return successfully."""
    # Fake LLM that never returns (so we hit timeout)
    class SlowLLM:
        async def ainvoke(self, prompt):
            await asyncio.sleep(999)
            return ""

    slow_llm = SlowLLM()
    agent = MockupAgent(state_manager=None, llm_client=slow_llm)
    # Use a 1s timeout so the test finishes quickly
    original_timeout = agent._LLM_TIMEOUT_SECONDS
    agent._LLM_TIMEOUT_SECONDS = 1.0

    with caplog.at_level(logging.WARNING, logger="src.agents.mockup_agent"):
        response = await agent.process(_minimal_request())

    agent._LLM_TIMEOUT_SECONDS = original_timeout

    # Must still return a valid response (fallback spec)
    assert response is not None
    assert "wireframe_spec" in response
    assert len(response["wireframe_spec"]["screens"]) >= 1
    assert "state_delta" in response and "mockups" in response["state_delta"]

    # Timeout should have been logged so we can see if timeout is interfering
    def has_timeout_msg(rec):
        msg = getattr(rec, "message", "") or (rec.getMessage() if hasattr(rec, "getMessage") else str(rec))
        return "timed out" in msg and "Mockup" in msg
    assert any(has_timeout_msg(rec) for rec in caplog.records), (
        f"Expected a log line containing 'timed out' and 'Mockup'; got: {[getattr(r, 'message', r) for r in caplog.records]}"
    )


@pytest.mark.asyncio
async def test_mockup_agent_with_real_llm_reports_failure_reason():
    """Run mockup with real LLM when configured; if LLM path fails, show why (timeout, parse, etc.)."""
    try:
        from src.utils.config import get_settings
        settings = get_settings()
        api_key = getattr(settings, "gemini_api_key", None) or getattr(settings, "GEMINI_API_KEY", None)
    except Exception:
        settings = None
        api_key = None
    if not api_key or str(api_key).strip() in ("", "your-gemini-api-key-here"):
        pytest.skip("GEMINI_API_KEY not set — run with .env configured to see why LLM path fails")

    from langchain_google_genai import ChatGoogleGenerativeAI
    model = getattr(settings, "model_name", "gemini-2.5-flash") if settings else "gemini-2.5-flash"
    llm = ChatGoogleGenerativeAI(
        model=model,
        api_key=api_key,
        temperature=0.5,
    )
    agent = MockupAgent(state_manager=None, llm_client=llm)
    request = MockupAgentRequest(
        version="1.0",
        requirements={
            "project_name": "Fitness Tracker",
            "functional": ["Log workouts", "View progress", "Set goals"],
            "constraints": ["Mobile-first"],
        },
        architecture={"tech_stack": {"frontend": "React Native", "backend": "API"}},
        platform="web",
    ).model_dump()

    response = await agent.process(request)
    meta = response.get("generation_metadata") or {}
    source = meta.get("source", "")
    reason = meta.get("fallback_reason", "")

    if source == "default_spec":
        pytest.fail(
            f"Mockup LLM path failed (used default spec). Reason: {reason!r}. "
            "Check timeout, API key, or LLM response format."
        )
    assert source == "llm"
    assert "wireframe_spec" in response and len(response["wireframe_spec"].get("screens", [])) >= 1
