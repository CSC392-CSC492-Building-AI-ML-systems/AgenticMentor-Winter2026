"""Unit tests for IntentClassifier (orchestrator): rule-based and optional LLM path."""
import os

import pytest

from src.orchestrator.intent_classifier import (
    IntentClassifier,
    INTENT_TO_AGENTS,
)


@pytest.fixture
def classifier():
    """Rule-based classifier (no LLM)."""
    return IntentClassifier(llm=None)


def test_requirements_gathering_initialization(classifier):
    """'I want to build a task app' in initialization -> requirements_gathering."""
    result = classifier.analyze("I want to build a task app", "initialization")
    assert result["primary_intent"] == "requirements_gathering"
    assert "requirements_collector" in result["requires_agents"]
    assert result["confidence"] >= 0.0


def test_architecture_design_requirements_complete(classifier):
    """'generate the architecture' in requirements_complete -> architecture_design."""
    result = classifier.analyze("generate the architecture", "requirements_complete")
    assert result["primary_intent"] == "architecture_design"
    assert "project_architect" in result["requires_agents"]


def test_architecture_design_api_keyword(classifier):
    """Mention of API/diagram in requirements_complete -> architecture_design."""
    result = classifier.analyze("we need a diagram and tech stack", "requirements_complete")
    assert result["primary_intent"] == "architecture_design"
    assert "project_architect" in result["requires_agents"]


def test_export_any_phase(classifier):
    """Export intent allowed in any phase."""
    result = classifier.analyze("export the document to PDF", "initialization")
    assert result["primary_intent"] == "export"
    assert "exporter" in result["requires_agents"]


def test_execution_planning_architecture_complete(classifier):
    """Roadmap/timeline in architecture_complete -> execution_planning."""
    result = classifier.analyze("give me a roadmap and timeline", "architecture_complete")
    assert result["primary_intent"] == "execution_planning"
    assert "execution_planner" in result["requires_agents"]


def test_empty_input_unknown(classifier):
    """Empty or whitespace -> unknown, empty agents, 0 confidence."""
    result = classifier.analyze("", "initialization")
    assert result["primary_intent"] == "unknown"
    assert result["requires_agents"] == []
    assert result["confidence"] == 0.0

    result2 = classifier.analyze("   ", "requirements_complete")
    assert result2["primary_intent"] == "unknown"
    assert result2["requires_agents"] == []


def test_unknown_no_keywords(classifier):
    """Gibberish with no keywords -> unknown."""
    result = classifier.analyze("xyzzz qqq", "initialization")
    assert result["primary_intent"] == "unknown"
    assert result["requires_agents"] == []


def test_intent_result_shape(classifier):
    """Result has required keys and valid types."""
    result = classifier.analyze("we need a roadmap and timeline", "architecture_complete")
    assert "primary_intent" in result
    assert "requires_agents" in result
    assert "confidence" in result
    assert isinstance(result["requires_agents"], list)
    assert 0.0 <= result["confidence"] <= 1.0
    if result["primary_intent"] != "unknown":
        assert result["requires_agents"] == INTENT_TO_AGENTS.get(
            result["primary_intent"], []
        )


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY") and not os.getenv("gemini_api_key"),
    reason="GEMINI_API_KEY (or gemini_api_key) not set; LLM intent test skipped",
)
def test_intent_classifier_with_llm_when_configured():
    """When Gemini API key is set, IntentClassifier uses LLM and returns valid IntentResult."""
    from src.orchestrator.master_agent import _make_llm_if_configured

    llm = _make_llm_if_configured()
    if llm is None:
        pytest.skip("LLM not configured (missing or invalid API key)")
    classifier = IntentClassifier(llm=llm)
    result = classifier.analyze("I want to clarify our project goals", "initialization")
    assert "primary_intent" in result
    assert "requires_agents" in result
    assert "confidence" in result
    assert isinstance(result["requires_agents"], list)
    assert 0.0 <= result["confidence"] <= 1.0
    # LLM should often classify this as requirements_gathering
    assert result["primary_intent"] in (
        "requirements_gathering",
        "unknown",
        "architecture_design",
        "export",
        "mockup_creation",
        "execution_planning",
    )
