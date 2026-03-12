"""Creates an organized, detailed project execution plan using LangGraph for structured generation."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, TypedDict

from pydantic import BaseModel, Field, ValidationError
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

from src.agents.base_agent import BaseAgent
from src.protocols.review_protocol import ReviewResult
from src.utils.config import settings
from src.state.project_state import (
    ArchitectureDefinition,
    ImplementationTask,
    Milestone,
    Phase,
    Roadmap,
    Sprint,
    ProjectState,
)


# ============================================================================
# Pydantic Schemas for LLM Structured Output
# ============================================================================

class PlannerRegenPlan(BaseModel):
    """Determines which roadmap components need regeneration."""

    components_to_regenerate: List[str] = Field(
        description="Components to regenerate: phases, milestones, tasks, sprints"
    )
    reasoning: str = Field(
        description="Brief explanation of why these components need regeneration"
    )
    preserve_components: List[str] = Field(
        default_factory=list,
        description="Components to keep unchanged from existing roadmap",
    )


# ============================================================================
# LangGraph State Definition
# ============================================================================

class PlannerState(TypedDict, total=False):
    """State passed through the LangGraph execution planner workflow."""

    # Inputs
    requirements: dict
    architecture: dict
    existing_roadmap: Optional[dict]
    user_request: Optional[str]

    # LLM-determined regeneration plan
    regen_plan: Optional[PlannerRegenPlan]

    # Generated/preserved outputs
    phases: Optional[List[dict]]
    milestones: Optional[List[dict]]
    implementation_tasks: Optional[List[dict]]
    sprints: Optional[List[dict]]
    critical_path: Optional[str]
    external_resources: Optional[List[str]]


# ============================================================================
# ExecutionPlannerAgent with LangGraph
# ============================================================================

class ExecutionPlannerAgent(BaseAgent):
    """
    Creates a structured execution plan for the project.

    - Input: Architect agent output (architecture); uses requirements for context.
    - Output: Phases, milestones, ordered implementation tasks with dependencies
      and relevant external resources. Consumed by Reviewer and Exporter agents.

    Uses LangGraph for multi-step structured generation (like ProjectArchitectAgent).
    Supports selective regeneration: preserve unchanged components when given an
    existing roadmap + user request.
    """

    description = (
        "Creates an organized and detailed checklist of steps, phases, and milestones "
        "for the project, including dependencies and external resources."
    )

    def __init__(
        self,
        state_manager: Any = None,
        llm_client: Any = None,
        review_config: Optional[dict] = None,
    ) -> None:
        # Always require LLM - create one using settings if not provided
        if llm_client is None:
            try:
                llm_client = ChatGoogleGenerativeAI(
                    model=settings.model_name,
                    temperature=settings.model_temperature,
                    max_output_tokens=8192,  # task lists can be large; override 4096 default
                    google_api_key=settings.gemini_api_key,
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to initialize LLM client for Execution Planner Agent: {e}. "
                    "This agent requires an LLM to function. Please ensure GEMINI_API_KEY is set in your .env file."
                ) from e

        super().__init__(
            name="Execution Planner",
            llm_client=llm_client,
            review_config=review_config or {"min_score": 0.7},
        )
        self.state_manager = state_manager
        self._graph = self._build_graph()

    # ========================================================================
    # Main Entry Point
    # ========================================================================

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build execution plan from architecture and requirements.

        Supports two modes:
        1. Full generation: No existing_roadmap provided.
        2. Selective regeneration: existing_roadmap + user_request provided —
           only changed components are regenerated; others are preserved.
        """
        architecture = self._extract_architecture(input_data)
        requirements = self._extract_requirements(input_data)

        # Prepare initial state for LangGraph
        initial_state: PlannerState = {
            "requirements": requirements,
            "architecture": architecture,
            "existing_roadmap": input_data.get("existing_roadmap"),
            "user_request": input_data.get("user_request"),
        }

        # Run the LangGraph workflow
        # print("  [1/4] Analyzing impact and determining regeneration plan...", flush=True)
        final_state = await self._graph.ainvoke(initial_state)
        # print("  [4/4] Building execution plan output...", flush=True)

        # Build typed Pydantic models from final state
        phases = [
            Phase(**p) if isinstance(p, dict) else p
            for p in (final_state.get("phases") or [])
        ]
        milestones = [
            Milestone(**m) if isinstance(m, dict) else m
            for m in (final_state.get("milestones") or [])
        ]
        implementation_tasks = [
            ImplementationTask(**t) if isinstance(t, dict) else t
            for t in (final_state.get("implementation_tasks") or [])
        ]
        sprints = [
            Sprint(**s) if isinstance(s, dict) else s
            for s in (final_state.get("sprints") or [])
        ]

        roadmap = Roadmap(
            phases=phases,
            milestones=milestones,
            implementation_tasks=implementation_tasks,
            sprints=sprints,
            critical_path=final_state.get("critical_path"),
            external_resources=final_state.get("external_resources") or [],
        )
        roadmap_dict = roadmap.model_dump()

        # Persist the canonical roadmap fragment in one update. Duplicating this
        # with additional roadmap.* deltas can append repeated list entries when
        # regeneration runs multiple times.
        state_delta = {
            "roadmap": roadmap_dict,
        }

        return {
            "summary": self._roadmap_summary(roadmap_dict),
            "roadmap": roadmap_dict,
            "execution_plan": roadmap_dict,  # backward-compatible key
            "state_delta": state_delta,
        }

    # ========================================================================
    # LangGraph Construction
    # ========================================================================

    def _build_graph(self) -> StateGraph:
        """Construct the LangGraph StateGraph for execution plan generation."""
        graph = StateGraph(PlannerState)

        graph.add_node("analyze_impact", self._analyze_impact_node)
        graph.add_node("generate_phases", self._generate_phases_node)
        graph.add_node("generate_milestones", self._generate_milestones_node)
        graph.add_node("generate_tasks", self._generate_tasks_node)
        graph.add_node("generate_sprints", self._generate_sprints_node)

        graph.set_entry_point("analyze_impact")
        graph.add_edge("analyze_impact", "generate_phases")
        graph.add_edge("generate_phases", "generate_milestones")
        graph.add_edge("generate_milestones", "generate_tasks")
        graph.add_edge("generate_tasks", "generate_sprints")
        graph.add_edge("generate_sprints", END)

        return graph.compile()

    # ========================================================================
    # LangGraph Nodes
    # ========================================================================

    async def _analyze_impact_node(self, state: PlannerState) -> dict:
        """Analyze user request to determine which roadmap components need regeneration."""
        existing = state.get("existing_roadmap")
        user_request = state.get("user_request")
        all_components = ["phases", "milestones", "tasks", "sprints"]

        # No existing roadmap or no user request → full generation
        if not existing or not user_request:
            return {
                "regen_plan": PlannerRegenPlan(
                    components_to_regenerate=all_components,
                    reasoning="Full generation requested (no existing roadmap or no specific request)",
                    preserve_components=[],
                )
            }

        # Try deterministic rules first
        deterministic_plan = self._deterministic_regen_plan(user_request, existing)
        if deterministic_plan is not None:
            return {"regen_plan": deterministic_plan}

        # Fallback: no LLM available
        if self.llm_client is None:
            return {
                "regen_plan": PlannerRegenPlan(
                    components_to_regenerate=all_components,
                    reasoning="No LLM available for semantic analysis",
                    preserve_components=[],
                )
            }

        # Use LLM for semantic impact analysis
        existing_summary = {
            "phases_count": len(existing.get("phases", [])),
            "milestones_count": len(existing.get("milestones", [])),
            "tasks_count": len(existing.get("implementation_tasks", [])),
            "phases": [p.get("name") for p in existing.get("phases", [])[:5]],
        }

        prompt = f"""Analyze which roadmap components need regeneration based on the user's request.

EXISTING ROADMAP SUMMARY:
{json.dumps(existing_summary, indent=2)}

USER REQUEST: "{user_request}"

Determine which components MUST be regenerated.
Valid component names: phases, milestones, tasks, sprints

Cascade rules:
- If phases change → milestones, tasks, sprints must also change.
- If milestones change → tasks, sprints must also change.
- If tasks change → sprints must also change.
- If only sprints → only sprints need regeneration.

Examples:
- "Add more tasks to phase 2" → tasks, sprints
- "Change the project phases" → phases, milestones, tasks, sprints
- "Update milestones" → milestones, tasks, sprints
- "Reorganize sprints" → sprints

Return JSON with components_to_regenerate (list), reasoning (string), preserve_components (list).
"""

        try:
            if hasattr(self.llm_client, "with_structured_output"):
                structured_llm = self.llm_client.with_structured_output(PlannerRegenPlan)
                regen_plan = await structured_llm.ainvoke(prompt)
            else:
                response = await self._invoke_llm(prompt)
                regen_plan = self._parse_regen_plan(response)
            return {"regen_plan": regen_plan}
        except Exception:
            return {
                "regen_plan": PlannerRegenPlan(
                    components_to_regenerate=all_components,
                    reasoning="Analysis failed, defaulting to full regeneration",
                    preserve_components=[],
                )
            }

    async def _generate_phases_node(self, state: PlannerState) -> dict:
        """Generate or preserve project phases."""
        regen_plan = state.get("regen_plan")
        existing = state.get("existing_roadmap") or {}

        if regen_plan and "phases" not in regen_plan.components_to_regenerate:
            return {"phases": existing.get("phases", [])}

        architecture = state.get("architecture", {})
        requirements = state.get("requirements", {})
        user_request = state.get("user_request") or ""

        # print("  [2/4] Generating phases and milestones...", flush=True)

        arch_json = json.dumps(architecture, indent=2, ensure_ascii=False)
        req_json = json.dumps(requirements, indent=2, ensure_ascii=False)

        prompt = f"""You are an expert software delivery planner.
Generate project execution PHASES based on the architecture and requirements below.
Return ONLY a valid JSON array of phases.

ARCHITECTURE:
{arch_json}

REQUIREMENTS:
{req_json}

{("USER REQUEST: " + user_request) if user_request else ""}

Return a JSON array with 3-6 phases:
[
  {{"name": "Phase name", "description": "What this phase covers", "order": 1}},
  ...
]

Rules:
- Each phase name must be unique.
- order starts at 1 and increments.
- Phases should flow logically (e.g. Setup → Core Development → Integration → Testing → Deployment).
- Return ONLY the JSON array, no markdown fences, no commentary.
"""

        try:
            phases_raw = await self._invoke_llm(prompt)
            phases = self._parse_json_array(phases_raw)
            if phases and all(isinstance(p, dict) and "name" in p for p in phases):
                for i, phase in enumerate(phases):
                    if "order" not in phase:
                        phase["order"] = i + 1
                return {"phases": phases}
            else:
                # print(
                #     f"  [warn] Phase generation: LLM returned {len(phases) if phases else 0} phases "
                    "but validation failed. Using fallback.",
                    flush=True,
                )
        except Exception as exc:
            # print(f"  [warn] Phase generation failed ({type(exc).__name__}: {exc}). Using fallback.", flush=True)

        return {"phases": self._default_phases()}

    async def _generate_milestones_node(self, state: PlannerState) -> dict:
        """Generate or preserve project milestones."""
        regen_plan = state.get("regen_plan")
        existing = state.get("existing_roadmap") or {}

        if regen_plan and "milestones" not in regen_plan.components_to_regenerate:
            return {"milestones": existing.get("milestones", [])}

        phases = state.get("phases") or []
        requirements = state.get("requirements", {})
        user_request = state.get("user_request") or ""

        phase_names = [
            p.get("name") if isinstance(p, dict) else p.name for p in phases
        ]
        req_json = json.dumps(requirements, indent=2, ensure_ascii=False)

        prompt = f"""You are an expert software delivery planner.
Generate project MILESTONES based on the phases and requirements below.
Return ONLY a valid JSON array of milestones.

PROJECT PHASES: {json.dumps(phase_names)}

REQUIREMENTS:
{req_json[:1500]}

{("USER REQUEST: " + user_request) if user_request else ""}

Return a JSON array with 3-8 milestones:
[
  {{"name": "Milestone name", "description": "What is achieved at this milestone", "target_date": null}},
  ...
]

Rules:
- Each milestone name must be unique.
- Milestones should represent key deliverables or project checkpoints.
- target_date can be null or a "YYYY-MM-DD" string.
- Return ONLY the JSON array, no markdown fences, no commentary.
"""

        try:
            milestones_raw = await self._invoke_llm(prompt)
            milestones = self._parse_json_array(milestones_raw)
            if milestones and all(isinstance(m, dict) and "name" in m for m in milestones):
                return {"milestones": milestones}
            else:
                # print(
                #     f"  [warn] Milestone generation: LLM returned {len(milestones) if milestones else 0} milestones "
                    "but validation failed. Using fallback.",
                    flush=True,
                )
        except Exception as exc:
            # print(f"  [warn] Milestone generation failed ({type(exc).__name__}: {exc}). Using fallback.", flush=True)

        return {"milestones": self._default_milestones(phases)}

    async def _generate_tasks_node(self, state: PlannerState) -> dict:
        """Generate or preserve implementation tasks."""
        regen_plan = state.get("regen_plan")
        existing = state.get("existing_roadmap") or {}

        if regen_plan and "tasks" not in regen_plan.components_to_regenerate:
            return {"implementation_tasks": existing.get("implementation_tasks", [])}

        phases = state.get("phases") or []
        milestones = state.get("milestones") or []
        architecture = state.get("architecture", {})
        requirements = state.get("requirements", {})
        user_request = state.get("user_request") or ""

        # print("  [3/4] Generating implementation tasks...", flush=True)

        phase_names = [
            p.get("name") if isinstance(p, dict) else p.name for p in phases
        ]
        milestone_names = [
            m.get("name") if isinstance(m, dict) else m.name for m in milestones
        ]
        # Cap inputs to keep the prompt + output within 8192 output tokens
        arch_json = json.dumps(architecture, indent=2, ensure_ascii=False)[:2000]
        req_json = json.dumps(requirements, indent=2, ensure_ascii=False)[:1500]

        prompt = f"""You are an expert software delivery planner.
Generate detailed IMPLEMENTATION TASKS based on the architecture and requirements below.
Return ONLY a valid JSON array of tasks.

PROJECT PHASES: {json.dumps(phase_names)}
PROJECT MILESTONES: {json.dumps(milestone_names)}

ARCHITECTURE:
{arch_json}

REQUIREMENTS:
{req_json}

{("USER REQUEST: " + user_request) if user_request else ""}

Return a JSON array with 10-25 implementation tasks:
[
  {{
    "id": "unique-kebab-case-id",
    "title": "Short actionable title",
    "description": "Optional longer description or null",
    "phase_name": "Must match one of the phases exactly",
    "milestone_name": "Must match one of the milestones or null",
    "depends_on": ["ids of tasks that must complete first"],
    "external_resources": ["Docs, APIs, or tools relevant to this task"],
    "order": 1
  }},
  ...
]

Rules:
- Each task id must be unique, kebab-case (lowercase letters, numbers, hyphens only).
- phase_name must exactly match one of: {json.dumps(phase_names)}.
- milestone_name must match one of: {json.dumps(milestone_names)} or be null.
- depends_on lists ids of OTHER tasks (never this task's own id).
- Map tasks to architecture components and functional requirements where relevant.
- Return ONLY the JSON array, no markdown fences, no commentary.
"""

        try:
            tasks_raw = await self._invoke_llm(prompt)
            tasks = self._parse_json_array(tasks_raw)
            if tasks and all(isinstance(t, dict) and "id" in t and "title" in t for t in tasks):
                for i, task in enumerate(tasks):
                    if not task.get("order"):
                        task["order"] = i + 1
                    if task.get("depends_on") is None:
                        task["depends_on"] = []
                    if task.get("external_resources") is None:
                        task["external_resources"] = []
                return {"implementation_tasks": tasks}
            else:
                # print(
                #     f"  [warn] Task generation: LLM returned {len(tasks) if tasks else 0} tasks "
                    "but validation failed (missing 'id' or 'title'). Using fallback.",
                    flush=True,
                )
        except Exception as exc:
            # print(f"  [warn] Task generation failed ({type(exc).__name__}: {exc}). Using fallback.", flush=True)

        # During selective regeneration, prefer the existing tasks over empty stubs
        existing_tasks = existing.get("implementation_tasks")
        if existing_tasks:
            # print("  [info] Using existing tasks as fallback (LLM unavailable).", flush=True)
            return {"implementation_tasks": existing_tasks}

        return {"implementation_tasks": self._default_tasks(phases)}

    async def _generate_sprints_node(self, state: PlannerState) -> dict:
        """Group tasks into sprints and compute critical path + external resources."""
        regen_plan = state.get("regen_plan")
        existing = state.get("existing_roadmap") or {}

        if regen_plan and "sprints" not in regen_plan.components_to_regenerate:
            return {
                "sprints": existing.get("sprints", []),
                "critical_path": existing.get("critical_path"),
                "external_resources": existing.get("external_resources", []),
            }

        tasks = state.get("implementation_tasks") or []
        phases = state.get("phases") or []

        # Collect and deduplicate external resources from all tasks
        seen_resources: set = set()
        external_resources: List[str] = []
        for task in tasks:
            if isinstance(task, dict):
                for r in (task.get("external_resources") or []):
                    if r not in seen_resources:
                        seen_resources.add(r)
                        external_resources.append(r)

        critical_path = self._compute_critical_path(tasks)
        # Honour an explicit sprint count if the user mentioned one (e.g. "exactly 3 sprints")
        requested_num_sprints = self._extract_sprint_count(state.get("user_request") or "")
        sprints = self._group_tasks_into_sprints(tasks, phases, num_sprints=requested_num_sprints)

        return {
            "sprints": sprints,
            "critical_path": critical_path,
            "external_resources": external_resources,
        }

    # ========================================================================
    # LLM Invocation Helper
    # ========================================================================

    async def _invoke_llm(self, prompt: str) -> str:
        """Invoke LLM and return response text."""
        if not self.llm_client:
            raise RuntimeError(
                "LLM client is not available. Please ensure GEMINI_API_KEY is set."
            )

        messages = [
            SystemMessage(content="You are an expert software delivery planner. Return only valid JSON."),
            HumanMessage(content=prompt),
        ]

        if hasattr(self.llm_client, "ainvoke"):
            response = await self.llm_client.ainvoke(messages)
            return response.content if hasattr(response, "content") else str(response)

        if hasattr(self.llm_client, "generate"):
            response = await self.llm_client.generate(prompt)
            return response if isinstance(response, str) else str(response)

        raise RuntimeError("LLM client does not support ainvoke or generate.")

    # ========================================================================
    # Parsing Helpers
    # ========================================================================

    def _parse_json_array(self, raw: str) -> List[dict]:
        """Extract and parse a JSON array from an LLM response."""
        if not isinstance(raw, str):
            raw = str(raw)

        text = raw.strip()

        # Strip markdown fences
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()

        # Find JSON array boundaries
        if not text.startswith("["):
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end > start:
                text = text[start : end + 1]

        return json.loads(text)

    def _parse_regen_plan(self, response: str) -> PlannerRegenPlan:
        """Parse PlannerRegenPlan from raw LLM response."""
        text = response.strip()
        if "{" in text:
            start = text.find("{")
            end = text.rfind("}")
            if end > start:
                text = text[start : end + 1]
        try:
            return PlannerRegenPlan.model_validate_json(text)
        except Exception:
            return PlannerRegenPlan(
                components_to_regenerate=["phases", "milestones", "tasks", "sprints"],
                reasoning="Failed to parse LLM response",
                preserve_components=[],
            )

    # ========================================================================
    # Deterministic Regeneration Rules
    # ========================================================================

    def _deterministic_regen_plan(
        self, user_request: str, existing: dict
    ) -> Optional[PlannerRegenPlan]:
        """Return a deterministic regeneration plan for explicit user requests."""
        text = user_request.lower()
        all_components = ["phases", "milestones", "tasks", "sprints"]

        def plan(components: List[str], reason: str) -> PlannerRegenPlan:
            preserve = [c for c in all_components if c not in components]
            return PlannerRegenPlan(
                components_to_regenerate=components,
                reasoning=reason,
                preserve_components=preserve,
            )

        if any(phrase in text for phrase in ("regenerate everything", "redo everything", "rebuild everything")):
            return plan(all_components, "User explicitly requested full regeneration")

        only_requested = any(token in text for token in ("only", "just"))

        if only_requested and any(token in text for token in ("sprint", "sprints")):
            return plan(["sprints"], "User explicitly requested sprint reorganization only")
        if only_requested and any(token in text for token in ("task", "tasks")):
            return plan(["tasks", "sprints"], "User explicitly requested task regeneration only")
        if only_requested and any(token in text for token in ("milestone", "milestones")):
            return plan(
                ["milestones", "tasks", "sprints"],
                "User explicitly requested milestone regeneration (cascades to tasks and sprints)",
            )
        if only_requested and any(token in text for token in ("phase", "phases")):
            return plan(all_components, "User explicitly requested phase regeneration (cascades to all)")

        if any(token in text for token in ("add", "more", "extra", "additional")) and any(
            token in text for token in ("task", "tasks")
        ):
            return plan(["tasks", "sprints"], "User wants more tasks — regenerating tasks and sprints")

        if any(token in text for token in ("change", "update", "modify")) and any(
            token in text for token in ("phase", "phases")
        ):
            return plan(all_components, "Phase change cascades to all components")

        if any(token in text for token in ("change", "update", "modify")) and any(
            token in text for token in ("milestone", "milestones")
        ):
            return plan(
                ["milestones", "tasks", "sprints"],
                "Milestone change cascades to tasks and sprints",
            )

        return None

    # ========================================================================
    # Fallback Defaults
    # ========================================================================

    def _default_phases(self) -> List[dict]:
        return [
            {"name": "Project Setup", "description": "Initialize infrastructure and dependencies", "order": 1},
            {"name": "Core Development", "description": "Implement core features and business logic", "order": 2},
            {"name": "Integration", "description": "Integrate components and external services", "order": 3},
            {"name": "Testing & QA", "description": "Testing, bug fixing, and quality assurance", "order": 4},
            {"name": "Deployment", "description": "Production deployment and release", "order": 5},
        ]

    def _default_milestones(self, phases: List[dict]) -> List[dict]:
        milestones = []
        for i, phase in enumerate(phases):
            name = phase.get("name") if isinstance(phase, dict) else f"Phase {i + 1}"
            milestones.append(
                {"name": f"{name} Complete", "description": f"All tasks in {name} finished", "target_date": None}
            )
        return milestones

    def _default_tasks(self, phases: List[dict]) -> List[dict]:
        tasks = []
        order = 1
        for phase in phases:
            phase_name = phase.get("name") if isinstance(phase, dict) else "Phase"
            task_id = phase_name.lower().replace(" ", "-").replace("&", "and").replace("/", "-")
            tasks.append(
                {
                    "id": f"{task_id}-setup",
                    "title": f"Set up {phase_name}",
                    "description": f"Initialize and configure {phase_name} components",
                    "phase_name": phase_name,
                    "milestone_name": None,
                    "depends_on": [],
                    "external_resources": [],
                    "order": order,
                }
            )
            order += 1
        return tasks

    # ========================================================================
    # Critical Path & Sprint Grouping
    # ========================================================================

    def _compute_critical_path(self, tasks: List[dict]) -> str:
        """Compute a simple critical-path description from task dependency graph."""
        if not tasks:
            return ""

        tasks_by_id: Dict[str, dict] = {
            t.get("id"): t for t in tasks if isinstance(t, dict) and t.get("id")
        }

        # Memoized chain-length from each task forward through dependents
        memo: Dict[str, int] = {}

        def chain_length(task_id: str) -> int:
            if task_id in memo:
                return memo[task_id]
            dependents = [
                t.get("id")
                for t in tasks
                if isinstance(t, dict) and task_id in (t.get("depends_on") or [])
            ]
            length = 1 + (max(chain_length(d) for d in dependents) if dependents else 0)
            memo[task_id] = length
            return length

        # Start from tasks with no dependencies
        start_tasks = [t for t in tasks if isinstance(t, dict) and not t.get("depends_on")]
        if not start_tasks:
            start_tasks = tasks[:1]

        best_start = max(start_tasks, key=lambda t: chain_length(t.get("id", "")))

        # Walk the longest path forward
        path: List[str] = []
        current_id: Optional[str] = best_start.get("id")
        visited: set = set()
        while current_id and current_id not in visited:
            path.append(current_id)
            visited.add(current_id)
            dependents = [
                t.get("id")
                for t in tasks
                if isinstance(t, dict) and current_id in (t.get("depends_on") or [])
            ]
            current_id = dependents[0] if dependents else None

        return " → ".join(path)

    def _extract_sprint_count(self, user_request: str) -> Optional[int]:
        """Extract an explicit sprint count from the user's request (e.g. 'exactly 3 sprints')."""
        import re
        text = user_request.lower()
        if "sprint" not in text:
            return None
        # Match patterns like "3 sprints", "exactly 3 sprints", "into 3 sprints"
        match = re.search(r"\b(\d+)\s+sprint", text)
        if match:
            n = int(match.group(1))
            return n if 1 <= n <= 20 else None
        return None

    def _group_tasks_into_sprints(
        self, tasks: List[dict], phases: List[dict], num_sprints: Optional[int] = None
    ) -> List[dict]:
        """Group tasks into sprints ordered by phase.

        If num_sprints is provided the tasks are split into exactly that many sprints;
        otherwise aims for ~4 sprints (or 1 per phase chunk of 5 tasks).
        """
        if not tasks:
            return []

        phase_order: Dict[str, int] = {}
        for i, phase in enumerate(phases):
            name = phase.get("name") if isinstance(phase, dict) else f"Phase {i}"
            phase_order[name] = i

        def sort_key(t: dict):
            phase_idx = phase_order.get(t.get("phase_name"), 999)
            return (phase_idx, t.get("order", 999))

        sorted_tasks = sorted(tasks, key=sort_key)
        target = num_sprints if num_sprints else 4
        sprint_size = max(1, (len(sorted_tasks) + target - 1) // target)

        sprints: List[dict] = []
        for sprint_num, i in enumerate(range(0, len(sorted_tasks), sprint_size), start=1):
            chunk = sorted_tasks[i : i + sprint_size]
            task_ids = [t.get("id") for t in chunk if t.get("id")]
            sprint_phases = list(
                dict.fromkeys(
                    t.get("phase_name") for t in chunk if t.get("phase_name")
                )
            )
            goal = (
                f"Complete {', '.join(sprint_phases[:2])} deliverables"
                if sprint_phases
                else f"Sprint {sprint_num} deliverables"
            )
            sprints.append({"name": f"Sprint {sprint_num}", "goal": goal, "tasks": task_ids})

        return sprints

    # ========================================================================
    # Extraction Helpers
    # ========================================================================

    def _extract_architecture(self, input_data: Dict[str, Any]) -> dict:
        arch = input_data.get("architecture") or input_data.get("context", {}).get("architecture")
        if arch is None:
            return {}
        if isinstance(arch, ArchitectureDefinition):
            return arch.model_dump()
        if isinstance(arch, dict):
            return dict(arch)
        if hasattr(arch, "model_dump"):
            return arch.model_dump()
        if hasattr(arch, "dict"):
            return arch.dict()
        return {}

    def _extract_requirements(self, input_data: Dict[str, Any]) -> dict:
        req = input_data.get("requirements") or input_data.get("context", {}).get("requirements")
        if req is None:
            return {}
        if isinstance(req, dict):
            return req
        if hasattr(req, "model_dump"):
            return req.model_dump()
        if hasattr(req, "dict"):
            return req.dict()
        return {}

    # ========================================================================
    # Review Protocol
    # ========================================================================

    async def review(self, artifact: Any, context: Optional[dict] = None) -> ReviewResult:
        """Validate execution plan output."""
        base_result = await super().review(artifact, context or {})
        issues = list(base_result.feedback)

        if not isinstance(artifact, dict):
            issues.append("Execution planner output must be a dictionary")
            return ReviewResult(
                is_valid=False,
                score=0.0,
                feedback=self._dedupe(issues),
                detailed_scores=base_result.detailed_scores,
            )

        roadmap = artifact.get("roadmap") or artifact.get("execution_plan")
        if not isinstance(roadmap, dict):
            issues.append("Roadmap payload must be a dictionary")
            return ReviewResult(
                is_valid=False,
                score=0.0,
                feedback=self._dedupe(issues),
                detailed_scores=base_result.detailed_scores,
            )

        if not roadmap.get("phases"):
            issues.append("Roadmap must contain at least one phase")
        if not roadmap.get("milestones"):
            issues.append("Roadmap must contain at least one milestone")
        if not roadmap.get("implementation_tasks"):
            issues.append("Roadmap must contain at least one implementation task")

        issues = self._dedupe(issues)
        score_penalty = min(0.6, 0.1 * len(issues))
        adjusted_score = max(0.0, base_result.score - score_penalty)

        return ReviewResult(
            is_valid=(adjusted_score >= self.reviewer.min_score and not issues),
            score=adjusted_score,
            feedback=issues,
            detailed_scores=base_result.detailed_scores,
        )

    # ========================================================================
    # BaseAgent Interface
    # ========================================================================

    async def _generate(self, input: Any, context: dict, tools: list) -> Dict[str, Any]:
        """BaseAgent interface for execute() compatibility — delegates to process()."""
        payload: Dict[str, Any]
        if isinstance(input, dict):
            payload = dict(input)
        else:
            payload = {"user_request": str(input)}

        # Merge context fields into payload if not already present
        for key in ("architecture", "requirements", "existing_roadmap"):
            if context.get(key) is not None and key not in payload:
                payload[key] = context[key]

        return await self.process(payload)

    def _get_quality_criteria(self) -> dict:
        return {
            "feasibility": 0.35,
            "clarity": 0.35,
            "completeness": 0.3,
            "consistency": 0.2,
        }

    # ========================================================================
    # Utility
    # ========================================================================

    def _roadmap_summary(self, roadmap: Dict[str, Any]) -> str:
        phases = roadmap.get("phases", [])
        milestones = roadmap.get("milestones", [])
        tasks = roadmap.get("implementation_tasks", [])
        phase_names = [p.get("name") for p in phases[:3] if isinstance(p, dict)]
        suffix = "..." if len(phases) > 3 else ""
        return (
            f"Execution plan: {len(phases)} phases ({', '.join(phase_names)}{suffix}), "
            f"{len(milestones)} milestones, {len(tasks)} implementation tasks."
        )

    def _dedupe(self, items: List[str]) -> List[str]:
        seen: set = set()
        unique: List[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique
