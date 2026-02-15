"""Project architect agent using LangGraph for selective regeneration."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict, Annotated
from operator import add

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END

from src.agents.base_agent import BaseAgent
from src.protocols.review_protocol import ReviewResult
from src.protocols.schemas import MermaidLLMResponse
from src.state.project_state import ArchitectureDefinition, ProjectState
from src.tools.diagram_generator import DiagramGenerator
from src.utils.mermaid_validator import validate_mermaid
from src.utils.token_optimizer import ContextExtractor


# ============================================================================
# Pydantic Schemas for LLM Structured Output
# ============================================================================

class RegenPlan(BaseModel):
    """LLM-generated regeneration plan with reasoning."""
    
    artifacts_to_regenerate: List[str] = Field(
        description="List of artifacts to regenerate: tech_stack, system_diagram, data_schema, api_design, deployment_strategy"
    )
    reasoning: str = Field(
        description="Brief explanation of why these artifacts need regeneration"
    )
    preserve_artifacts: List[str] = Field(
        default_factory=list,
        description="Artifacts to keep unchanged from existing state"
    )


class TechStackOutput(BaseModel):
    """Structured tech stack output from LLM."""
    
    frontend: str = Field(description="Frontend framework/library")
    backend: str = Field(description="Backend framework/language")
    database: str = Field(description="Database system")
    devops: str = Field(description="DevOps/CI-CD tooling")


class MermaidDiagramOutput(BaseModel):
    """Structured Mermaid diagram output from LLM."""
    
    mermaid_code: str = Field(description="Raw Mermaid.js code without markdown fences")


# ============================================================================
# LangGraph State Definition
# ============================================================================

class ArchitectState(TypedDict, total=False):
    """State passed through the LangGraph workflow."""
    
    # Inputs
    requirements: dict
    existing_architecture: Optional[dict]
    user_request: Optional[str]
    
    # LLM-determined regeneration plan
    regen_plan: Optional[RegenPlan]
    
    # Generated/preserved outputs
    tech_stack: Optional[dict]
    tech_stack_rationale: Optional[str]
    system_diagram: Optional[str]
    data_schema: Optional[str]
    api_design: Optional[list]
    deployment_strategy: Optional[str]
    
    # Metadata
    app_type: Optional[str]
    requirements_text: Optional[str]


# ============================================================================
# ProjectArchitectAgent with LangGraph
# ============================================================================

class ProjectArchitectAgent(BaseAgent):
    """Defines technical stack and system diagrams with selective regeneration support."""

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
        self._graph = self._build_graph()
        self._mermaid_store: Any = None  # lazy-loaded for RAG snippets

    # ========================================================================
    # Main Entry Point
    # ========================================================================

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build architecture outputs from requirements.
        
        Supports two modes:
        1. Full generation: No existing_architecture provided
        2. Selective regeneration: existing_architecture + user_request provided
        """
        requirements = self._extract_requirements(input_data)
        if not requirements:
            raise ValueError("ProjectArchitectAgent requires populated requirements input.")

        # Prepare initial state for LangGraph
        initial_state: ArchitectState = {
            "requirements": requirements,
            "existing_architecture": input_data.get("existing_architecture") or input_data.get("existing_state"),
            "user_request": input_data.get("user_request"),
            "requirements_text": self._requirements_to_text(requirements),
            "app_type": self._infer_app_type(requirements),
        }

        # Token optimization for large requirements
        if len(initial_state["requirements_text"]) > 2800:
            initial_state["requirements_text"] = self.context_extractor.summarize_text(
                initial_state["requirements_text"], max_chars=2800
            )

        # Run the LangGraph workflow
        print("  [1/4] Analyzing impact and generating tech stack...", flush=True)
        final_state = await self._graph.ainvoke(initial_state)
        print("  [4/4] Building architecture output...", flush=True)

        # Build ArchitectureDefinition from final state
        architecture = ArchitectureDefinition(
            tech_stack=final_state.get("tech_stack") or {},
            tech_stack_rationale=final_state.get("tech_stack_rationale"),
            data_schema=final_state.get("data_schema"),
            system_diagram=final_state.get("system_diagram"),
            api_design=final_state.get("api_design") or [],
            deployment_strategy=final_state.get("deployment_strategy"),
        )

        architecture_dict = architecture.model_dump()
        return {
            "summary": self._architecture_summary(architecture_dict),
            "architecture": architecture_dict,
            "state_delta": {
                "architecture": architecture_dict,
            },
        }

    # ========================================================================
    # LangGraph Construction
    # ========================================================================

    def _build_graph(self) -> StateGraph:
        """Construct the LangGraph StateGraph for architecture generation."""
        
        graph = StateGraph(ArchitectState)

        # Add nodes
        graph.add_node("analyze_impact", self._analyze_impact_node)
        graph.add_node("generate_tech_stack", self._tech_stack_node)
        graph.add_node("generate_system_diagram", self._system_diagram_node)
        graph.add_node("generate_data_schema", self._data_schema_node)
        graph.add_node("generate_deployment", self._deployment_node)

        # Define flow
        graph.set_entry_point("analyze_impact")
        graph.add_edge("analyze_impact", "generate_tech_stack")
        graph.add_edge("generate_tech_stack", "generate_system_diagram")
        graph.add_edge("generate_system_diagram", "generate_data_schema")
        graph.add_edge("generate_data_schema", "generate_deployment")
        graph.add_edge("generate_deployment", END)

        return graph.compile()

    # ========================================================================
    # LangGraph Nodes
    # ========================================================================

    async def _analyze_impact_node(self, state: ArchitectState) -> dict:
        """Analyze user request to determine what needs regeneration."""
        
        existing = state.get("existing_architecture")
        user_request = state.get("user_request")

        # If no existing architecture or no user request, regenerate everything
        if not existing or not user_request:
            return {
                "regen_plan": RegenPlan(
                    artifacts_to_regenerate=["tech_stack", "system_diagram", "data_schema", "deployment_strategy"],
                    reasoning="Full generation requested (no existing state or no specific request)",
                    preserve_artifacts=[]
                )
            }

        # Deterministic rules for explicit user requests (avoids LLM misclassification)
        deterministic_plan = self._deterministic_regen_plan(user_request)
        if deterministic_plan is not None:
            return {"regen_plan": deterministic_plan}

        # Use LLM to analyze semantic impact
        if self.llm_client is None:
            # No LLM, regenerate everything
            return {
                "regen_plan": RegenPlan(
                    artifacts_to_regenerate=["tech_stack", "system_diagram", "data_schema", "deployment_strategy"],
                    reasoning="No LLM available for analysis",
                    preserve_artifacts=[]
                )
            }

        prompt = f"""Analyze what architecture artifacts need regeneration based on the user's request.

EXISTING ARCHITECTURE:
- Tech Stack: {json.dumps(existing.get('tech_stack', {}), indent=2)}
- System Diagram: {'exists' if existing.get('system_diagram') else 'none'}
- Data Schema (ERD): {'exists' if existing.get('data_schema') else 'none'}
- Deployment Strategy: {existing.get('deployment_strategy', 'none')}

USER REQUEST: "{user_request}"

Determine which artifacts MUST be regenerated based on semantic impact.
Valid artifact names: tech_stack, system_diagram, data_schema, deployment_strategy

Examples of reasoning:
- "Change database to MongoDB" → only data_schema needs regeneration
- "Redo ERD only" → only data_schema needs regeneration
- "Switch from React to Vue" → only tech_stack needs regeneration (diagrams reference concepts, not specific frameworks)
- "Switch to microservices architecture" → tech_stack, system_diagram, deployment_strategy all need regeneration
- "Regenerate everything" → all artifacts

Return artifacts_to_regenerate (list), reasoning (string), and preserve_artifacts (list).
"""

        try:
            if hasattr(self.llm_client, "with_structured_output"):
                structured_llm = self.llm_client.with_structured_output(RegenPlan)
                regen_plan = await structured_llm.ainvoke(prompt)
            else:
                # Fallback: parse JSON response manually
                response = await self._invoke_llm(prompt)
                regen_plan = self._parse_regen_plan(response)
            
            return {"regen_plan": regen_plan}

        except Exception:
            # On error, regenerate everything
            return {
                "regen_plan": RegenPlan(
                    artifacts_to_regenerate=["tech_stack", "system_diagram", "data_schema", "deployment_strategy"],
                    reasoning="Analysis failed, defaulting to full regeneration",
                    preserve_artifacts=[]
                )
            }

    async def _tech_stack_node(self, state: ArchitectState) -> dict:
        """Generate or preserve tech stack."""
        
        regen_plan = state.get("regen_plan")
        existing = state.get("existing_architecture") or {}

        # Check if we should preserve
        if regen_plan and "tech_stack" not in regen_plan.artifacts_to_regenerate:
            return {
                "tech_stack": existing.get("tech_stack", {}),
                "tech_stack_rationale": existing.get("tech_stack_rationale"),
            }

        # Generate new tech stack
        requirements = dict(state.get("requirements", {}))
        constraints = requirements.get("constraints", [])
        user_request = state.get("user_request")
        effective_constraints = self._reconcile_constraints_with_user_request(
            constraints, user_request
        )
        requirements["constraints"] = effective_constraints
        
        tech_stack, rationale = await self._generate_tech_stack(
            requirements, effective_constraints, user_request=user_request
        )
        return {
            "tech_stack": tech_stack,
            "tech_stack_rationale": rationale,
        }

    async def _system_diagram_node(self, state: ArchitectState) -> dict:
        """Generate or preserve system diagram."""
        
        regen_plan = state.get("regen_plan")
        existing = state.get("existing_architecture") or {}

        # Check if we should preserve
        if regen_plan and "system_diagram" not in regen_plan.artifacts_to_regenerate:
            return {"system_diagram": existing.get("system_diagram")}

        # Generate new system diagram
        print("  [2/4] Generating system diagram (LLM)...", flush=True)
        diagram = await self._generate_mermaid_diagram(
            diagram_kind="system",
            requirements_text=state.get("requirements_text", ""),
            app_type=state.get("app_type", "Web application"),
            existing_diagram=existing.get("system_diagram") if existing else None,
        )
        return {"system_diagram": diagram}

    async def _data_schema_node(self, state: ArchitectState) -> dict:
        """Generate or preserve data schema (ERD)."""
        
        regen_plan = state.get("regen_plan")
        existing = state.get("existing_architecture") or {}

        # Check if we should preserve
        if regen_plan and "data_schema" not in regen_plan.artifacts_to_regenerate:
            return {"data_schema": existing.get("data_schema")}

        # Generate new ERD
        print("  [3/4] Generating ERD diagram (LLM)...", flush=True)
        diagram = await self._generate_mermaid_diagram(
            diagram_kind="erd",
            requirements_text=state.get("requirements_text", ""),
            app_type=state.get("app_type", "Web application"),
            existing_diagram=existing.get("data_schema") if existing else None,
        )
        return {"data_schema": diagram}

    async def _deployment_node(self, state: ArchitectState) -> dict:
        """Generate or preserve deployment strategy."""
        
        regen_plan = state.get("regen_plan")
        existing = state.get("existing_architecture") or {}

        # Check if we should preserve
        if regen_plan and "deployment_strategy" not in regen_plan.artifacts_to_regenerate:
            return {"deployment_strategy": existing.get("deployment_strategy")}

        # Generate new deployment strategy
        tech_stack = state.get("tech_stack", {})
        requirements = state.get("requirements", {})
        
        strategy = self._propose_deployment_strategy(tech_stack, requirements)
        return {"deployment_strategy": strategy}

    # ========================================================================
    # Generation Helpers
    # ========================================================================

    async def _generate_tech_stack(
        self,
        requirements: Dict[str, Any],
        constraints: List[str],
        user_request: Optional[str] = None,
    ) -> tuple[Dict[str, str], Optional[str]]:
        """Generate tech stack via LLM with fallback. Returns (stack_dict, rationale)."""
        
        if self.llm_client is None:
            return self._default_tech_stack(constraints), None

        prompt = (
    "You are a Senior Software Architect with expertise across multiple technology ecosystems. "
    "Your task is to analyze the specific requirements and constraints below, then select the MOST APPROPRIATE tech stack for THIS PARTICULAR project.\n\n"
    
    "CRITICAL INSTRUCTIONS:\n"
    "- Base your choices ENTIRELY on the requirements and constraints provided\n"
    "- Do NOT default to common examples unless they genuinely fit best\n"
    "- Consider the project's unique characteristics: scale, domain, team context, and constraints\n"
    "- Justify each choice based on specific requirement alignment, not general popularity\n\n"
    
    "DECISION FRAMEWORK:\n"
    "1. Analyze functional requirements to determine application type and complexity\n"
    "2. Review non-functional requirements (scale, performance, latency, reliability)\n"
    "3. Evaluate constraints (budget, team skills, timeline, existing infrastructure)\n"
    "4. Select technologies that maximize requirement satisfaction while respecting all constraints\n"
    "5. Prioritize the latest user request if it conflicts with earlier constraints\n\n"
    
    "OUTPUT FORMAT (strict JSON):\n"
    "{\n"
    '  "frontend": "specific technology + version (e.g., \'Next.js 14 + TypeScript\', \'Flutter 3.16\', \'Vue 3 + Vite\')",\n'
    '  "backend": "specific technology + version (e.g., \'Node.js 20 + Express\', \'Django 5.0\', \'Go 1.21 + Gin\')",\n'
    '  "database": "specific technology + version (e.g., \'MongoDB 7.0\', \'PostgreSQL 16\', \'MySQL 8.0 + Redis\')",\n'
    '  "devops": "specific tools + orchestration (e.g., \'Kubernetes + ArgoCD\', \'Docker + GitLab CI\', \'AWS ECS + Terraform\')",\n'
    '  "explanation": "2-4 sentences explaining why THIS stack fits THESE specific requirements. Reference actual requirements by name/type. Highlight trade-offs considered."\n'
    "}\n\n"
    
    "QUALITY STANDARDS:\n"
    "- Be specific: Include versions, not just names (e.g., 'React 18' not 'React')\n"
    "- Be concrete: Actual frameworks, not categories (e.g., 'FastAPI' not 'Python framework')\n"
    "- Be intentional: Every choice must have a requirement-driven justification\n"
    "- Be current: Prefer stable, production-ready versions (avoid bleeding edge unless justified)\n\n"
    
    f"PROJECT REQUIREMENTS:\n{json.dumps(requirements, indent=2, ensure_ascii=True)}\n\n"
    f"PROJECT CONSTRAINTS:\n{json.dumps(constraints, indent=2, ensure_ascii=True)}\n\n"
    
    "Think through your choices step by step before outputting JSON. "
    "Ask yourself: 'Why is this the RIGHT stack for THESE requirements?' not 'What stack do I usually use?'"
)

        if user_request:
            prompt += f"\nLatest user request: {user_request}"

        try:
            response = await self._invoke_llm(prompt)
            text = response.strip()

            # Extract JSON from markdown code blocks if present
            text = self._extract_json_from_response(text)

            parsed = json.loads(text)
            required = {"frontend", "backend", "database", "devops"}
            if not isinstance(parsed, dict) or not required.issubset(parsed.keys()):
                return self._default_tech_stack(constraints), None

            # Handle nested structures: extract string from nested dicts/lists
            result: Dict[str, str] = {}
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

            # Extract rationale/explanation
            explanation = None
            for key in ("explanation", "rationale", "reasoning"):
                if key in parsed and isinstance(parsed[key], str) and parsed[key].strip():
                    explanation = parsed[key].strip()
                    break
            return result, explanation

        except Exception:
            return self._default_tech_stack(constraints), None

    async def _generate_mermaid_diagram(
        self,
        diagram_kind: str,
        requirements_text: str,
        app_type: str,
        existing_diagram: str | None = None,
    ) -> str:
        """Generate Mermaid diagram via LLM with RAG, validation, retry, and fallback.
        When existing_diagram is set (selective regen), prompt asks for an improved/alternative version."""
        
        participants = ["User", "Frontend", "API", "Database"]
        
        # Fallback diagram
        fallback_type = "erd" if diagram_kind == "erd" else "c4_context"
        fallback_diagram = await self.diagram_gen.generate_diagram(
            type=fallback_type,
            context=f"{app_type}: {requirements_text}" if diagram_kind != "erd" else requirements_text,
            participants=participants if diagram_kind != "erd" else None,
        )

        if self.llm_client is None:
            return fallback_diagram

        # When selectively regenerating, ask for a fresh take so output is not a copy
        regen_hint = ""
        if existing_diagram and existing_diagram.strip():
            regen_hint = (
                "The user asked to regenerate this diagram. Below is the current version. "
                "Produce an improved or alternative version that still satisfies the requirements; "
                "vary naming, layout, or structure where reasonable so this is a fresh take, not a copy.\n\n"
                f"Current diagram:\n{existing_diagram.strip()[:2000]}\n\n"
            )

        # Fetch RAG snippets for better diagram generation
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
                f"{regen_hint}"
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
                f"{regen_hint}"
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

            try:
                response = await self._invoke_llm(prompt)
                mermaid = self._extract_mermaid_from_structured_response(
                    raw_text=response,
                    expected_diagram_kind=diagram_kind,
                )
                if diagram_kind == "system" and mermaid:
                    mermaid = self._sanitize_mermaid_flowchart(mermaid)
                if not self._is_valid_mermaid(mermaid):
                    last_parse_error = "Diagram did not start with valid keyword (flowchart/graph/erDiagram/...)."
                    continue
                # Compile with mmdc and get real parse errors for retry
                if attempt == 0:
                    print(f"  [diagram] Validating {diagram_kind} (mmdc)...", flush=True)
                valid, parse_error = validate_mermaid(mermaid)
                if valid:
                    return mermaid
                last_parse_error = parse_error or "Mermaid syntax error."
                continue
            except Exception:
                continue

        return fallback_diagram

    async def _invoke_llm(self, prompt: str) -> str:
        """Invoke LLM with various client interfaces."""
        if hasattr(self.llm_client, "generate"):
            response = await self.llm_client.generate(prompt)
        elif hasattr(self.llm_client, "ainvoke"):
            response = await self.llm_client.ainvoke(prompt)
        else:
            return ""
        
        return response if isinstance(response, str) else str(response)

    # ========================================================================
    # Parsing Helpers
    # ========================================================================

    def _parse_regen_plan(self, response: str) -> RegenPlan:
        """Parse RegenPlan from raw LLM response."""
        text = self._extract_json_from_response(response)
        try:
            return RegenPlan.model_validate_json(text)
        except Exception:
            return RegenPlan(
                artifacts_to_regenerate=["tech_stack", "system_diagram", "data_schema", "deployment_strategy"],
                reasoning="Failed to parse response",
                preserve_artifacts=[]
            )

    def _parse_tech_stack(self, response: str) -> Optional[Dict[str, str]]:
        """Parse tech stack from raw LLM response."""
        text = self._extract_json_from_response(response)
        try:
            parsed = json.loads(text)
            required = {"frontend", "backend", "database", "devops"}
            if isinstance(parsed, dict) and required.issubset(parsed.keys()):
                return {k: str(v) if isinstance(v, str) else str(list(v.values())[0]) if isinstance(v, dict) else str(v) for k, v in parsed.items() if k in required}
        except Exception:
            pass
        return None

    def _extract_json_from_response(self, text: str) -> str:
        """Extract JSON from markdown code blocks if present."""
        text = text.strip()
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        return text

    def _extract_mermaid_code(self, text: str) -> str:
        """Extract Mermaid code from response."""
        text = text.strip()
        # Remove markdown fences
        if "```mermaid" in text:
            start = text.find("```mermaid") + 10
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        
        # Look for diagram start tokens
        for token in ("flowchart", "graph", "erDiagram", "sequenceDiagram"):
            idx = text.find(token)
            if idx != -1:
                return text[idx:].strip()
        return text

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
        """Parse MermaidLLMResponse from LLM JSON output."""
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

    def _default_tech_stack(self, constraints: List[str]) -> Dict[str, str]:
        """Generate default tech stack based on constraints."""
        constraints_text = " ".join(str(c).lower() for c in constraints)
        backend = "FastAPI (Python)" if "python" in constraints_text else "Node.js (NestJS)"
        return {
            "frontend": "React (Next.js)",
            "backend": backend,
            "database": "PostgreSQL",
            "devops": "Docker + GitHub Actions",
        }

    def _deterministic_regen_plan(self, user_request: str) -> Optional[RegenPlan]:
        """Return a deterministic regeneration plan for explicit requests."""
        text = user_request.lower()
        all_artifacts = ["tech_stack", "system_diagram", "data_schema", "deployment_strategy"]

        def plan(artifacts: List[str], reason: str) -> RegenPlan:
            preserve = [a for a in all_artifacts if a not in artifacts]
            return RegenPlan(
                artifacts_to_regenerate=artifacts,
                reasoning=reason,
                preserve_artifacts=preserve,
            )

        if any(phrase in text for phrase in ("regenerate everything", "redo everything", "rebuild everything")):
            return plan(all_artifacts, "User explicitly requested full regeneration")

        only_requested = any(token in text for token in ("only", "just"))
        if only_requested and any(token in text for token in ("erd", "data schema", "database schema")):
            return plan(["data_schema"], "User explicitly requested ERD/data schema only")
        if only_requested and any(token in text for token in ("system diagram", "context diagram", "architecture diagram")):
            return plan(["system_diagram"], "User explicitly requested system diagram only")
        if only_requested and any(token in text for token in ("tech stack", "stack")):
            return plan(["tech_stack"], "User explicitly requested tech stack only")
        if only_requested and "deployment" in text:
            return plan(["deployment_strategy"], "User explicitly requested deployment strategy only")

        if "database" in text and any(token in text for token in ("change", "switch", "migrate", "use", "to ")):
            return plan(
                ["tech_stack", "data_schema", "deployment_strategy"],
                "Database change impacts stack, schema, and deployment strategy",
            )
        if "backend" in text and any(token in text for token in ("change", "switch", "migrate", "use", "to ")):
            return plan(
                ["tech_stack", "deployment_strategy"],
                "Backend change impacts stack and deployment strategy",
            )
        if "frontend" in text and any(token in text for token in ("change", "switch", "migrate", "use", "to ")):
            return plan(
                ["tech_stack", "deployment_strategy"],
                "Frontend change impacts stack and deployment strategy",
            )

        return None

    def _reconcile_constraints_with_user_request(
        self, constraints: List[str], user_request: Optional[str]
    ) -> List[str]:
        """
        Reconcile older constraints with the latest user request.
        If they conflict, latest user request wins.
        """
        if not user_request:
            return list(constraints)

        text = user_request.lower()
        updated = list(constraints)

        backend_target = self._extract_target_value(
            text,
            ["backend"],
            {
                "python": "Python",
                "node.js": "Node.js",
                "node": "Node.js",
                "express": "Node.js (Express)",
                "fastapi": "Python (FastAPI)",
                "django": "Python (Django)",
                "flask": "Python (Flask)",
                "java": "Java",
                "spring": "Java (Spring)",
            },
        )
        if backend_target is not None:
            updated = [
                c for c in updated
                if not self._constraint_mentions_any(
                    c,
                    [
                        "backend", "python", "fastapi", "django", "flask", "node",
                        "express", "java", "spring", "nestjs", ".net", "dotnet",
                    ],
                )
            ]
            updated.append(f"Must use {backend_target} for backend")

        database_target = self._extract_target_value(
            text,
            ["database", "db"],
            {
                "postgresql": "PostgreSQL",
                "postgres": "PostgreSQL",
                "mysql": "MySQL",
                "mongodb": "MongoDB",
                "mongo": "MongoDB",
                "sqlite": "SQLite",
                "redis": "Redis",
            },
        )
        if database_target is not None:
            updated = [
                c for c in updated
                if not self._constraint_mentions_any(
                    c,
                    ["database", "db", "postgres", "mysql", "mongo", "sqlite", "redis"],
                )
            ]
            updated.append(f"Must use {database_target} for database")

        frontend_target = self._extract_target_value(
            text,
            ["frontend"],
            {
                "react": "React",
                "next.js": "Next.js",
                "next": "Next.js",
                "vue": "Vue",
                "angular": "Angular",
                "svelte": "Svelte",
            },
        )
        if frontend_target is not None:
            updated = [
                c for c in updated
                if not self._constraint_mentions_any(
                    c,
                    ["frontend", "react", "next", "vue", "angular", "svelte"],
                )
            ]
            updated.append(f"Must use {frontend_target} for frontend")

        return updated

    def _extract_target_value(
        self,
        request_text: str,
        domain_tokens: List[str],
        candidate_map: Dict[str, str],
    ) -> Optional[str]:
        """Extract an explicit target technology for a domain from a request string."""
        if not any(token in request_text for token in domain_tokens):
            return None
        if not any(token in request_text for token in ("change", "switch", "migrate", "use", "to ")):
            return None

        for key, value in candidate_map.items():
            pattern = r"\b" + re.escape(key) + r"\b"
            if re.search(pattern, request_text):
                return value
        return None

    def _constraint_mentions_any(self, constraint: str, keywords: List[str]) -> bool:
        text = constraint.lower()
        return any(keyword in text for keyword in keywords)

    # ========================================================================
    # Review Protocol
    # ========================================================================

    async def review(
        self, artifact: Any, context: Optional[dict] = None
    ) -> ReviewResult:
        """Validate architecture output."""
        base_result = await super().review(artifact, context or {})
        issues = list(base_result.feedback)

        if not isinstance(artifact, dict):
            issues.append("Architect output must be a dictionary")
            return ReviewResult(
                is_valid=False, score=0.0, feedback=self._dedupe(issues),
                detailed_scores=base_result.detailed_scores,
            )

        if not artifact.get("summary"):
            issues.append("Architecture summary is missing")

        architecture = artifact.get("architecture")
        if not isinstance(architecture, dict):
            issues.append("Architecture payload must be a dictionary")
            return ReviewResult(
                is_valid=False, score=0.0, feedback=self._dedupe(issues),
                detailed_scores=base_result.detailed_scores,
            )

        required_fields = ("tech_stack", "system_diagram", "data_schema")
        for field_name in required_fields:
            if not architecture.get(field_name):
                issues.append(f"Architecture field missing: {field_name}")

        tech_stack = architecture.get("tech_stack", {})
        if isinstance(tech_stack, dict):
            required_stack_keys = {"frontend", "backend", "database", "devops"}
            missing = sorted(required_stack_keys.difference(tech_stack.keys()))
            if missing:
                issues.append(f"Tech stack missing required components: {', '.join(missing)}")

        for diagram_field in ("system_diagram", "data_schema"):
            if not self._is_valid_mermaid(architecture.get(diagram_field)):
                issues.append(f"Invalid Mermaid syntax in {diagram_field}")

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
        """BaseAgent interface for execute() compatibility."""
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

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _extract_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        requirements = input_data.get("requirements")
        if isinstance(requirements, ProjectState):
            return requirements.requirements.model_dump()
        if isinstance(input_data.get("state"), ProjectState):
            return input_data["state"].requirements.model_dump()
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
