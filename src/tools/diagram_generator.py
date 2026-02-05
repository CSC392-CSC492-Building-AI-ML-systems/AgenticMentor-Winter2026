"""Generates Mermaid.js diagrams from structured inputs."""

from __future__ import annotations

from typing import Iterable


def generate_mermaid(diagram_spec: str) -> str:
    """Return a Mermaid fenced block from raw spec text."""
    return f"```mermaid\n{diagram_spec}\n```"


class DiagramGenerator:
    """Tool wrapper used by agents to generate Mermaid diagram code."""

    async def generate_diagram(
        self,
        type: str,
        context: str,
        participants: Iterable[str] | None = None,
    ) -> str:
        diagram_type = type.strip().lower()
        nodes = [self._safe_node(name) for name in (participants or [])]
        context_label = self._safe_label(context, limit=72)

        if diagram_type in {"c4_context", "c4", "system_context"}:
            user = nodes[0] if len(nodes) > 0 else "User"
            frontend = nodes[1] if len(nodes) > 1 else "Frontend"
            api = nodes[2] if len(nodes) > 2 else "API"
            database = nodes[3] if len(nodes) > 3 else "Database"
            return (
                "flowchart TD\n"
                f"  U[{user}] --> F[{frontend}]\n"
                f"  F --> A[{api}]\n"
                f"  A --> D[{database}]\n"
                f"  A -. context .-> C[{context_label}]"
            )

        if diagram_type in {"erd", "er", "entity_relationship"}:
            return (
                "erDiagram\n"
                "  USERS ||--o{ PROJECTS : owns\n"
                "  PROJECTS ||--o{ TASKS : contains\n"
                "  USERS ||--o{ TASKS : creates\n"
                f"  PROJECTS {{ string context \"{context_label}\" }}"
            )

        if diagram_type == "sequence":
            user = nodes[0] if len(nodes) > 0 else "User"
            frontend = nodes[1] if len(nodes) > 1 else "Frontend"
            api = nodes[2] if len(nodes) > 2 else "API"
            database = nodes[3] if len(nodes) > 3 else "Database"
            return (
                "sequenceDiagram\n"
                f"  participant {user}\n"
                f"  participant {frontend}\n"
                f"  participant {api}\n"
                f"  participant {database}\n"
                f"  {user}->>{frontend}: Submit request\n"
                f"  {frontend}->>{api}: API call\n"
                f"  {api}->>{database}: Query data\n"
                f"  {database}-->>{api}: Result\n"
                f"  {api}-->>{frontend}: Response"
            )

        return f"flowchart LR\n  A[Unsupported diagram type: {diagram_type}]"

    def _safe_node(self, value: str) -> str:
        return "".join(ch for ch in value if ch.isalnum() or ch in {"_", " "}).strip() or "Node"

    def _safe_label(self, value: str, limit: int = 80) -> str:
        cleaned = " ".join(str(value).split())
        cleaned = cleaned.replace('"', "'")
        return cleaned[:limit] if cleaned else "Project context"
