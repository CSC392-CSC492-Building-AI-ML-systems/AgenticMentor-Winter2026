"""Intent classification for orchestrator routing (rule-based + optional LangChain LLM)."""

from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field

INTENT_PATTERNS = {
    "requirements_gathering": {
        "keywords": ["need", "want", "goal", "problem", "user story", "feature", "mvp", "simple", "details", "defaults"],
        "phase_compatibility": ["*"],
        "triggers": ["clarify", "what if", "constraints", "personal use", "side project", "fill in", "pick for me", "pick everything", "you decide", "you choose", "just pick"]
    },
    "architecture_design": {
        "keywords": ["architecture", "tech stack", "database", "api", "technology", "technologies", "backend", "frontend", "stack"],
        "phase_compatibility": ["requirements_complete", "architecture_complete", "planning_complete"],
        "triggers": ["diagram", "structure", "how does"]
    },
    "mockup_creation": {
        "keywords": ["ui", "screen", "flow", "wireframe", "design", "mockup", "mockups", "prototype"],
        "phase_compatibility": ["requirements_complete", "architecture_complete", "planning_complete", "design_complete"],
        "triggers": ["looks like", "user journey"]
    },
    "execution_planning": {
        "keywords": ["roadmap", "timeline", "milestone", "sprint"],
        "phase_compatibility": ["requirements_complete", "architecture_complete", "planning_complete", "design_complete"],
        "triggers": ["how long", "when", "priority"]
    },
    "export": {
        "keywords": ["export", "download", "document", "pdf"],
        "phase_compatibility": ["*"],
        "triggers": ["save as", "download as"]
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


class IntentResult(TypedDict, total=False):
    """Result of intent classification."""
    primary_intent: str
    requires_agents: list[str]
    confidence: float
    expand_downstream: bool  # If False, run only requested agents (+ deps); no downstream expansion. Default True.


class IntentResultModel(BaseModel):
    """Pydantic model for LangChain structured output (intent classification)."""
    primary_intent: str = Field(description="One of: requirements_gathering, architecture_design, mockup_creation, execution_planning, export, or unknown")
    requires_agents: list[str] = Field(description="List of agent ids that should handle this request. Use ONE agent for narrow requests ('only tech stack'). Use MULTIPLE when user asks for several things (e.g. tech stack and roadmap -> project_architect, execution_planner).")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0 to 1.0")
    expand_downstream: bool = Field(default=True, description="If True, system will also run downstream agents (e.g. architect -> planner -> mockup). Set to False when user asks for ONLY a specific output (e.g. 'only update the tech stack', 'just the architecture').")


# Max recent conversation turns to include for intent context (user + assistant pairs).
MAX_RECENT_TURNS_FOR_INTENT = 6

INTENT_CLASSIFY_PROMPT = """You classify the user's intent for a project-planning assistant. Use the full message and conversation context.

Context:
- Project phase: {current_phase}
{conversation_context}

Agents (use these exact ids in requires_agents):
- requirements_collector: gathering or filling in goals, users, features, constraints — also when user says "fill in the details", "pick everything for me", "you decide", "use defaults"
- project_architect: tech stack, ERD/diagrams, API, architecture
- mockup_agent: UI wireframes, screens, visual design
- execution_planner: roadmap, phases, milestones, implementation tasks
- exporter: producing a file for download — PDF, Markdown (.md), or document bundle

User message: "{user_input}"

Rules (apply in order):
1. File/output request → export. If the user asks for a file to download or a format (pdf, markdown, md file, "give me a pdf", "export", "download", "save as"), set primary_intent="export", requires_agents=["exporter"], expand_downstream=false. Never treat these as mockup or other intents.
2. "Fill in / pick for me" → requirements first. If the user says they want you to "fill in the details", "pick everything for me", "you decide", "just pick", "use defaults", "fill in all the details", that is requirements_gathering. Set primary_intent="requirements_gathering", requires_agents=["requirements_collector"]. If they also ask for something else (e.g. "and give me a tech stack"), still include requirements_collector first: requires_agents=["requirements_collector", "project_architect"] (or the other agent they asked for), so the collector runs and can fill in before the next agent.
3. Narrow request → one agent, no downstream. "Just the tech stack", "only an ERD", "give me a pdf", "only update architecture" → requires_agents = only that agent, expand_downstream=false.
4. Multiple asks → multiple agents. "Tech stack and roadmap", "architecture and wireframes" → requires_agents = both agent ids, expand_downstream=true unless they said "only" or "just".
5. General/content request → one or more agents, expand_downstream=true. "Give me a diagram", "what's the tech stack", "show me wireframes" (no file format) → pick the right agent(s); downstream expansion is fine.
6. Unclear or chit-chat → primary_intent="unknown", requires_agents=[], confidence low.

Output: primary_intent (one of: requirements_gathering, architecture_design, mockup_creation, execution_planning, export, unknown), requires_agents (list of agent ids above), confidence (0.0-1.0), expand_downstream (bool)."""


# When the current message clearly asks for a file/export, prefer export (avoids tie with mockup from context).
_EXPORT_IN_MESSAGE = ("pdf", "markdown", ".md", " md file", "export", "download", "save as")


def _current_message_wants_export(user_input: str) -> bool:
    if not (user_input or "").strip():
        return False
    lower = (user_input or "").lower().strip()
    return any(s in lower for s in _EXPORT_IN_MESSAGE)


def _override_export_if_requested(user_input: str, result: IntentResult) -> IntentResult:
    """If the current message clearly asks for PDF/export but result is not export, override to export."""
    if not _current_message_wants_export(user_input):
        return result
    agents = list(result.get("requires_agents") or [])
    if "exporter" in agents:
        return result
    return IntentResult(
        primary_intent="export",
        requires_agents=["exporter"],
        confidence=max(0.9, result.get("confidence", 0.5)),
        expand_downstream=False,
    )


def _format_conversation_for_intent(history: list[dict] | None, max_turns: int = MAX_RECENT_TURNS_FOR_INTENT) -> str:
    """Format recent conversation for the intent-classification prompt. Returns a string for prompt inclusion."""
    if not history:
        return "Recent conversation: (none)"
    turns = history[-max_turns:] if len(history) > max_turns else history
    lines = []
    for t in turns:
        role = (t.get("role") or "user").lower()
        content = (t.get("content") or "").strip()
        if not content:
            continue
        prefix = "User" if role == "user" else "Assistant"
        lines.append(f"{prefix}: {content[:500]}")
    if not lines:
        return "Recent conversation: (none)"
    return "Recent conversation:\n" + "\n".join(lines)


def _conversation_context_for_rules(history: list[dict] | None, user_input: str, max_turns: int = 3) -> str:
    """Combine current message with last few turns for rule-based keyword matching."""
    parts = [user_input or ""]
    if history:
        for t in reversed(history[-max_turns * 2 :]):
            content = (t.get("content") or "").strip()
            if content:
                parts.append(content)
    return " ".join(parts).lower().strip()


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

    def _analyze_rule_based(
        self,
        user_input: str,
        current_phase: str,
        conversation_history: list[dict] | None = None,
    ) -> IntentResult:
        """Rule-based classification using INTENT_PATTERNS, phase, and optional conversation context."""
        current_text = (user_input or "").lower().strip()
        history_text = _conversation_context_for_rules(conversation_history, "")
        if not current_text:
            return IntentResult(
                primary_intent="unknown",
                requires_agents=[],
                confidence=0.0,
            )

        scored_intents: list[tuple[str, int, int]] = []

        for intent_name, pattern in INTENT_PATTERNS.items():
            phases = pattern.get("phase_compatibility") or []
            if "*" not in phases and current_phase not in phases:
                continue
            keywords = pattern.get("keywords") or []
            triggers = pattern.get("triggers") or []
            score_current = sum(1 for k in keywords + triggers if k in current_text)
            score_history = sum(1 for k in keywords + triggers if k in history_text)
            scored_intents.append((intent_name, score_current, score_history))

        any_current_match = any(score_current > 0 for _, score_current, _ in scored_intents)
        best_intent: str | None = None
        best_score = 0
        best_current_score = 0
        for intent_name, score_current, score_history in scored_intents:
            score = score_current if any_current_match else score_history
            if score > best_score:
                best_score = score
                best_intent = intent_name
                best_current_score = score_current

        if best_intent is None:
            return IntentResult(
                primary_intent="unknown",
                requires_agents=[],
                confidence=0.0,
            )

        agents = INTENT_TO_AGENTS.get(best_intent, [])
        confidence = min(1.0, 0.3 + 0.2 * (best_current_score if best_current_score > 0 else best_score))
        return IntentResult(
            primary_intent=best_intent,
            requires_agents=list(agents),
            confidence=confidence,
        )

    def analyze(
        self,
        user_input: str,
        current_phase: str,
        conversation_history: list[dict] | None = None,
    ) -> IntentResult:
        """
        Classify user message into primary intent and required agents.
        Uses LLM (LangChain) when available, else rule-based.
        conversation_history: optional list of {"role": "user"|"assistant", "content": "..."} for context.
        """
        if self._structured_llm is not None:
            try:
                conversation_context = _format_conversation_for_intent(conversation_history)
                prompt = INTENT_CLASSIFY_PROMPT.format(
                    current_phase=current_phase,
                    conversation_context=conversation_context,
                    user_input=(user_input or "").strip()[:2000],
                )
                result = self._structured_llm.invoke(prompt)
                if isinstance(result, IntentResultModel):
                    agents = getattr(result, "requires_agents", []) or []
                    if isinstance(agents, str):
                        agents = [agents]
                    expand = getattr(result, "expand_downstream", True)
                    out = IntentResult(
                        primary_intent=getattr(result, "primary_intent", "unknown") or "unknown",
                        requires_agents=list(agents),
                        confidence=float(getattr(result, "confidence", 0.5)),
                        expand_downstream=bool(expand),
                    )
                    return _override_export_if_requested(user_input, out)
            except Exception:
                pass
        return _override_export_if_requested(
            user_input, self._analyze_rule_based(user_input, current_phase, conversation_history)
        )

    async def analyze_async(
        self,
        user_input: str,
        current_phase: str,
        conversation_history: list[dict] | None = None,
    ) -> IntentResult:
        """Async version: use LLM when available, else rule-based. Uses conversation_history for context."""
        if self._structured_llm is not None and hasattr(self._structured_llm, "ainvoke"):
            try:
                conversation_context = _format_conversation_for_intent(conversation_history)
                prompt = INTENT_CLASSIFY_PROMPT.format(
                    current_phase=current_phase,
                    conversation_context=conversation_context,
                    user_input=(user_input or "").strip()[:2000],
                )
                result = await self._structured_llm.ainvoke(prompt)
                if isinstance(result, IntentResultModel):
                    agents = getattr(result, "requires_agents", []) or []
                    if isinstance(agents, str):
                        agents = [agents]
                    expand = getattr(result, "expand_downstream", True)
                    out = IntentResult(
                        primary_intent=getattr(result, "primary_intent", "unknown") or "unknown",
                        requires_agents=list(agents),
                        confidence=float(getattr(result, "confidence", 0.5)),
                        expand_downstream=bool(expand),
                    )
                    return _override_export_if_requested(user_input, out)
            except Exception:
                pass
        return _override_export_if_requested(
            user_input, self._analyze_rule_based(user_input, current_phase, conversation_history)
        )
