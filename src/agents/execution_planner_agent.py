"""Creates an organized, detailed project execution plan (phases, milestones, tasks, dependencies)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.state.project_state import (
    ArchitectureDefinition,
    ImplementationTask,
    Milestone,
    Phase,
    Roadmap,
)


class ExecutionPlannerAgent(BaseAgent):
    """
    Creates a structured execution plan for the project.

    - Input: Architect agent output (architecture); uses requirements for context.
    - Output: Phases, milestones, ordered implementation tasks with dependencies
      and relevant external resources. Consumed by Reviewer and Exporter agents.
    """

    description = (
        "Creates an organized and detailed checklist of steps, phases, and milestones "
        "for the project, including dependencies and external resources."
    )

    def __init__(
        self,
        llm_client: Any = None,
        review_config: Optional[dict] = None,
    ) -> None:
        super().__init__(
            name="Execution Planner",
            llm_client=llm_client,
            review_config=review_config or {"min_score": 0.7},
        )

    async def _generate(self, input: Any, context: dict, tools: list) -> Dict[str, Any]:
        """
        Produce a project execution plan from architecture (and requirements).

        Dependencies: requires Architect agent output in context.
        Deliverable: phases, milestones, ordered implementation tasks,
        dependencies, and external resources.
        """
        architecture = self._get_architecture(context)
        requirements = context.get("requirements") or {}
        if isinstance(requirements, dict):
            req_dict = requirements
        elif requirements is None:
            req_dict = {}
        else:
            dump = getattr(requirements, "model_dump", None) or getattr(requirements, "dict", None)
            req_dict = dump() if callable(dump) else {}

        if self.llm_client:
            roadmap = await self._generate_with_llm(architecture, req_dict, context, input)
        else:
            roadmap = self._build_plan_fallback(architecture, req_dict, context)

        # Serialize for content and state_delta (Reviewer and Exporter consume content)
        plan_payload = roadmap.model_dump() if hasattr(roadmap, "model_dump") else roadmap

        return {
            "execution_plan": plan_payload,
            "state_delta": {"roadmap": plan_payload},
            "metadata": {"deliverable": "execution_plan", "consumers": ["reviewer", "exporter"]},
        }

    def _get_architecture(self, context: dict) -> Dict[str, Any]:
        arch = context.get("architecture")
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

    def _build_plan_fallback(
        self,
        architecture: Dict[str, Any],
        requirements: Dict[str, Any],
        context: dict,
    ) -> Roadmap:
        """Build a structured execution plan from architecture and requirements without LLM."""
        tech_stack = architecture.get("tech_stack") or {}
        frontend = tech_stack.get("frontend", "Frontend")
        backend = tech_stack.get("backend", "Backend")
        database = tech_stack.get("database", "Database")
        api_design = architecture.get("api_design") or []
        has_api = len(api_design) > 0

        phases = [
            Phase(name="Environment & Setup", description="Tooling, repo, and environment", order=1),
            Phase(name="Core Implementation", description="Backend, data, and API", order=2),
            Phase(name="Frontend & Integration", description="UI and integration", order=3),
            Phase(name="Quality & Deploy", description="Testing and deployment", order=4),
        ]

        milestones = [
            Milestone(name="Setup complete", description="Environment and repo ready", target_date=None),
            Milestone(name="Backend ready", description="API and data layer working", target_date=None),
            Milestone(name="Feature complete", description="Core flows implemented", target_date=None),
            Milestone(name="Shipped", description="Deployed and documented", target_date=None),
        ]

        tasks: List[ImplementationTask] = []
        order = 0

        # Phase 1
        order += 1
        tasks.append(
            ImplementationTask(
                id="setup-repo",
                title="Initialize repository and tooling",
                phase_name="Environment & Setup",
                milestone_name="Setup complete",
                depends_on=[],
                external_resources=["Git", "Package manager docs"],
                order=order,
            )
        )
        order += 1
        tasks.append(
            ImplementationTask(
                id="setup-env",
                title="Configure dev environment and dependencies",
                phase_name="Environment & Setup",
                milestone_name="Setup complete",
                depends_on=["setup-repo"],
                external_resources=[f"{frontend} setup", f"{backend} setup"],
                order=order,
            )
        )

        # Phase 2
        order += 1
        tasks.append(
            ImplementationTask(
                id="data-layer",
                title="Implement data layer and schema",
                phase_name="Core Implementation",
                milestone_name="Backend ready",
                depends_on=["setup-env"],
                external_resources=[f"{database} documentation"],
                order=order,
            )
        )
        if has_api:
            order += 1
            tasks.append(
                ImplementationTask(
                    id="api-layer",
                    title="Implement API endpoints",
                    phase_name="Core Implementation",
                    milestone_name="Backend ready",
                    depends_on=["data-layer"],
                    external_resources=[f"{backend} API docs"],
                    order=order,
                )
            )
        order += 1
        tasks.append(
            ImplementationTask(
                id="core-logic",
                title="Implement core business logic",
                phase_name="Core Implementation",
                milestone_name="Backend ready",
                depends_on=["data-layer"],
                external_resources=[],
                order=order,
            )
        )

        # Phase 3
        order += 1
        deps = ["data-layer", "core-logic"]
        if has_api:
            deps.append("api-layer")
        tasks.append(
            ImplementationTask(
                id="frontend-shell",
                title="Build frontend shell and routing",
                phase_name="Frontend & Integration",
                milestone_name="Feature complete",
                depends_on=deps,
                external_resources=[f"{frontend} docs"],
                order=order,
            )
        )
        order += 1
        tasks.append(
            ImplementationTask(
                id="integration",
                title="Integrate frontend with backend/API",
                phase_name="Frontend & Integration",
                milestone_name="Feature complete",
                depends_on=["frontend-shell"],
                external_resources=[],
                order=order,
            )
        )

        # Phase 4
        order += 1
        tasks.append(
            ImplementationTask(
                id="quality-deploy",
                title="Testing and deployment",
                phase_name="Quality & Deploy",
                milestone_name="Shipped",
                depends_on=["integration"],
                external_resources=["CI/CD docs", architecture.get("deployment_strategy") or "Deployment guide"],
                order=order,
            )
        )

        external_resources: List[str] = []
        if tech_stack:
            external_resources.extend([f"{k}: {v}" for k, v in tech_stack.items()])
        if architecture.get("deployment_strategy"):
            external_resources.append("Deployment: " + (architecture["deployment_strategy"] or ""))

        return Roadmap(
            phases=phases,
            milestones=milestones,
            implementation_tasks=tasks,
            sprints=[],
            critical_path="setup-repo → setup-env → data-layer → core-logic → frontend-shell → integration → quality-deploy",
            external_resources=list(dict.fromkeys(external_resources)),
        )

    async def _generate_with_llm(
        self,
        architecture: Dict[str, Any],
        requirements: Dict[str, Any],
        context: dict,
        input: Any,
    ) -> Roadmap:
        """Use LLM to generate or refine the execution plan; fallback to rule-based if unavailable."""
        # TODO: Call LLM with architecture + requirements to produce phases, milestones,
        # implementation_tasks with dependencies, and external_resources; parse into Roadmap.
        return self._build_plan_fallback(architecture, requirements, context)

    def _get_quality_criteria(self) -> dict:
        return {
            "feasibility": 0.35,
            "clarity": 0.35,
            "completeness": 0.3,
            "consistency": 0.2,
        }
