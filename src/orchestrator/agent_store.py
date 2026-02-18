"""Agent registry metadata: id, requires, produces, phase_compatibility."""

from __future__ import annotations

from typing import Any

AGENT_STORE: list[dict[str, Any]] = [
    {
        "id": "requirements_collector",
        "name": "Requirements Collector",
        "description": "Asks structured questions to gather goals, constraints, features. Updates requirements state.",
        "requires": [],
        "produces": ["requirements"],
        "phase_compatibility": ["initialization", "discovery", "*"],
    },
    {
        "id": "project_architect",
        "name": "Project Architect",
        "description": "Turns requirements into tech stack, system/ER diagrams, API and data model.",
        "requires": ["requirements"],
        "produces": ["architecture"],
        "phase_compatibility": ["requirements_complete", "architecture_complete"],
    },
    {
        "id": "execution_planner",
        "name": "Execution Planner Agent",
        "description": "Creates phases, milestones, and implementation steps from architecture.",
        "requires": ["architecture"],
        "produces": ["roadmap"],
        "phase_compatibility": ["architecture_complete"],
    },
    {
        "id": "mockup_agent",
        "name": "Mockup Agent",
        "description": "Generates UI wireframes and Figma-ready layouts.",
        "requires": ["requirements", "architecture"],
        "produces": ["mockups"],
        "phase_compatibility": ["requirements_complete"],
    },
    {
        "id": "exporter",
        "name": "Exporter",
        "description": "Bundles all artifacts into Markdown, PDF, or GitHub-ready docs.",
        "requires": ["*"],
        "produces": ["export"],
        "phase_compatibility": ["*"],
    },
]

# Default full pipeline when intent is unknown or classification fails (dependency order).
FULL_PIPELINE_AGENT_IDS: list[str] = [
    "requirements_collector",
    "project_architect",
    "execution_planner",
    "mockup_agent",
    "exporter",
]


def get_agent_by_id(agent_id: str) -> dict[str, Any] | None:
    """Return agent store entry for agent_id or None."""
    for entry in AGENT_STORE:
        if entry.get("id") == agent_id:
            return entry
    return None


def get_producer_for_artifact(artifact: str) -> str | None:
    """Return agent id that produces the given artifact, or None."""
    for entry in AGENT_STORE:
        if artifact in (entry.get("produces") or []):
            return entry.get("id")
    return None
