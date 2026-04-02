"""Intent classification for orchestrator routing (rule-based + optional LangChain LLM)."""

from __future__ import annotations

import logging
from typing import TypedDict

from pydantic import BaseModel, Field

_log = logging.getLogger(__name__)

# Intent patterns keyed by artifact/domain name.
# Each entry has: primary_intent (new vocab), target_artifacts, keywords, triggers, phase_compatibility.
INTENT_PATTERNS = {
    "requirements": {
        "primary_intent": "create",
        "target_artifacts": ["requirements"],
        "keywords": ["need", "want", "goal", "problem", "user story", "feature", "mvp", "simple", "details", "defaults"],
        "phase_compatibility": ["*"],
        "triggers": ["clarify", "what if", "constraints", "personal use", "side project", "fill in", "pick for me", "pick everything", "you decide", "you choose", "just pick"],
    },
    "architecture": {
        "primary_intent": "create",
        "target_artifacts": ["architecture"],
        "keywords": ["architecture", "tech stack", "database", "api", "technology", "technologies", "backend", "frontend", "stack"],
        "phase_compatibility": ["requirements_complete", "architecture_complete", "planning_complete"],
        "triggers": ["diagram", "structure", "how does"],
    },
    "mockups": {
        "primary_intent": "create",
        "target_artifacts": ["mockups"],
        "keywords": ["ui", "screen", "flow", "wireframe", "design", "mockup", "mockups", "prototype"],
        "phase_compatibility": ["requirements_complete", "architecture_complete", "planning_complete", "design_complete"],
        "triggers": ["looks like", "user journey"],
    },
    "roadmap": {
        "primary_intent": "create",
        "target_artifacts": ["roadmap"],
        "keywords": ["roadmap", "timeline", "milestone", "sprint"],
        "phase_compatibility": ["requirements_complete", "architecture_complete", "planning_complete", "design_complete"],
        "triggers": ["how long", "when", "priority"],
    },
    "export": {
        "primary_intent": "export",
        "target_artifacts": [],
        "keywords": ["export", "download", "document", "pdf"],
        "phase_compatibility": ["architecture_complete", "planning_complete", "design_complete", "exportable"],
        "triggers": ["save as", "download as"],
    },
}

# Map pattern key → agent ids (used by rule-based classifier).
INTENT_TO_AGENTS: dict[str, list[str]] = {
    "requirements": ["requirements_collector"],
    "architecture": ["project_architect"],
    "mockups": ["mockup_agent"],
    "roadmap": ["execution_planner"],
    "export": ["exporter"],
}


class IntentResult(TypedDict, total=False):
    """Result of intent classification."""
    primary_intent: str           # create | update | inspect | export | general_inquiry | unknown
    target_artifacts: list[str]   # e.g. ["architecture"], ["requirements", "mockups"]
    requires_agents: list[str]
    confidence: float
    expand_downstream: bool  # If False, run only requested agents (+ deps); no downstream expansion. Default True.
    full_stack_refresh: bool  # True → replan full artifact chain (req → arch → roadmap → mockups) on update


class IntentResultModel(BaseModel):
    """Pydantic model for LangChain structured output (intent classification)."""
    primary_intent: str = Field(
        description="One of: create, update, inspect, export, general_inquiry, or unknown"
    )
    target_artifacts: list[str] = Field(
        default_factory=list,
        description=(
            "List of artifact names targeted by this intent. "
            "e.g. ['architecture'], ['requirements', 'mockups']. "
            "Empty list for general_inquiry, unknown, or export."
        ),
    )
    requires_agents: list[str] = Field(
        description=(
            "List of agent ids that should handle this request. "
            "Use ONE agent for narrow requests ('only tech stack'). "
            "Use MULTIPLE when user asks for several things (e.g. tech stack and roadmap "
            "-> project_architect, execution_planner)."
        )
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0 to 1.0")
    expand_downstream: bool = Field(
        default=True,
        description=(
            "If True, system will also run downstream agents (e.g. architect -> planner -> mockup). "
            "Set to False when user asks for ONLY a specific output "
            "(e.g. 'only update the tech stack', 'just the architecture')."
        ),
    )
    full_stack_refresh: bool = Field(
        default=False,
        description=(
            "Set True when the user wants to refresh the ENTIRE project (e.g. 'update the full', "
            "'migrate stack', 'redo everything', 'refresh all deliverables'). "
            "Use with primary_intent='update' and target all artifacts, or alone for orchestrator to expand."
        ),
    )


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
1. File/output request → export. If the user asks for a file to download or a format (pdf, markdown, md file, "give me a pdf", "export", "download", "save as"), set primary_intent="export", target_artifacts=[], requires_agents=["exporter"], expand_downstream=false. Never treat these as mockup or other intents.
2. "Fill in / pick for me" → requirements first. If the user says they want you to "fill in the details", "pick everything for me", "you decide", "just pick", "use defaults", "fill in all the details", that is create/requirements. Set primary_intent="create", target_artifacts=["requirements"], requires_agents=["requirements_collector"]. If they also ask for something else (e.g. "and give me a tech stack"), still include requirements_collector first: requires_agents=["requirements_collector", "project_architect"] (or the other agent they asked for).
3. Narrow request → one agent, no downstream. "Just the tech stack", "only an ERD", "give me a pdf", "only update architecture" → requires_agents = only that agent, expand_downstream=false.
4. Multiple asks → multiple agents. "Tech stack and roadmap", "architecture and wireframes" → requires_agents = both agent ids, expand_downstream=true unless they said "only" or "just".
5. General/content request → one or more agents, expand_downstream=true. "Give me a diagram", "what's the tech stack", "show me wireframes" (no file format) → pick the right agent(s); downstream expansion is fine.
6. Project status/progress question → primary_intent="general_inquiry", target_artifacts=[], requires_agents=[], confidence medium-high. Use this when the user asks about what has been done, where we are in the process, what decisions were made, a summary of the project, or any question the orchestrator can answer from project state alone — WITHOUT needing to run an agent.
7. True chit-chat with no project relevance → primary_intent="unknown", target_artifacts=[], requires_agents=[], confidence low. Only use unknown when the message has nothing to do with the project at all.
8. Full project / stack migration refresh → update all core artifacts. If the user says things like "update the full", "full update", "update everything", "refresh everything", "redo the whole project", "migrate from X to Y" (framework/stack change affecting the whole plan), set primary_intent="update", target_artifacts=["requirements","architecture","roadmap","mockups"], requires_agents=[], expand_downstream=false, full_stack_refresh=true. Narrow stack tweaks ("only tech stack", "just the backend") stay single-artifact update with full_stack_refresh=false.

For primary_intent use: create (produce a new artifact), update (refine/regenerate existing artifact), inspect (query state without running agents), export (produce downloadable file), general_inquiry (project status/progress), or unknown.

Output: primary_intent, target_artifacts (list of artifact names: requirements/architecture/roadmap/mockups or [] for export/general/unknown), requires_agents (list of agent ids above), confidence (0.0-1.0), expand_downstream (bool), full_stack_refresh (bool)."""


_FULL_STACK_MESSAGE_PHRASES = (
    "update the full",
    "full update",
    "update everything",
    "refresh everything",
    "redo everything",
    "full refresh",
    "update all",
    "whole project",
    "entire project",
    "migrate from",
    "rewrite everything",
    "redesign everything",
)


def user_message_implies_full_stack_refresh(user_input: str) -> bool:
    """True when the user message suggests refreshing all core deliverables (heuristic fallback)."""
    t = (user_input or "").lower().strip()
    if not t:
        return False
    return any(p in t for p in _FULL_STACK_MESSAGE_PHRASES)


def apply_full_stack_intent_overrides(user_input: str, result: IntentResult) -> IntentResult:
    """Map broad refresh phrasing to a full-stack update intent when the classifier missed it."""
    if not user_message_implies_full_stack_refresh(user_input):
        return result
    out: IntentResult = dict(result)
    out["primary_intent"] = "update"
    out["target_artifacts"] = ["requirements", "architecture", "roadmap", "mockups"]
    out["requires_agents"] = []
    out["expand_downstream"] = False
    out["full_stack_refresh"] = True
    return out


# When the current message clearly asks for a file/export, prefer export (avoids tie with mockup from context).
_EXPORT_IN_MESSAGE = ("pdf", "markdown", ".md", " md file", "export", "download", "save as")


def _current_message_wants_export(user_input: str) -> bool:
    if not (user_input or "").strip():
        return False
    lower = (user_input or "").lower().strip()
    return any(s in lower for s in _EXPORT_IN_MESSAGE)


_EXPORT_ALLOWED_PHASES = {
    "architecture_complete",
    "planning_complete",
    "design_complete",
    "exportable",
}


def _override_export_if_requested(user_input: str, result: IntentResult, current_phase: str = "") -> IntentResult:
    """If the current message clearly asks for PDF/export but result is not export, override to export.
    Only applies when the project is past the requirements stage to prevent premature exporter invocation.
    """
    if not _current_message_wants_export(user_input):
        return result
    if current_phase not in _EXPORT_ALLOWED_PHASES:
        return result
    agents = list(result.get("requires_agents") or [])
    if "exporter" in agents:
        return result
    return IntentResult(
        primary_intent="export",
        target_artifacts=[],
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
                target_artifacts=[],
                requires_agents=[],
                confidence=0.0,
            )

        scored_intents: list[tuple[str, int, int]] = []

        for pattern_key, pattern in INTENT_PATTERNS.items():
            phases = pattern.get("phase_compatibility") or []
            if "*" not in phases and current_phase not in phases:
                continue
            keywords = pattern.get("keywords") or []
            triggers = pattern.get("triggers") or []
            score_current = sum(1 for k in keywords + triggers if k in current_text)
            score_history = sum(1 for k in keywords + triggers if k in history_text)
            scored_intents.append((pattern_key, score_current, score_history))

        any_current_match = any(score_current > 0 for _, score_current, _ in scored_intents)
        best_pattern: str | None = None
        best_score = 0
        best_current_score = 0
        for pattern_key, score_current, score_history in scored_intents:
            score = score_current if any_current_match else score_history
            if score > best_score:
                best_score = score
                best_pattern = pattern_key
                best_current_score = score_current

        if best_pattern is None:
            # Check for general project-status/progress questions before falling back to unknown.
            general_inquiry_keywords = [
                "progress", "status", "so far", "what have we", "what did we",
                "where are we", "summary", "summarize", "remind me", "what's been done",
                "what has been done", "what phase", "how is the project", "what decisions",
                "what features", "what we decided", "overview", "recap",
            ]
            if any(kw in current_text for kw in general_inquiry_keywords):
                return apply_full_stack_intent_overrides(
                    user_input,
                    IntentResult(
                        primary_intent="general_inquiry",
                        target_artifacts=[],
                        requires_agents=[],
                        confidence=0.7,
                    ),
                )
            return apply_full_stack_intent_overrides(
                user_input,
                IntentResult(
                    primary_intent="unknown",
                    target_artifacts=[],
                    requires_agents=[],
                    confidence=0.0,
                ),
            )

        pattern = INTENT_PATTERNS[best_pattern]
        agents = INTENT_TO_AGENTS.get(best_pattern, [])
        primary_intent = pattern.get("primary_intent", "create")
        target_artifacts = list(pattern.get("target_artifacts") or [])
        confidence = min(1.0, 0.3 + 0.2 * (best_current_score if best_current_score > 0 else best_score))
        return apply_full_stack_intent_overrides(
            user_input,
            IntentResult(
                primary_intent=primary_intent,
                target_artifacts=target_artifacts,
                requires_agents=list(agents),
                confidence=confidence,
                expand_downstream=True,
            ),
        )

    def _build_prompt(
        self,
        user_input: str,
        current_phase: str,
        conversation_history: list[dict] | None,
    ) -> str:
        """Build the LLM classification prompt string."""
        conversation_context = _format_conversation_for_intent(conversation_history)
        return INTENT_CLASSIFY_PROMPT.format(
            current_phase=current_phase,
            conversation_context=conversation_context,
            user_input=(user_input or "").strip()[:2000],
        )

    def _parse_llm_result(
        self,
        result: object,
        user_input: str,
        current_phase: str,
    ) -> IntentResult | None:
        """Parse an IntentResultModel into an IntentResult. Returns None on invalid input."""
        if not isinstance(result, IntentResultModel):
            return None
        agents = list(getattr(result, "requires_agents", None) or [])
        if isinstance(agents, str):
            agents = [agents]
        target_artifacts = list(getattr(result, "target_artifacts", None) or [])
        out = IntentResult(
            primary_intent=getattr(result, "primary_intent", "unknown") or "unknown",
            target_artifacts=target_artifacts,
            requires_agents=agents,
            confidence=float(getattr(result, "confidence", 0.5)),
            expand_downstream=bool(getattr(result, "expand_downstream", True)),
            full_stack_refresh=bool(getattr(result, "full_stack_refresh", False)),
        )
        return apply_full_stack_intent_overrides(
            user_input, _override_export_if_requested(user_input, out, current_phase)
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
                prompt = self._build_prompt(user_input, current_phase, conversation_history)
                result = self._parse_llm_result(
                    self._structured_llm.invoke(prompt), user_input, current_phase
                )
                if result:
                    return result
            except Exception as exc:
                _log.warning("LLM intent classify failed: %s", exc)
        return apply_full_stack_intent_overrides(
            user_input,
            _override_export_if_requested(
                user_input, self._analyze_rule_based(user_input, current_phase, conversation_history), current_phase
            ),
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
                prompt = self._build_prompt(user_input, current_phase, conversation_history)
                result = self._parse_llm_result(
                    await self._structured_llm.ainvoke(prompt), user_input, current_phase
                )
                if result:
                    return result
            except Exception as exc:
                _log.warning("LLM intent classify (async) failed: %s", exc)
        return apply_full_stack_intent_overrides(
            user_input,
            _override_export_if_requested(
                user_input, self._analyze_rule_based(user_input, current_phase, conversation_history), current_phase
            ),
        )