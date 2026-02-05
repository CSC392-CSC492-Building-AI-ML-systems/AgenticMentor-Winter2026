"""Token optimization utilities for context extraction."""

from __future__ import annotations

from typing import Any, Dict


class ContextExtractor:
    """
    Intelligent context window management.
    """

    AGENT_CONTEXT_REQUIREMENTS = {
        "requirements_collector": [
            "requirements.functional",
            "requirements.non_functional",
            "requirements.gaps",
        ],
        "project_architect": [
            "requirements.*",
            "architecture.tech_stack",
        ],
        "mockup_agent": [
            "requirements.user_stories",
            "architecture.tech_stack.frontend",
        ],
        "execution_planner_agent": [
            "requirements.*",
            "architecture.*",
            "mockups[*].screen_name",
        ],
        "exporter": ["*"],
    }

    def extract(self, state: Any, agent_name: str) -> Dict[str, Any]:
        """
        Extract only relevant fragments for the target agent.
        """
        requirements = self.AGENT_CONTEXT_REQUIREMENTS.get(agent_name, [])
        context: Dict[str, Any] = {}

        for req in requirements:
            if req == "*":
                if hasattr(state, "model_dump"):
                    return state.model_dump()
                if hasattr(state, "dict"):
                    return state.dict()
                return dict(state)

            if ".*" in req:
                base_path = req.replace(".*", "")
                context[base_path] = self._get_nested(state, base_path)
            elif "[*]" in req:
                base_path = req.split("[*]")[0]
                items = self._get_nested(state, base_path) or []
                context[base_path] = [self._summarize_item(item) for item in items]
            else:
                context[req] = self._get_nested(state, req)

        return context

    def _get_nested(self, obj: Any, path: str) -> Any:
        keys = path.split(".")
        value = obj
        for key in keys:
            if value is None:
                return None
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = getattr(value, key, None)
        return value

    def _summarize_item(self, item: Any) -> Any:
        if hasattr(item, "model_dump"):
            data = item.model_dump()
        elif hasattr(item, "dict"):
            data = item.dict()
        else:
            return item

        if isinstance(data, dict):
            keys = list(data.keys())[:3]
            return {key: data.get(key) for key in keys}
        return data

    def summarize_text(self, text: str, max_chars: int = 2500) -> str:
        if len(text) <= max_chars:
            return text
        return f"{text[:max_chars].rstrip()}..."
