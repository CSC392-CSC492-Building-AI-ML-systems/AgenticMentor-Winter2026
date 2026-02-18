"""Intent classification for orchestrator routing (rule-based + optional LangChain LLM)."""

from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field

INTENT_PATTERNS = {
    "requirements_gathering": {
        "keywords": ["need", "want", "goal", "problem", "user story"],
        "phase_compatibility": ["initialization", "discovery"],
        "triggers": ["clarify", "what if", "constraints"]
    },
    "architecture_design": {
        "keywords": ["architecture", "tech stack", "database", "API"],
        "phase_compatibility": ["requirements_complete"],
        "triggers": ["diagram", "structure", "how does"]
    },
    "mockup_creation": {
        "keywords": ["UI", "screen", "flow", "wireframe", "design"],
        "phase_compatibility": ["requirements_complete"],
        "triggers": ["looks like", "user journey"]
    },
    "execution_planning": {
        "keywords": ["roadmap", "timeline", "milestone", "sprint"],
        "phase_compatibility": ["architecture_complete"],
        "triggers": ["how long", "when", "priority"]
    },
    "export": {
        "keywords": ["export", "download", "document", "PDF"],
        "phase_compatibility": ["*"],
        "triggers": ["generate", "compile"]
    }
}

# Map primary_intent -> agent ids (used by IntentClassifier)
INTENT_TO_AGENTS: dict[str, list[str]] = {
    "requirements_gathering": ["requirements_collector"],
    "architecture_design": ["project_architect"],
    "mockup_creation": ["mockup_agent"],
    "execution_planning": ["execution_planner"],
    "export": ["exporter"],
}


class IntentResult(TypedDict):
    """Result of intent classification."""
    primary_intent: str
    requires_agents: list[str]
    confidence: float


class IntentResultModel(BaseModel):
    """Pydantic model for LangChain structured output (intent classification)."""
    primary_intent: str = Field(description="One of: requirements_gathering, architecture_design, mockup_creation, execution_planning, export, or unknown")
    requires_agents: list[str] = Field(description="List of agent ids that should handle this request, e.g. ['requirements_collector'] or ['project_architect']")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0 to 1.0")


INTENT_CLASSIFY_PROMPT = """You are an intent classifier for a project-planning assistant.
Current project phase: {current_phase}

Available intents and the agents that handle them:
- requirements_gathering -> requirements_collector (user describing goals, needs, constraints)
- architecture_design -> project_architect (user asking for tech stack, diagrams, API, architecture)
- mockup_creation -> mockup_agent (user asking for UI, wireframes, screens)
- execution_planning -> execution_planner (user asking for roadmap, timeline, milestones)
- export -> exporter (user asking to export, download, document, PDF)

User message: "{user_input}"

Return the primary_intent, requires_agents (list of agent ids above), and confidence (0.0-1.0). Use "unknown" and empty requires_agents only if the message does not match any intent."""


class IntentClassifier:
    """Intent classifier: rule-based by default, optional LangChain LLM when llm is provided."""

    def __init__(self, llm: object | None = None):
        """
        Args:
            llm: Optional LangChain LLM (e.g. ChatGoogleGenerativeAI). If set, classify using LLM structured output; else rule-based.
        """
        self._llm = llm
        self._structured_llm = None
        if llm is not None and hasattr(llm, "with_structured_output"):
            self._structured_llm = llm.with_structured_output(IntentResultModel)

    def _analyze_rule_based(self, user_input: str, current_phase: str) -> IntentResult:
        """Rule-based classification using INTENT_PATTERNS and phase."""
        text = (user_input or "").lower().strip()
        if not text:
            return IntentResult(
                primary_intent="unknown",
                requires_agents=[],
                confidence=0.0,
            )

        best_intent: str | None = None
        best_score = 0

        for intent_name, pattern in INTENT_PATTERNS.items():
            phases = pattern.get("phase_compatibility") or []
            if "*" not in phases and current_phase not in phases:
                continue
            keywords = pattern.get("keywords") or []
            triggers = pattern.get("triggers") or []
            score = sum(1 for k in keywords + triggers if k in text)
            if score > best_score:
                best_score = score
                best_intent = intent_name

        if best_intent is None:
            return IntentResult(
                primary_intent="unknown",
                requires_agents=[],
                confidence=0.0,
            )

        agents = INTENT_TO_AGENTS.get(best_intent, [])
        confidence = min(1.0, 0.3 + 0.2 * best_score)
        return IntentResult(
            primary_intent=best_intent,
            requires_agents=list(agents),
            confidence=confidence,
        )

    def analyze(self, user_input: str, current_phase: str) -> IntentResult:
        """
        Classify user message into primary intent and required agents.
        Uses LLM (LangChain) when available, else rule-based.
        """
        if self._structured_llm is not None:
            try:
                prompt = INTENT_CLASSIFY_PROMPT.format(
                    current_phase=current_phase,
                    user_input=(user_input or "").strip()[:2000],
                )
                result = self._structured_llm.invoke(prompt)
                if isinstance(result, IntentResultModel):
                    agents = getattr(result, "requires_agents", []) or []
                    if isinstance(agents, str):
                        agents = [agents]
                    return IntentResult(
                        primary_intent=getattr(result, "primary_intent", "unknown") or "unknown",
                        requires_agents=list(agents),
                        confidence=float(getattr(result, "confidence", 0.5)),
                    )
            except Exception:
                pass
        return self._analyze_rule_based(user_input, current_phase)

    async def analyze_async(self, user_input: str, current_phase: str) -> IntentResult:
        """Async version: use LLM when available, else rule-based."""
        if self._structured_llm is not None and hasattr(self._structured_llm, "ainvoke"):
            try:
                prompt = INTENT_CLASSIFY_PROMPT.format(
                    current_phase=current_phase,
                    user_input=(user_input or "").strip()[:2000],
                )
                result = await self._structured_llm.ainvoke(prompt)
                if isinstance(result, IntentResultModel):
                    agents = getattr(result, "requires_agents", []) or []
                    if isinstance(agents, str):
                        agents = [agents]
                    return IntentResult(
                        primary_intent=getattr(result, "primary_intent", "unknown") or "unknown",
                        requires_agents=list(agents),
                        confidence=float(getattr(result, "confidence", 0.5)),
                    )
            except Exception:
                pass
        return self._analyze_rule_based(user_input, current_phase)