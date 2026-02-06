"""Project architect agent for technical design and architecture outputs."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.protocols.schemas import MermaidLLMResponse
from src.protocols.review_protocol import ReviewResult
from src.state.project_state import ArchitectureDefinition, ProjectState
from src.tools.diagram_generator import DiagramGenerator
from src.utils.token_optimizer import ContextExtractor


class ProjectArchitectAgent(BaseAgent):
    """Defines technical stack and system diagrams from project requirements."""

    description = "Defines technical stack and system diagrams."

    def __init__(
        self,
        state_manager: Any,
        llm_client: Any = None,
        review_config: Optional[dict] = None,
    ) -> None:
        super().__init__(
            name="Project Architect",
            llm_client=llm_client,
            review_config=review_config or {"min_score": 0.75},
        )
        self.state_manager = state_manager
        self.diagram_gen = DiagramGenerator()
        self.context_extractor = ContextExtractor()

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build architecture outputs from requirements and return state delta payload.
        """
        requirements = self._extract_requirements(input_data)
        if not requirements:
            raise ValueError("ProjectArchitectAgent requires populated requirements input.")

        requirements_text = self._requirements_to_text(requirements)
        if len(requirements_text) > 2800:
            requirements_text = self.context_extractor.summarize_text(
                requirements_text, max_chars=2800
            )

        tech_stack = await self._draft_tech_stack(
            requirements=requirements,
            constraints=requirements.get("constraints", []),
        )

        app_type = self._infer_app_type(requirements)
        participants = ["User", "Frontend", "API", "Database"]
        # Old deterministic tool generation path (kept for reference):
        # system_diagram = await self.diagram_gen.generate_diagram(
        #     type="c4_context",
        #     context=f"{app_type}: {requirements_text}",
        #     participants=participants,
        # )
        # erd = await self.diagram_gen.generate_diagram(
        #     type="erd",
        #     context=requirements_text,
        # )

        system_diagram = await self._generate_mermaid_with_llm(
            diagram_kind="system",
            requirements_text=requirements_text,
            app_type=app_type,
            participants=participants,
        )
        erd = await self._generate_mermaid_with_llm(
            diagram_kind="erd",
            requirements_text=requirements_text,
            app_type=app_type,
            participants=participants,
        )

        architecture = ArchitectureDefinition(
            tech_stack=tech_stack,
            data_schema=erd,
            system_diagram=system_diagram,
            deployment_strategy=self._propose_deployment_strategy(tech_stack, requirements),
        )

        architecture_dict = architecture.model_dump()
        return {
            "summary": self._architecture_summary(architecture_dict),
            "architecture": architecture_dict,
            "state_delta": {"architecture": architecture_dict},
        }

    async def review(
        self, artifact: Any, context: Optional[dict] = None
    ) -> ReviewResult:
        """
        Validate shared quality dimensions plus architect-specific checks.
        """
        base_result = await super().review(artifact, context or {})
        issues = list(base_result.feedback)

        if not isinstance(artifact, dict):
            issues.append("Architect output must be a dictionary")
            return ReviewResult(
                is_valid=False,
                score=0.0,
                feedback=self._dedupe(issues),
                detailed_scores=base_result.detailed_scores,
            )

        if not artifact.get("summary"):
            issues.append("Architecture summary is missing")

        architecture = artifact.get("architecture")
        if not isinstance(architecture, dict):
            issues.append("Architecture payload must be a dictionary")
            return ReviewResult(
                is_valid=False,
                score=0.0,
                feedback=self._dedupe(issues),
                detailed_scores=base_result.detailed_scores,
            )

        required_fields = ("tech_stack", "system_diagram", "data_schema")
        for field_name in required_fields:
            if not architecture.get(field_name):
                issues.append(f"Architecture field missing: {field_name}")

        tech_stack = architecture.get("tech_stack", {})
        if not isinstance(tech_stack, dict):
            issues.append("Tech stack must be a dictionary")
        else:
            required_stack_keys = {"frontend", "backend", "database", "devops"}
            missing = sorted(required_stack_keys.difference(tech_stack.keys()))
            if missing:
                issues.append(f"Tech stack missing required components: {', '.join(missing)}")

        for diagram_field in ("system_diagram", "data_schema"):
            diagram_code = architecture.get(diagram_field)
            if not self._is_valid_mermaid(diagram_code):
                issues.append(f"Invalid Mermaid syntax in {diagram_field}")

        if not self._tech_stack_covers_requirements(
            tech_stack=tech_stack,
            requirements=(context or {}).get("requirements", {}),
        ):
            issues.append("Tech stack does not clearly cover functional requirements")

        if not self._respects_constraints(
            tech_stack=tech_stack,
            requirements=(context or {}).get("requirements", {}),
        ):
            issues.append("Tech stack conflicts with stated project constraints")

        issues = self._dedupe(issues)
        score_penalty = min(0.6, 0.1 * len(issues))
        adjusted_score = max(0.0, base_result.score - score_penalty)
        return ReviewResult(
            is_valid=(adjusted_score >= self.reviewer.min_score and not issues),
            score=adjusted_score,
            feedback=issues,
            detailed_scores=base_result.detailed_scores,
        )

    async def _generate(self, input: Any, context: dict, tools: list) -> Dict[str, Any]:
        payload: Dict[str, Any]
        if isinstance(input, dict):
            payload = dict(input)
        else:
            payload = {"prompt": str(input)}

        if "requirements" not in payload and context.get("requirements") is not None:
            payload["requirements"] = context.get("requirements")

        return await self.process(payload)

    def _get_quality_criteria(self) -> dict:
        return {
            "feasibility": 0.5,
            "clarity": 0.3,
            "completeness": 0.2,
            "consistency": 0.2,
        }

    def _extract_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        requirements = input_data.get("requirements")
        if isinstance(requirements, ProjectState):
            return requirements.requirements.model_dump()

        if isinstance(input_data.get("state"), ProjectState):
            state: ProjectState = input_data["state"]
            return state.requirements.model_dump()

        if hasattr(requirements, "model_dump"):
            return requirements.model_dump()

        if isinstance(requirements, dict):
            return requirements

        return {}

    def _requirements_to_text(self, requirements: Dict[str, Any]) -> str:
        functional = requirements.get("functional", []) or []
        non_functional = requirements.get("non_functional", []) or []
        constraints = requirements.get("constraints", []) or []
        user_stories = requirements.get("user_stories", []) or []

        lines: List[str] = []
        if functional:
            lines.append("Functional: " + "; ".join(str(item) for item in functional))
        if non_functional:
            lines.append("Non-functional: " + "; ".join(str(item) for item in non_functional))
        if constraints:
            lines.append("Constraints: " + "; ".join(str(item) for item in constraints))
        if user_stories:
            lines.append("User stories: " + "; ".join(str(item) for item in user_stories[:5]))
        return " | ".join(lines)

    async def _draft_tech_stack(
        self, requirements: Dict[str, Any], constraints: List[str]
    ) -> Dict[str, str]:
        llm_result = await self._draft_tech_stack_with_llm(requirements, constraints)
        if llm_result:
            return llm_result

        constraints_text = " ".join(str(c).lower() for c in constraints)
        backend = "FastAPI (Python)" if "python" in constraints_text else "Node.js (NestJS)"
        frontend = "React (Next.js)"
        database = "PostgreSQL"
        devops = "Docker + GitHub Actions"

        return {
            "frontend": frontend,
            "backend": backend,
            "database": database,
            "devops": devops,
        }

    async def _draft_tech_stack_with_llm(
        self, requirements: Dict[str, Any], constraints: List[str]
    ) -> Dict[str, str]:
        if self.llm_client is None:
            return {}

        prompt = (
            "You are a Senior Software Architect. Analyze the requirements and output "
            "strict JSON with keys: frontend, backend, database, devops. "
            "Constraints must be respected.\n\n"
            f"Requirements: {json.dumps(requirements, ensure_ascii=True)}\n"
            f"Constraints: {json.dumps(constraints, ensure_ascii=True)}"
        )

        raw_response: Any = None
        if hasattr(self.llm_client, "generate"):
            raw_response = await self.llm_client.generate(prompt)
        elif hasattr(self.llm_client, "ainvoke"):
            raw_response = await self.llm_client.ainvoke(prompt)
        else:
            return {}

        text = raw_response if isinstance(raw_response, str) else str(raw_response)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}

        required = {"frontend", "backend", "database", "devops"}
        if not isinstance(parsed, dict) or not required.issubset(parsed.keys()):
            return {}

        return {key: str(parsed[key]) for key in required}

    async def _generate_mermaid_with_llm(
        self,
        diagram_kind: str,
        requirements_text: str,
        app_type: str,
        participants: List[str],
    ) -> str:
        fallback_type = "erd" if diagram_kind == "erd" else "c4_context"
        
        if self.llm_client is None:
            fallback_diagram = await self.diagram_gen.generate_diagram(
            type=fallback_type,
            context=f"{app_type}: {requirements_text}" if diagram_kind != "erd" else requirements_text,
            participants=participants if diagram_kind != "erd" else None,
        )
            return fallback_diagram

        if diagram_kind == "erd":
            prompt = (
                "You are a software architect. Output strict JSON only with keys: "
                'diagram_type and mermaid_code. diagram_type must be "erd". '
                "mermaid_code must be raw Mermaid.js code that starts with erDiagram "
                "and must not include markdown fences.\n\n"
                f"Requirements: {requirements_text}"
            )
        else:
            prompt = (
                "You are a software architect. Output strict JSON only with keys: "
                'diagram_type and mermaid_code. diagram_type must be "system". '
                "mermaid_code must be raw Mermaid.js system-context code that starts with "
                "flowchart or graph and must not include markdown fences.\n\n"
                f"Application Type: {app_type}\n"
                f"Participants: {', '.join(participants)}\n"
                f"Requirements: {requirements_text}"
            )

        raw_response: Any = None
        if hasattr(self.llm_client, "generate"):
            raw_response = await self.llm_client.generate(prompt)
        elif hasattr(self.llm_client, "ainvoke"):
            raw_response = await self.llm_client.ainvoke(prompt)
        else:
            return fallback_diagram

        text = raw_response if isinstance(raw_response, str) else str(raw_response)
        mermaid = self._extract_mermaid_from_structured_response(
            raw_text=text,
            expected_diagram_kind=diagram_kind,
        )
        if self._is_valid_mermaid(mermaid):
            return mermaid
        return fallback_diagram

    def _extract_mermaid_from_structured_response(
        self, raw_text: str, expected_diagram_kind: str
    ) -> str:
        try:
            parsed = MermaidLLMResponse.model_validate_json(raw_text)
        except Exception:
            return ""

        if parsed.diagram_type != expected_diagram_kind:
            return ""
        return parsed.mermaid_code.strip()

    # Old free-text extraction heuristic (replaced by structured JSON + pydantic validation):
    # def _extract_mermaid_code(self, text: str) -> str:
    #     stripped = (text or "").strip()
    #     if not stripped:
    #         return ""
    #
    #     if "```" in stripped:
    #         blocks = stripped.split("```")
    #         for block in blocks:
    #             candidate = block.strip()
    #             if candidate.startswith("mermaid"):
    #                 candidate = candidate[len("mermaid") :].strip()
    #             if candidate.startswith(
    #                 ("flowchart", "graph", "sequenceDiagram", "erDiagram", "classDiagram")
    #             ):
    #                 return candidate
    #
    #     for token in ("flowchart", "graph", "sequenceDiagram", "erDiagram", "classDiagram"):
    #         idx = stripped.find(token)
    #         if idx != -1:
    #             return stripped[idx:].strip()
    #     return stripped

    def _infer_app_type(self, requirements: Dict[str, Any]) -> str:
        corpus = " ".join(
            str(item).lower()
            for item in (
                requirements.get("functional", [])
                + requirements.get("non_functional", [])
                + requirements.get("constraints", [])
            )
        )
        if "microservice" in corpus:
            return "Microservice application"
        if "mobile" in corpus:
            return "Mobile-first application"
        if "real-time" in corpus:
            return "Real-time web application"
        return "Web application"

    def _propose_deployment_strategy(
        self, tech_stack: Dict[str, str], requirements: Dict[str, Any]
    ) -> str:
        stack_text = " ".join(value.lower() for value in tech_stack.values())
        if "next.js" in stack_text:
            return "Vercel for frontend, managed PostgreSQL, containerized backend services."
        if "fastapi" in stack_text:
            return "Containerized deployment on cloud VM/Kubernetes with managed PostgreSQL."
        return "Containerized CI/CD deployment with managed database services."

    def _architecture_summary(self, architecture: Dict[str, Any]) -> str:
        tech = architecture.get("tech_stack", {})
        return (
            "Selected stack: "
            f"Frontend={tech.get('frontend', 'N/A')}, "
            f"Backend={tech.get('backend', 'N/A')}, "
            f"Database={tech.get('database', 'N/A')}, "
            f"DevOps={tech.get('devops', 'N/A')}."
        )

    def _is_valid_mermaid(self, diagram_code: Any) -> bool:
        if not isinstance(diagram_code, str) or not diagram_code.strip():
            return False
        starts = ("flowchart", "graph", "sequenceDiagram", "erDiagram", "classDiagram")
        return diagram_code.strip().startswith(starts)

    def _tech_stack_covers_requirements(
        self, tech_stack: Dict[str, Any], requirements: Dict[str, Any]
    ) -> bool:
        if not isinstance(tech_stack, dict) or not tech_stack:
            return False
        required_keys = {"frontend", "backend", "database", "devops"}
        if not required_keys.issubset(set(tech_stack.keys())):
            return False
        functional = requirements.get("functional", []) if isinstance(requirements, dict) else []
        return isinstance(functional, list)

    def _respects_constraints(
        self, tech_stack: Dict[str, Any], requirements: Dict[str, Any]
    ) -> bool:
        if not isinstance(requirements, dict):
            return True

        constraints = requirements.get("constraints", [])
        if not isinstance(constraints, list):
            return True

        normalized_constraints = " ".join(str(item).lower() for item in constraints)
        if "python" in normalized_constraints:
            backend = str(tech_stack.get("backend", "")).lower()
            return "python" in backend or "fastapi" in backend
        return True

    def _dedupe(self, items: List[str]) -> List[str]:
        seen = set()
        unique: List[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique


# Backward-compatible alias for existing imports.
class ProjectArchitect(ProjectArchitectAgent):
    """Compatibility alias."""
