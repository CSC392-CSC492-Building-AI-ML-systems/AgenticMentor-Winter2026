"""Unit tests for ExporterAgent and export document builder."""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.agents.exporter_agent import (
    ExporterAgent,
    build_export_markdown,
    _architecture_to_markdown,
    _requirements_to_markdown,
    _roadmap_to_markdown,
    _mockups_to_markdown,
)


def test_build_export_markdown_empty_context():
    out = build_export_markdown({}, project_name="My Project")
    assert "My Project" in out
    assert "Exported:" in out


def test_build_export_markdown_with_requirements():
    context = {
        "project_name": "Test App",
        "requirements": {
            "functional": ["Login", "Dashboard"],
            "constraints": ["Python backend"],
        },
    }
    out = build_export_markdown(context)
    assert "Test App" in out
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


def test_mockups_to_markdown():
    md = _mockups_to_markdown([{"screen_name": "Home", "user_flow": "Landing", "wireframe_code": "div", "interactions": ["click"]}])
    assert "Mockups" in md
    assert "Home" in md
    assert "Landing" in md


def test_exporter_agent_generate_returns_structure():
    agent = ExporterAgent()
    context = {
        "session_id": "test-session",
        "project_name": "Unit Test Project",
        "requirements": {"functional": ["Requirement one"]},
        "architecture": {},
        "roadmap": {},
        "mockups": [],
    }
    result = asyncio.run(agent._generate({"destination": None}, context, ["markdown_formatter"]))
    assert "markdown" in result
    assert "Unit Test Project" in result["markdown"]
    assert "Requirement one" in result["markdown"]
    assert result.get("state_delta") == {}
    assert "files_written" in result


def test_exporter_agent_writes_file_when_destination_set(tmp_path):
    agent = ExporterAgent()
    dest = str(tmp_path / "out.md")
    context = {"project_name": "File Test", "requirements": {}}
    result = asyncio.run(agent._generate({"destination": dest}, context, []))
    assert dest in result["files_written"]
    assert (tmp_path / "out.md").read_text(encoding="utf-8").strip().startswith("# File Test")


def test_exporter_agent_get_quality_criteria():
    agent = ExporterAgent()
    criteria = agent._get_quality_criteria()
    assert "feasibility" in criteria
    assert "clarity" in criteria
    assert "completeness" in criteria
