"""Agent registry metadata: id, requires, produces, phase_compatibility."""

from __future__ import annotations

from typing import Any

AGENT_STORE: list[dict[str, Any]] = [
    {
        "id": "requirements_collector",
        "name": "Requirements Collector",
        "description": "Asks structured questions to gather goals, constraints, features. Updates requirements state.",
        "interaction_mode": "conversational",
        "supports_selective_regen": False,
        "expensive": False,
        "requires": [],
        "produces": ["requirements"],
        "satisfies_intents": ["create", "update"],
        "target_artifacts": ["requirements"],
        "phase_compatibility": ["initialization", "discovery", "*"],
    },
    {
        "id": "project_architect",
        "name": "Project Architect",
        "description": "Turns requirements into tech stack, system/ER diagrams, API and data model.",
        "interaction_mode": "functional",
        "supports_selective_regen": True,
        "expensive": True,
        "requires": ["requirements"],
        "produces": ["architecture"],
        "satisfies_intents": ["create", "update"],
        "target_artifacts": ["architecture"],
        "phase_compatibility": ["requirements_complete", "architecture_complete"],
    },
    {
        "id": "execution_planner",
        "name": "Execution Planner Agent",
        "description": "Creates phases, milestones, and implementation steps from architecture.",
        "interaction_mode": "functional",
        "supports_selective_regen": True,
        "expensive": True,
        "requires": ["architecture"],
        "produces": ["roadmap"],
        "satisfies_intents": ["create", "update"],
        "target_artifacts": ["roadmap"],
        # Allow execution planner to be used again after design, as long as architecture exists.
        "phase_compatibility": ["requirements_complete", "architecture_complete", "planning_complete", "design_complete"],
    },
    {
        "id": "mockup_agent",
        "name": "Mockup Agent",
        "description": "Generates UI wireframes and Figma-ready layouts.",
        "interaction_mode": "functional",
        "supports_selective_regen": True,
        "expensive": True,
        "requires": ["requirements", "architecture"],
        "produces": ["mockups"],
        "satisfies_intents": ["create", "update"],
        "target_artifacts": ["mockups"],
        "phase_compatibility": [
            "requirements_complete",
            "architecture_complete",
            "planning_complete",
            "design_complete",
        ],
    },
    {
        "id": "exporter",
        "name": "Exporter",
        "description": "Bundles all artifacts into Markdown, PDF, or GitHub-ready docs.",
        "interaction_mode": "functional",
        "supports_selective_regen": False,
        "expensive": False,
        "requires": ["*"],
        "produces": ["export"],
        "satisfies_intents": ["export"],
        "target_artifacts": [],
        "phase_compatibility": ["*"],
    },
]

# Default full pipeline when intent is unknown or classification fails (dependency order).
# Convenience constant — not authoritative for ordering; use _resolve_upstream() for that.
FULL_PIPELINE_AGENT_IDS: list[str] = [
    "requirements_collector",
    "project_architect",
    "execution_planner",
    "mockup_agent",
    "exporter",
]

# Declarative phase configuration: allowed intents, agents, and required artifacts per phase.
PHASE_CONFIG: dict[str, dict] = {
    "initialization": {
        "allowed_intents": ["create", "inspect", "general_inquiry", "unknown"],
        "allowed_agents": ["requirements_collector"],
        "required_artifacts": [],
        "transitions_to": None,
    },
    "requirements_complete": {
        "allowed_intents": ["create", "update", "inspect", "export", "general_inquiry"],
        "allowed_agents": ["requirements_collector", "project_architect", "mockup_agent", "execution_planner", "exporter"],
        "required_artifacts": ["requirements"],
        "transitions_to": None,
    },
    "architecture_complete": {
        "allowed_intents": ["create", "update", "inspect", "export", "general_inquiry"],
        "allowed_agents": ["requirements_collector", "project_architect", "execution_planner", "mockup_agent", "exporter"],
        "required_artifacts": ["requirements", "architecture"],
        "transitions_to": None,
    },
    "planning_complete": {
        "allowed_intents": ["create", "update", "inspect", "export", "general_inquiry"],
        "allowed_agents": ["requirements_collector", "project_architect", "execution_planner", "mockup_agent", "exporter"],
        "required_artifacts": ["requirements", "architecture", "roadmap"],
        "transitions_to": None,
    },
    "design_complete": {
        "allowed_intents": ["create", "update", "inspect", "export", "general_inquiry"],
        "allowed_agents": ["requirements_collector", "project_architect", "execution_planner", "mockup_agent", "exporter"],
        "required_artifacts": ["requirements", "architecture", "roadmap", "mockups"],
        "transitions_to": None,
    },
    "exportable": {
        "allowed_intents": ["update", "inspect", "export", "general_inquiry"],
        # After export, allow upstream agents to run again so the user can
        # tweak architecture/roadmap/mockups and optionally re-export.
        "allowed_agents": [
            "requirements_collector",
            "project_architect",
            "execution_planner",
            "mockup_agent",
            "exporter",
        ],
        "required_artifacts": ["requirements", "architecture", "roadmap", "mockups"],
        "transitions_to": None,
    },
}

# Agent-ID → next phase (replaces PHASE_TRANSITION_MAP in master_agent.py).
AGENT_PHASE_TRANSITIONS: dict[str, str] = {
    "requirements_collector": "requirements_complete",
    "project_architect": "architecture_complete",
    "execution_planner": "planning_complete",
    "mockup_agent": "design_complete",
    "exporter": "exportable",
}

# Valid phase names — use as a guard at phase transition time.
VALID_PHASES: set[str] = set(PHASE_CONFIG.keys())


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


def get_agent_for_intent(intent: str, artifact: str) -> str | None:
    """Return agent id that satisfies the given intent for the given artifact."""
    for entry in AGENT_STORE:
        if artifact in (entry.get("produces") or []) and intent in (entry.get("satisfies_intents") or []):
            return entry.get("id")
    return None
