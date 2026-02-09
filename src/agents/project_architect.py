"""Project architect agent for technical design and architecture outputs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent
from src.protocols.schemas import MermaidLLMResponse
from src.protocols.review_protocol import ReviewResult
from src.state.project_state import ArchitectureDefinition, ProjectState
from src.tools.diagram_generator import DiagramGenerator
from src.utils.mermaid_validator import validate_mermaid
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
        self._mermaid_store: Any = None  # lazy-loaded for RAG snippets

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

        print("  [1/4] Drafting tech stack (LLM)...", flush=True)
        tech_stack, tech_stack_rationale = await self._draft_tech_stack(
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

        print("  [2/4] Generating system diagram (LLM)...", flush=True)
        system_diagram = await self._generate_mermaid_with_llm(
            diagram_kind="system",
            requirements_text=requirements_text,
            app_type=app_type,
            participants=participants,
        )
        print("  [3/4] Generating ERD diagram (LLM)...", flush=True)
        erd = await self._generate_mermaid_with_llm(
            diagram_kind="erd",
            requirements_text=requirements_text,
            app_type=app_type,
            participants=participants,
        )

        architecture = ArchitectureDefinition(
            tech_stack=tech_stack,
            tech_stack_rationale=tech_stack_rationale,
            data_schema=erd,
            system_diagram=system_diagram,
            deployment_strategy=self._propose_deployment_strategy(tech_stack, requirements),
        )

        print("  [4/4] Building architecture output...", flush=True)
        architecture_dict = architecture.model_dump()
        return {
            "summary": self._architecture_summary(architecture_dict),
            "architecture": architecture_dict,
            "state_delta": {
                "architecture": architecture_dict,
                "requirements": requirements,
            },
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
    ) -> tuple[Dict[str, str], Optional[str]]:
        tech_stack, rationale = await self._draft_tech_stack_with_llm(requirements, constraints)
        if tech_stack:
            return tech_stack, rationale

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
        }, None

    async def _draft_tech_stack_with_llm(
        self, requirements: Dict[str, Any], constraints: List[str]
    ) -> tuple[Dict[str, str], Optional[str]]:
        if self.llm_client is None:
            return {}, None

        prompt = (
            "You are a Senior Software Architect. Analyze the requirements and choose a concrete tech stack. "
            "Output strict JSON with these keys: frontend, backend, database, devops, explanation. "
            "frontend, backend, database, devops: each must be a single string (e.g. 'React 18 + TypeScript', 'FastAPI (Python 3.11)', 'PostgreSQL 15', 'Docker + GitHub Actions'). "
            "explanation: a short paragraph (2-4 sentences) explaining why you chose this stack and how it fits the requirements and constraints. "
            "Respect all constraints. Consider non-functional requirements (scale, latency, mobile vs web) when choosing. "
            "Prefer specific, production-ready choices over vague ones like 'Python' or 'React'.\n\n"
            f"Requirements: {json.dumps(requirements, ensure_ascii=True)}\n"
            f"Constraints: {json.dumps(constraints, ensure_ascii=True)}"
        )

        raw_response: Any = None
        if hasattr(self.llm_client, "generate"):
            raw_response = await self.llm_client.generate(prompt)
        elif hasattr(self.llm_client, "ainvoke"):
            raw_response = await self.llm_client.ainvoke(prompt)
        else:
            return {}, None

        text = raw_response if isinstance(raw_response, str) else str(raw_response)
        
        # Try to extract JSON from markdown code blocks if present
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
        
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}, None

        required = {"frontend", "backend", "database", "devops"}
        if not isinstance(parsed, dict) or not required.issubset(parsed.keys()):
            return {}, None

        # Handle nested structures: extract string from nested dicts/lists
        result = {}
        for key in required:
            value = parsed[key]
            if isinstance(value, str):
                result[key] = value
            elif isinstance(value, dict):
                if "technologies" in value and isinstance(value["technologies"], list) and value["technologies"]:
                    result[key] = str(value["technologies"][0])
                elif "name" in value:
                    result[key] = str(value["name"])
                else:
                    result[key] = str(list(value.values())[0]) if value else "Unknown"
            elif isinstance(value, list) and value:
                result[key] = str(value[0])
            else:
                result[key] = str(value)

        # Optional explanation: expand on choices (does not affect strict parsing)
        explanation = None
        for key in ("explanation", "rationale", "reasoning"):
            if key in parsed and isinstance(parsed[key], str) and parsed[key].strip():
                explanation = parsed[key].strip()
                break
        return result, explanation

    def _get_mermaid_store(self) -> Any:
        """Lazy-load mermaid vector store (same embedder as ingest). Returns None if unavailable."""
        if self._mermaid_store is not None:
            return self._mermaid_store
        try:
            from sentence_transformers import SentenceTransformer
            from src.tools.vector_store import VectorStore
            project_root = Path(__file__).resolve().parents[2]
            persist_dir = project_root / "data" / "vector_stores"
            if not (persist_dir / "mermaid.index").is_file():
                return None
            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            self._mermaid_store = VectorStore(
                store_name="mermaid",
                persist_dir=persist_dir,
                embedder=embedder,
            )
            if len(self._mermaid_store) == 0:
                self._mermaid_store = None
            return self._mermaid_store
        except Exception:
            return None

    def _get_mermaid_rag_snippets(
        self,
        diagram_kind: str,
        max_chars: int = 1500,
        query_override: str | None = None,
    ) -> str:
        """Return concatenated RAG snippets for the diagram type, or empty string if unavailable.
        When query_override is set (e.g. validator error message), use it to retrieve error-relevant chunks."""
        store = self._get_mermaid_store()
        if store is None:
            return ""
        try:
            if query_override and query_override.strip():
                query = query_override.strip()[:300]  # cap so query is not huge
            elif diagram_kind == "erd":
                query = "erDiagram entities relationships attributes"
            else:
                query = "flowchart TD graph nodes edges labels"
            if diagram_kind == "erd":
                pairs = store.query_text_with_metadata(
                    query,
                    k=3,
                    meta_filter={"diagram_type": "erd"},
                )
            else:
                pairs = store.query_text_with_metadata(
                    query,
                    k=3,
                    meta_filter={"diagram_type": "flowchart"},
                )
            if not pairs:
                return ""
            out: List[str] = []
            total = 0
            for text, _ in pairs:
                if total + len(text) > max_chars:
                    out.append(text[: max_chars - total].strip())
                    break
                out.append(text.strip())
                total += len(text)
            return "\n\n---\n\n".join(out) if out else ""
        except Exception:
            return ""

    async def _generate_mermaid_with_llm(
        self,
        diagram_kind: str,
        requirements_text: str,
        app_type: str,
        participants: List[str],
    ) -> str:
        fallback_type = "erd" if diagram_kind == "erd" else "c4_context"
        fallback_diagram = await self.diagram_gen.generate_diagram(
            type=fallback_type,
            context=f"{app_type}: {requirements_text}" if diagram_kind != "erd" else requirements_text,
            participants=participants if diagram_kind != "erd" else None,
        )
        if self.llm_client is None:
            
            return fallback_diagram

        rag_snippets = self._get_mermaid_rag_snippets(diagram_kind)
        if rag_snippets:
            print(f"  [diagram] Using mermaid RAG snippets for {diagram_kind} ({len(rag_snippets)} chars)", flush=True)
        rag_block = (
            f"Relevant Mermaid syntax (from docs):\n{rag_snippets}\n\n"
            if rag_snippets else ""
        )

        if diagram_kind == "erd":
            prompt = (
                "You are a software architect. Output strict JSON only with keys: "
                'diagram_type and mermaid_code. diagram_type must be "erd". '
                "mermaid_code must be raw Mermaid.js code that starts with erDiagram "
                "and must not include markdown fences. "
                "Include every entity and relationship implied by the requirements (e.g. users, sessions, core domain entities, audit/log tables). "
                "Use proper Mermaid erDiagram syntax: entity blocks with attributes and relationship lines (||--o{, }o--||, etc.).\n\n"
                f"{rag_block}"
                f"Requirements: {requirements_text}"
            )
        else:
            prompt = (
                "You are a software architect. Output strict JSON only with keys: "
                'diagram_type and mermaid_code. diagram_type must be "system". '
                "mermaid_code must be raw Mermaid.js flowchart code that starts with "
                "'graph TD' or 'flowchart TD' and must not include markdown fences. "
                "CRITICAL Mermaid syntax rules:\n"
                "1. Edge labels: use pipe syntax only, e.g. A -->|label text| B. Do NOT put parentheses inside edge labels (e.g. use 'email and password' not '(email/password)'); parentheses in edge labels cause parse errors.\n"
                "2. Node labels that contain parentheses or commas MUST be in double quotes inside brackets, e.g. N[\"Frontend (Web UI)\"] or N[\"Cache (e.g. Redis)\"]. Unquoted [Frontend (Web UI)] causes parse errors.\n"
                "3. Use simple node IDs (letters, no spaces) then the label: ID[Label] or ID[\"Label with (parens)\"].\n"
                "Show the main components and label edges with the main flows. Reflect the actual requirements.\n\n"
                f"{rag_block}"
                f"Application Type: {app_type}\n"
                f"Participants: {', '.join(participants)}\n"
                f"Requirements: {requirements_text}"
            )

        max_diagram_attempts = 2  # initial + one retry with real error message
        last_parse_error = ""
        for attempt in range(max_diagram_attempts):
            if attempt > 0:
                print(f"  [diagram] Retry {attempt + 1}/{max_diagram_attempts} for {diagram_kind} (validation failed)...", flush=True)
                # Query RAG with the error message to get error-relevant syntax chunks
                retry_rag = ""
                if last_parse_error:
                    retry_rag = self._get_mermaid_rag_snippets(
                        diagram_kind, max_chars=1000, query_override=last_parse_error
                    )
                    if retry_rag:
                        print(f"  [diagram] Using error-based RAG for retry ({len(retry_rag)} chars)", flush=True)
                retry_rag_block = (
                    f"Relevant Mermaid syntax (for this error):\n{retry_rag}\n\n"
                    if retry_rag else ""
                )
                correction = (
                    "Your previous Mermaid code had syntax errors. "
                    "Fix the diagram and output valid Mermaid only (JSON with diagram_type and mermaid_code). "
                )
                if last_parse_error:
                    correction += f"Parse error from validator:\n{last_parse_error}\n\n"
                correction = retry_rag_block + correction
                correction += (
                    "Rules: (1) edge labels use -->|label| only; no parentheses in edge labels. "
                    "(2) node labels with parentheses must be quoted: N[\"Label (detail)\"].\n\n"
                    f"Requirements: {requirements_text[:1500]}"
                )
                if diagram_kind == "erd":
                    prompt = (
                        "Output strict JSON with keys diagram_type and mermaid_code. diagram_type must be \"erd\". "
                        "mermaid_code must be valid erDiagram code.\n\n" + correction
                    )
                else:
                    prompt = (
                        "Output strict JSON with keys diagram_type and mermaid_code. diagram_type must be \"system\". "
                        "mermaid_code must be valid graph TD or flowchart TD. " + correction
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
            if diagram_kind == "system" and mermaid:
                mermaid = self._sanitize_mermaid_flowchart(mermaid)
            if not self._is_valid_mermaid(mermaid):
                last_parse_error = "Diagram did not start with valid keyword (flowchart/graph/erDiagram/...)."
                continue
            # Optional: compile with mmdc and get real parse errors for retry
            if attempt == 0:
                print(f"  [diagram] Validating {diagram_kind} (mmdc)...", flush=True)
            valid, parse_error = validate_mermaid(mermaid)
            if valid:
                return mermaid
            last_parse_error = parse_error or "Mermaid syntax error."
            continue

        return fallback_diagram

    def _sanitize_mermaid_flowchart(self, code: str) -> str:
        """Fix common Mermaid flowchart parse errors: unquoted node labels with ( ), and parentheses in edge labels."""
        if not code or "graph" not in code.lower():
            return code

        # 1. Node labels: [Text (with) parens] -> ["Text (with) parens"] so ( ) are not parsed as shape syntax
        def _quote_node_label(m: re.Match) -> str:
            content = m.group(1)
            if "(" in content and not content.strip().startswith('"'):
                # Escape any double quotes in content
                escaped = content.replace("\\", "\\\\").replace('"', '\\"')
                return f'["{escaped}"]'
            return m.group(0)

        code = re.sub(r"\[(?!\")([^\[\]]+)\]", _quote_node_label, code)

        # 2. Edge labels: -->|label (with) parens| -> -->|label with parens| (remove parentheses; they break parsing)
        def _strip_edge_parens(m: re.Match) -> str:
            prefix, label = m.group(1), m.group(2)
            label = re.sub(r"\(([^)]*)\)", r"\1", label)  # (x) -> x
            label = re.sub(r"\s+", " ", label).strip()  # collapse spaces
            return f"{prefix}|{label}|"
        code = re.sub(r"(-->|---)\|(.*?)\|", _strip_edge_parens, code)

        return code

    def _extract_mermaid_from_structured_response(
        self, raw_text: str, expected_diagram_kind: str
    ) -> str:
        text = raw_text.strip()
        
        # Extract JSON from markdown code blocks if present
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
        
        try:
            parsed = MermaidLLMResponse.model_validate_json(text)
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
        summary = (
            "Selected stack: "
            f"Frontend={tech.get('frontend', 'N/A')}, "
            f"Backend={tech.get('backend', 'N/A')}, "
            f"Database={tech.get('database', 'N/A')}, "
            f"DevOps={tech.get('devops', 'N/A')}."
        )
        rationale = architecture.get("tech_stack_rationale")
        if rationale and isinstance(rationale, str) and rationale.strip():
            summary += "\n\nRationale: " + rationale.strip()
        return summary

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
