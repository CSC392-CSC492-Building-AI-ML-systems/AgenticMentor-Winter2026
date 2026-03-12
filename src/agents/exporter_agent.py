"""Organizes the final plan into Markdown, Canvas output, PDFs, or GitHub-ready documentation."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import json
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agents.base_agent import BaseAgent
from src.utils.config import settings
from src.state.project_state import ExportArtifacts

from src.tools.markdown_formatter import format_markdown
from src.tools.pdf_exporter import PDFExporter


# =============================================================================
# Module-level markdown builders (used by agent and by build_export_markdown)
# =============================================================================

def _requirements_to_markdown(reqs: Any) -> str:
    """Build Requirements & User Stories section. Accepts dict or Pydantic."""
    if hasattr(reqs, "model_dump"):
        reqs = reqs.model_dump()
    reqs = reqs or {}
    lines = ["## 1. Requirements & User Stories\n"]
    functional = reqs.get("functional", [])
    if functional:
        lines.append("### Functional Requirements")
        for req in functional:
            lines.append(f"- {req}")
        lines.append("")
    non_functional = reqs.get("non_functional", [])
    if non_functional:
        lines.append("### Non-Functional Requirements")
        for req in non_functional:
            lines.append(f"- {req}")
        lines.append("")
    constraints = reqs.get("constraints", [])
    if constraints:
        lines.append("### Constraints")
        for c in constraints:
            lines.append(f"- {c}")
        lines.append("")
    user_stories = reqs.get("user_stories", [])
    if user_stories:
        lines.append("### User Stories")
        for story in user_stories:
            s = story if isinstance(story, dict) else (story.model_dump() if hasattr(story, "model_dump") else {})
            role = s.get("role", "User")
            goal = s.get("goal", "do something")
            reason = s.get("reason", "N/A")
            lines.append(f"- **As a {role}**, I want to {goal} so that {reason}.")
        lines.append("")
    if not (functional or non_functional or constraints or user_stories):
        return ""
    return "\n".join(lines)


def _architecture_to_markdown(arch: Any) -> str:
    """Build System Architecture section. Accepts dict or Pydantic."""
    if hasattr(arch, "model_dump"):
        arch = arch.model_dump()
    arch = arch or {}
    lines = ["## 2. System Architecture\n"]
    tech_stack = arch.get("tech_stack", {})
    if tech_stack:
        lines.append("### Tech Stack")
        for tech, role in tech_stack.items():
            lines.append(f"- **{tech}**: {role}")
        lines.append("")
    rationale = arch.get("tech_stack_rationale")
    if rationale:
        lines.append(f"*{rationale}*\n")
    system_diagram = arch.get("system_diagram")
    if system_diagram and ("graph" in system_diagram or "flowchart" in system_diagram):
        lines.append("### System Context Diagram")
        lines.append("```mermaid")
        lines.append(system_diagram)
        lines.append("```\n")
    data_schema = arch.get("data_schema")
    if data_schema and "erDiagram" in data_schema:
        lines.append("### Entity Relationship Diagram (ERD)")
        lines.append("```mermaid")
        lines.append(data_schema)
        lines.append("```\n")
    api_design = arch.get("api_design", [])
    if api_design:
        lines.append("### API Design")
        for api in api_design:
            a = api if isinstance(api, dict) else (api.model_dump() if hasattr(api, "model_dump") else {})
            method = a.get("method", "")
            path = a.get("path", "")
            desc = a.get("description", "")
            lines.append(f"- **{method}** `{path}` — {desc}")
        lines.append("")
    deployment = arch.get("deployment_strategy")
    if deployment:
        lines.append("### Deployment Strategy")
        lines.append(f"{deployment}\n")
    if not (tech_stack or system_diagram or data_schema or api_design or deployment):
        return ""
    return "\n".join(lines)


def _roadmap_to_markdown(roadmap: Any) -> str:
    """Build Execution Roadmap section. Supports phases, milestones, tasks, sprints, critical_path."""
    if isinstance(roadmap, list):
        if not roadmap:
            return ""
        lines = ["## 3. Execution Roadmap\n"]
        for step in roadmap:
            lines.append(f"- {step}")
        lines.append("")
        return "\n".join(lines)
    lines = ["## 3. Execution Roadmap\n"]

    if not isinstance(roadmap, dict):
        return ""

    # Phases (Execution Planner output)
    phases = roadmap.get("phases") or []
    if phases:
        lines.append("### Phases")
        for p in phases:
            ph = p if isinstance(p, dict) else (p.model_dump() if hasattr(p, "model_dump") else {})
            name = ph.get("name", "Unnamed Phase")
            desc = ph.get("description", "")
            order = ph.get("order", 0)
            lines.append(f"- **[{order}] {name}**: {desc}")
        lines.append("")

    # Milestones
    milestones = roadmap.get("milestones") or []
    if milestones:
        lines.append("### Milestones")
        for m in milestones:
            mm = m if isinstance(m, dict) else (m.model_dump() if hasattr(m, "model_dump") else {})
            name = mm.get("name", "Unnamed")
            target = mm.get("target_date", "TBD")
            desc = mm.get("description", "")
            lines.append(f"- **{name}** (Target: {target}): {desc}")
        lines.append("")

    # Implementation tasks
    tasks = roadmap.get("implementation_tasks") or []
    if tasks:
        lines.append("### Implementation Tasks")
        for t in tasks:
            tt = t if isinstance(t, dict) else (t.model_dump() if hasattr(t, "model_dump") else {})
            tid = tt.get("id", "?")
            title = tt.get("title", "")
            phase_name = tt.get("phase_name", "")
            milestone_name = tt.get("milestone_name", "")
            deps = tt.get("depends_on", [])
            deps_str = ", ".join(deps) if deps else "none"
            resources = tt.get("external_resources", [])
            lines.append(f"- **[{tid}]** {title}")
            if phase_name or milestone_name:
                lines.append(f"  - Phase: {phase_name}  |  Milestone: {milestone_name}")
            lines.append(f"  - Depends on: {deps_str}")
            if resources:
                lines.append(f"  - Resources: {', '.join(resources[:5])}")
        lines.append("")

    # Sprints
    sprints = roadmap.get("sprints") or []
    if sprints:
        lines.append("### Sprints")
        for s in sprints:
            ss = s if isinstance(s, dict) else (s.model_dump() if hasattr(s, "model_dump") else {})
            name = ss.get("name", "Sprint")
            goal = ss.get("goal", "")
            task_list = ss.get("tasks", [])
            lines.append(f"- **{name}**: {goal} ({len(task_list)} tasks)")
            for task_ref in task_list[:10]:
                lines.append(f"  - {task_ref}")
            if len(task_list) > 10:
                lines.append(f"  - ... and {len(task_list) - 10} more")
        lines.append("")

    # Critical path
    critical_path = roadmap.get("critical_path")
    if critical_path:
        lines.append("### Critical Path")
        lines.append(f"`{critical_path}`")
        lines.append("")

    if not (phases or milestones or tasks or sprints or critical_path):
        return ""
    return "\n".join(lines)


def _mockups_to_markdown(mockups: Any) -> str:
    """Build UI/UX Mockups section. Supports legacy and rich mockup payloads."""
    lines = ["## 4. UI/UX Mockups\n"]
    if isinstance(mockups, str):
        lines.append(f"*{mockups}*")
        lines.append("")
        return "\n".join(lines)
    if not isinstance(mockups, list) or not mockups:
        return ""
    for screen in mockups:
        s = screen if isinstance(screen, dict) else (screen.model_dump() if hasattr(screen, "model_dump") else {})
        name = s.get("screen_name", "Screen")
        flow = s.get("user_flow", "")
        lines.append(f"- **{name}**: {flow}" if flow else f"- **{name}**")
        interactions = s.get("interactions", [])
        if interactions:
            lines.append("  - Interactions: " + ", ".join(interactions))
        if s.get("screenshot_path"):
            lines.append("  - Preview: " + str(s["screenshot_path"]))

        raw_wireframe = s.get("wireframe_code")
        wireframe_code = raw_wireframe.strip() if isinstance(raw_wireframe, str) else ""
        if not wireframe_code:
            if s.get("excalidraw_scene"):
                wireframe_code = json.dumps(s.get("excalidraw_scene"), indent=2)
            elif s.get("wireframe_spec"):
                wireframe_code = json.dumps(s.get("wireframe_spec"), indent=2)

        if wireframe_code:
            # Match mockup agent output: Excalidraw JSON, or HTML/Mermaid snippets
            if wireframe_code.startswith("{") and ("\"type\": \"excalidraw\"" in wireframe_code or "\"elements\"" in wireframe_code):
                lang = "json"
            elif "<" in wireframe_code and ">" in wireframe_code:
                lang = "html"
            elif "graph" in wireframe_code or "flowchart" in wireframe_code:
                lang = "mermaid"
            else:
                lang = "text"
            lines.append("  - Wireframe:")
            lines.append("")
            # Cap size so PDF stays readable (Excalidraw JSON is often one long line)
            max_wireframe_chars = 2000
            truncated = len(wireframe_code) > max_wireframe_chars
            wireframe_preview = wireframe_code[:max_wireframe_chars] if truncated else wireframe_code
            lines.append("```" + lang)
            for wline in wireframe_preview.split("\n")[:30]:
                lines.append(wline)
            if truncated or wireframe_code.count("\n") >= 30:
                lines.append("... (truncated; full wireframe in app)")
            lines.append("```")
    lines.append("")
    return "\n".join(lines)


def compile_markdown_document(
    project_name: str,
    summary: str,
    reqs: Any,
    arch: Any,
    roadmap: Any,
    mockups: Any,
) -> str:
    """Build full export markdown from project name, summary, and state fragments."""
    name = (project_name or "Untitled Project").strip() or "Untitled Project"
    title = f"# {name.upper()} - Comprehensive Project Plan\n"
    exec_summary = f"## Executive Summary\n{summary}\n"
    parts = [title, exec_summary]
    for section in (_requirements_to_markdown(reqs), _architecture_to_markdown(arch), _roadmap_to_markdown(roadmap), _mockups_to_markdown(mockups)):
        if section:
            parts.append(section)
    return "".join(parts)


def build_export_markdown(context: Dict[str, Any], project_name: Optional[str] = None) -> str:
    """Build full export markdown from a context dict (e.g. project state). Used by tests and callers."""
    if project_name is None:
        project_name = context.get("project_name", "Untitled Project")
    reqs = context.get("requirements", {})
    arch = context.get("architecture", {})
    roadmap = context.get("roadmap", context.get("plan", {}))
    mockups = context.get("mockups", context.get("mockup", []))
    if hasattr(reqs, "model_dump"):
        reqs = reqs.model_dump()
    if hasattr(arch, "model_dump"):
        arch = arch.model_dump()
    if hasattr(roadmap, "model_dump"):
        roadmap = roadmap.model_dump()
    if isinstance(mockups, list) and mockups and hasattr(mockups[0], "model_dump"):
        mockups = [m.model_dump() for m in mockups]
    summary = "Exported project plan."
    return compile_markdown_document(project_name, summary, reqs, arch, roadmap, mockups)


# =============================================================================
# ExporterAgent
# =============================================================================

class ExporterAgent(BaseAgent):
    """Agent that prepares deliverables for export and validates formatting.

    Can be called at any stage of the flow. Missing requirements, architecture,
    roadmap, or mockups are omitted (no "pending" or "missing" text); partial
    state still produces a valid document with only the sections that have data.
    """

    def __init__(self, review_config: Optional[dict] = None) -> None:
        """Initialize the agent with Gemini LLM."""
        llm_client = ChatGoogleGenerativeAI(
            model=settings.model_name,
            temperature=0.2,
            max_tokens=settings.model_max_tokens,
            google_api_key=settings.gemini_api_key,
        )
        super().__init__(
            name="ExporterAgent",
            llm_client=llm_client,
            review_config=review_config or {"min_score": 0.80},
        )
        # print("Initializing Exporter Agent...")

    async def _generate(self, input: Any, context: dict, tools: list) -> Dict[str, Any]:
        """Agent-specific generation logic."""
        # print("--- EXPORTER AGENT GENERATING ---", flush=True)
        payload = input if isinstance(input, dict) else context
        project_name = payload.get("project_name") or "Untitled Project"
        if not isinstance(project_name, str):
            project_name = "Untitled Project"
        reqs = self._extract_fragment(payload.get("requirements", {}))
        arch = self._extract_fragment(payload.get("architecture", {}))
        roadmap = self._extract_fragment(payload.get("roadmap", payload.get("plan", {})))
        mockups = self._extract_fragment(payload.get("mockups", payload.get("mockup", {})))

        executive_summary = await self._generate_executive_summary(project_name, reqs, arch, roadmap, mockups)
        # print("  [1/2] Compiling Markdown Artifacts...", flush=True)
        raw_markdown = compile_markdown_document(
            project_name=project_name,
            summary=executive_summary,
            reqs=reqs,
            arch=arch,
            roadmap=roadmap,
            mockups=mockups,
        )
        final_markdown = format_markdown(raw_markdown)

        # print("  [2/2] Running PDF Exporter Tool...", flush=True)
        pdf_tool = PDFExporter()
        safe_name = (project_name or "Untitled Project").lower().replace(" ", "_")
        export_dir = "outputs"
        os.makedirs(export_dir, exist_ok=True)
        pdf_destination = os.path.join(export_dir, f"{safe_name}.pdf")
        pdf_tool.export(content=final_markdown, destination=pdf_destination)

        # Use actual written path: HTML fallback writes to .html
        saved_path = pdf_destination
        if not os.path.exists(pdf_destination):
            html_fallback = pdf_destination.replace(".pdf", ".html")
            if os.path.exists(html_fallback):
                saved_path = html_fallback

        existing_artifacts = payload.get("export_artifacts", {})
        if hasattr(existing_artifacts, "model_dump"):
            existing_artifacts = existing_artifacts.model_dump()
        existing_artifacts = existing_artifacts or {}
        generated_formats = ["markdown", "pdf"]
        exported_at = datetime.now(timezone.utc).isoformat()
        history = list(existing_artifacts.get("history") or [])
        history.append(
            {
                "saved_path": saved_path,
                "generated_formats": generated_formats,
                "exported_at": exported_at,
            }
        )
        new_artifacts = ExportArtifacts(
            executive_summary=executive_summary,
            markdown_content=final_markdown,
            saved_path=saved_path,
            generated_formats=generated_formats,
            exported_at=exported_at,
            history=history,
        )
        return {
            "content": final_markdown,
            "state_delta": {
                "export_artifacts": new_artifacts.model_dump(),
            },
            "metadata": {
                "formats_generated": ["markdown", "pdf"],
                "saved_path": saved_path,
            },
        }

    async def _generate_executive_summary(
        self,
        project_name: str,
        reqs: dict,
        arch: dict,
        roadmap: Any = None,
        mockups: Any = None,
    ) -> str:
        """Helper to generate a concise summary via LLM. Uses a slice of each payload section."""
        if self.llm_client is None:
            return "Executive summary unavailable (LLM not configured)."
        system_prompt = (
            "You are a Senior Technical Project Manager. Write a highly concise, 2-paragraph executive summary of the following project. "
            "Describe ONLY what is in the provided Requirements (and Architecture/Roadmap). Do not add features that are not listed—e.g. if 'user authentication' or 'authentication' is not in the Requirements, do not mention it."
        )
        # Include a bit of every available section (truncated so prompt stays reasonable)
        max_chars = 1000
        reqs_str = json.dumps(reqs)[:max_chars] if reqs else "(none)"
        arch_str = json.dumps(arch)[:max_chars] if arch else "(none)"
        roadmap_str = json.dumps(roadmap)[:max_chars] if roadmap else "(none)"
        mockups_str = json.dumps(mockups)[:max_chars] if mockups else "(none)"
        user_prompt = (
            f"Project Name: {project_name}\n"
            f"Requirements: {reqs_str}\n"
            f"Architecture: {arch_str}\n"
            f"Roadmap: {roadmap_str}\n"
            f"Mockups: {mockups_str}"
        )
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        try:
            # print("  [LLM] Generating Executive Summary...", flush=True)
            response = await self.llm.ainvoke(messages)
            return response.content.strip()
        except Exception as e:
            # print(f"  [Error] Failed to generate summary: {e}")
            return "Executive summary generation failed."

    def _extract_fragment(self, data: Any) -> Any:
        """Helper to safely extract dicts from Pydantic models or pass through."""
        if hasattr(data, "model_dump"):
            return data.model_dump()
        return data

    def _get_quality_criteria(self) -> dict:
        """Return weighted review criteria for the agent."""
        return {
            "completeness": 0.4,
            "formatting": 0.4,
            "diagrams": 0.2,
        }


_agent_instance: Optional[ExporterAgent] = None


def get_agent() -> ExporterAgent:
    """Get or create the singleton agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ExporterAgent()
    return _agent_instance
