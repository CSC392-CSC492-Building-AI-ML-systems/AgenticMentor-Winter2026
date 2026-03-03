"""Unit tests for ExporterAgent and export document builder."""

from __future__ import annotations

import asyncio
import os

import pytest

from src.agents.exporter_agent import (
    ExporterAgent,
    build_export_markdown,
    compile_markdown_document,
    _architecture_to_markdown,
    _requirements_to_markdown,
    _roadmap_to_markdown,
    _mockups_to_markdown,
)


def test_build_export_markdown_empty_context():
    out = build_export_markdown({}, project_name="My Project")
    assert "MY PROJECT" in out  # title is uppercased
    assert "Executive Summary" in out
    assert "Exported project plan" in out


def test_build_export_markdown_with_requirements():
    context = {
        "project_name": "Test App",
        "requirements": {
            "functional": ["Login", "Dashboard"],
            "constraints": ["Python backend"],
        },
    }
    out = build_export_markdown(context)
    assert "TEST APP" in out  # title is uppercased
    assert "Requirements" in out
    assert "Login" in out
    assert "Dashboard" in out
    assert "Python backend" in out


def test_build_export_markdown_with_architecture():
    context = {
        "architecture": {
            "tech_stack": {"frontend": "React", "backend": "FastAPI"},
            "tech_stack_rationale": "Modern stack.",
        },
    }
    out = build_export_markdown(context)
    assert "Architecture" in out
    assert "React" in out
    assert "FastAPI" in out
    assert "Modern stack" in out


def test_requirements_to_markdown():
    md = _requirements_to_markdown({"functional": ["F1"], "user_stories": [{"role": "User", "goal": "Do X", "reason": "Y"}]})
    assert "Requirements" in md
    assert "F1" in md
    assert "User" in md
    assert "Do X" in md


def test_architecture_to_markdown():
    md = _architecture_to_markdown({"tech_stack": {"db": "PostgreSQL"}, "api_design": [{"method": "GET", "path": "/api", "description": "List"}]})
    assert "Architecture" in md
    assert "PostgreSQL" in md
    assert "GET" in md
    assert "/api" in md


def test_roadmap_to_markdown():
    md = _roadmap_to_markdown({"milestones": [{"name": "M1", "description": "First"}], "sprints": [{"name": "S1", "goal": "Goal", "tasks": ["T1"]}]})
    assert "Roadmap" in md
    assert "M1" in md
    assert "S1" in md
    assert "T1" in md


def test_roadmap_to_markdown_phases_tasks_critical_path():
    """New: phases, implementation_tasks, critical_path from Execution Planner."""
    roadmap = {
        "phases": [{"name": "Setup", "description": "Initial setup", "order": 1}],
        "implementation_tasks": [
            {"id": "task-1", "title": "Init repo", "phase_name": "Setup", "depends_on": [], "external_resources": ["GitHub"]},
        ],
        "critical_path": "task-1 -> task-2",
    }
    md = _roadmap_to_markdown(roadmap)
    assert "Phases" in md
    assert "Setup" in md
    assert "Implementation Tasks" in md
    assert "task-1" in md
    assert "Init repo" in md
    assert "Critical Path" in md
    assert "task-1 -> task-2" in md


def test_mockups_to_markdown():
    md = _mockups_to_markdown([{"screen_name": "Home", "user_flow": "Landing", "wireframe_code": "div", "interactions": ["click"]}])
    assert "Mockups" in md
    assert "Home" in md
    assert "Landing" in md


def test_mockups_to_markdown_wireframe_and_interactions():
    """New: wireframe_code and interactions included in export."""
    mockups = [
        {
            "screen_name": "Login",
            "user_flow": "User signs in",
            "wireframe_code": "<div>Login form</div>",
            "interactions": ["click Submit", "focus Email"],
        },
    ]
    md = _mockups_to_markdown(mockups)
    assert "Mockups" in md
    assert "Login" in md
    assert "User signs in" in md
    assert "click Submit" in md
    assert "focus Email" in md
    assert "Login form" in md
    assert "```" in md


@pytest.mark.asyncio
async def test_exporter_agent_generate_returns_structure():
    """Agent returns content, state_delta (export_artifacts), metadata (saved_path)."""
    agent = ExporterAgent()
    context = {
        "project_name": "Unit Test Project",
        "requirements": {"functional": ["Requirement one"]},
        "architecture": {},
        "roadmap": {},
        "mockups": [],
    }
    # Pass context as input so project_name and requirements are used
    result = await agent._generate(context, {}, [])
    assert "content" in result
    assert "UNIT TEST PROJECT" in result["content"]  # title is uppercased
    assert "Requirement one" in result["content"]
    assert "state_delta" in result
    artifacts = result["state_delta"]["export_artifacts"]
    assert "executive_summary" in artifacts
    assert "markdown_content" in artifacts
    assert "metadata" in result
    assert "saved_path" in result["metadata"]


@pytest.mark.asyncio
async def test_exporter_agent_metadata_saved_path(tmp_path, monkeypatch):
    """Agent sets metadata.saved_path to PDF or HTML fallback path."""
    monkeypatch.chdir(tmp_path)
    agent = ExporterAgent()
    context = {"project_name": "Saved Path Test", "requirements": {}, "architecture": {}, "roadmap": {}, "mockups": []}
    result = await agent._generate(context, {}, [])  # context as input so project_name is used
    saved_path = result["metadata"]["saved_path"]
    assert saved_path
    assert saved_path.endswith(".pdf") or saved_path.endswith(".html")
    assert "saved_path_test" in saved_path.lower()


def test_exporter_agent_get_quality_criteria():
    agent = ExporterAgent()
    criteria = agent._get_quality_criteria()
    assert "completeness" in criteria
    assert "formatting" in criteria
    assert "diagrams" in criteria


def test_build_export_markdown_partial_state():
    """Exporter can be called at any stage: only sections with content are included."""
    context = {
        "project_name": "Early Stage",
        "requirements": {"functional": ["Only requirement so far"]},
        # no architecture, roadmap, or mockups
    }
    out = build_export_markdown(context)
    assert "EARLY STAGE" in out
    assert "Only requirement so far" in out
    assert "Requirements" in out
    # No "pending" or "missing" wording for other agents
    assert "pending" not in out.lower()
    assert "No architecture" not in out
    assert "Mockups pending" not in out


def test_compile_markdown_document_full():
    """Full document includes all sections when all fragments provided."""
    md = compile_markdown_document(
        project_name="Full Doc",
        summary="Summary here.",
        reqs={"functional": ["F1"]},
        arch={"tech_stack": {"frontend": "React"}},
        roadmap={"milestones": [{"name": "M1", "target_date": "Week 1"}]},
        mockups=[{"screen_name": "Home", "user_flow": "Land"}],
    )
    assert "FULL DOC" in md
    assert "Summary here" in md
    assert "F1" in md
    assert "React" in md
    assert "M1" in md
    assert "Week 1" in md
    assert "Home" in md
    assert "Land" in md
