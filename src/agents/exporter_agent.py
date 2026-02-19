"""Organizes the final plan into Markdown, Canvas output, PDFs, or GitHub-ready documentation."""

from __future__ import annotations
from typing import Any, Dict, Optional
import json
import os # <-- ADD THIS

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agents.base_agent import BaseAgent
from src.utils.config import settings
from src.state.project_state import ExportArtifacts

# tools/ folder contains helpers
from src.tools.markdown_formatter import format_markdown
from src.tools.pdf_exporter import PDFExporter


class ExporterAgent(BaseAgent):
    """Agent that prepares deliverables for export and validates formatting."""

    def __init__(self, review_config: Optional[dict] = None) -> None:
        """Initialize the agent with Gemini LLM."""
        llm_client = ChatGoogleGenerativeAI(
            model=settings.model_name,
            temperature=0.2,  # Low temperature for highly deterministic formatting
            max_tokens=settings.model_max_tokens,
            google_api_key=settings.gemini_api_key,
        )

        super().__init__(
            name="ExporterAgent",
            llm_client=llm_client,
            review_config=review_config or {"min_score": 0.80}
        )
        print("Initializing Exporter Agent...")

    async def _generate(self, input: Any, context: dict, tools: list) -> Dict[str, Any]:
        """Agent-specific generation logic."""
        print("--- 🚀 EXPORTER AGENT GENERATING ---", flush=True)
        
        # 1. Safely extract state fragments from context or input
        payload = input if isinstance(input, dict) else context
        project_name = payload.get("project_name", "Untitled Project")
        
        # Fault-tolerant extraction: handle both Pydantic models and raw dicts/placeholders
        reqs = self._extract_fragment(payload.get("requirements", {}))
        arch = self._extract_fragment(payload.get("architecture", {}))
        roadmap = self._extract_fragment(payload.get("roadmap", payload.get("plan", {})))
        mockups = self._extract_fragment(payload.get("mockups", payload.get("mockup", {})))

        # 2. Use LLM to write the Executive Summary
        executive_summary = await self._generate_executive_summary(project_name, reqs, arch)

        # 3. Stitch together the core Markdown Document
        print("  [1/2] Compiling Markdown Artifacts...", flush=True)
        raw_markdown = self._compile_markdown(
            project_name=project_name,
            summary=executive_summary,
            reqs=reqs,
            arch=arch,
            roadmap=roadmap,
            mockups=mockups
        )

        # 4. Use the formatting tool to finalize the string
        final_markdown = format_markdown(raw_markdown)

        # 5. Use the PDF Exporter tool to save the file locally
        print("  [2/2] Running PDF Exporter Tool...", flush=True)
        pdf_tool = PDFExporter()
        
        # Create a safe file name (e.g., "Untitled Project" -> "untitled_project.pdf")
        safe_name = project_name.lower().replace(" ", "_")
        
        # Save it to a local 'outputs' directory
        export_dir = "outputs"
        os.makedirs(export_dir, exist_ok=True)
        pdf_destination = os.path.join(export_dir, f"{safe_name}.pdf")
        
        # Call the tool we upgraded!
        pdf_tool.export(content=final_markdown, destination=pdf_destination)

        # 6. Create the ExportArtifacts state delta
        new_artifacts = ExportArtifacts(
            executive_summary=executive_summary,
            markdown_content=final_markdown
        )

        # 7. Return standard BaseAgent payload (Only ONE return statement!)
        return {
            "content": final_markdown,
            "state_delta": {
                "export_artifacts": new_artifacts.model_dump()
            },
            "metadata": {
                "formats_generated": ["markdown", "pdf"],
                "saved_path": pdf_destination
            }
        }

    async def _generate_executive_summary(self, project_name: str, reqs: dict, arch: dict) -> str:
        """Helper to generate a concise summary via LLM."""
        if self.llm_client is None:
            return "Executive summary unavailable (LLM not configured)."

        system_prompt = "You are a Senior Technical Project Manager. Write a highly concise, 2-paragraph executive summary of the following project."
        
        # Truncate context to avoid token limits (mirroring Architect's ContextExtractor pattern)
        reqs_str = json.dumps(reqs)[:1500]
        arch_str = json.dumps(arch)[:1500]
        
        user_prompt = f"Project Name: {project_name}\nRequirements: {reqs_str}\nArchitecture: {arch_str}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            print("  [LLM] Generating Executive Summary...", flush=True)
            response = await self.llm.ainvoke(messages)
            return response.content.strip()
        except Exception as e:
            print(f"  [Error] Failed to generate summary: {e}")
            return "Executive summary generation failed."

    def _compile_markdown(self, project_name: str, summary: str, reqs: dict, arch: dict, roadmap: Any, mockups: Any) -> str:
        """Deterministic Markdown compiler ensuring valid syntax for the Reviewer."""
        md_lines = [f"# {project_name.upper()} - Comprehensive Project Plan\n"]
        md_lines.append(f"## Executive Summary\n{summary}\n")

        # --- REQUIREMENTS ---
        md_lines.append("## 1. Requirements & User Stories\n")
        
        functional = reqs.get("functional", [])
        if functional:
            md_lines.append("### Functional Requirements")
            for req in functional:
                md_lines.append(f"- {req}")
            md_lines.append("\n")
            
        user_stories = reqs.get("user_stories", [])
        if user_stories:
            md_lines.append("### User Stories")
            for story in user_stories:
                role = story.get("role", "User")
                goal = story.get("goal", "do something")
                reason = story.get("reason", "N/A")
                md_lines.append(f"- **As a {role}**, I want to {goal} so that {reason}.")
        md_lines.append("\n")

        # --- ARCHITECTURE ---
        md_lines.append("## 2. System Architecture\n")
        tech_stack = arch.get("tech_stack", {})
        if tech_stack:
            md_lines.append("### Tech Stack")
            for tech, role in tech_stack.items():
                md_lines.append(f"- **{tech}**: {role}")
            md_lines.append("\n")
        
        # System Diagram (Flowchart)
        system_diagram = arch.get("system_diagram")
        if system_diagram and "graph" in system_diagram or "flowchart" in system_diagram:
            md_lines.append("### System Context Diagram")
            md_lines.append("```mermaid\n" + system_diagram + "\n```\n")

        # Data Schema (ERD)
        data_schema = arch.get("data_schema")
        if data_schema and "erDiagram" in data_schema:
            md_lines.append("### Entity Relationship Diagram (ERD)")
            md_lines.append("```mermaid\n" + data_schema + "\n```\n")
            
        deployment = arch.get("deployment_strategy")
        if deployment:
            md_lines.append(f"### Deployment Strategy\n{deployment}\n")

        # --- EXECUTION PLAN (WIP placeholder handling) ---
        md_lines.append("## 3. Execution Roadmap\n")
        if isinstance(roadmap, list):
            # Handles the current {"plan": ["step_one", "step_two"]} placeholder
            for step in roadmap:
                md_lines.append(f"- {step}")
        elif isinstance(roadmap, dict) and "milestones" in roadmap:
            # Handles the future strict Pydantic Roadmap
            for phase in roadmap.get("milestones", []):
                name = phase.get("name", "Unnamed Phase")
                target = phase.get("target_date")
                date_str = f" (Target: {target})" if target else ""
                md_lines.append(f"### {name}{date_str}")
        else:
            md_lines.append("*Execution plan pending generation.*")
        md_lines.append("\n")

        # --- MOCKUPS (WIP placeholder handling) ---
        md_lines.append("## 4. UI/UX Mockups\n")
        if isinstance(mockups, str):
            md_lines.append(f"*{mockups}*")
        elif isinstance(mockups, list):
            for screen in mockups:
                name = screen.get("screen_name", "Screen")
                flow = screen.get("user_flow", "")
                md_lines.append(f"- **{name}**: {flow}")
        else:
            md_lines.append("*Mockups pending generation.*")

        return "\n".join(md_lines)

    def _extract_fragment(self, data: Any) -> Any:
        """Helper to safely extract dicts from Pydantic models or pass through lists/strings."""
        if hasattr(data, "model_dump"):
            return data.model_dump()
        return data

    def _get_quality_criteria(self) -> dict:
        """Return weighted review criteria for the agent."""
        return {
            "completeness": 0.4, # Must contain Summary, Reqs, Arch, Roadmap, and Mockups
            "formatting": 0.4,   # Must be strictly valid Markdown format
            "diagrams": 0.2      # If diagrams exist, they MUST be wrapped in valid ```mermaid fences
        }


# --- SINGLETON PATTERN ---
_agent_instance = None

def get_agent() -> ExporterAgent:
    """Get or create the singleton agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ExporterAgent()
    return _agent_instance