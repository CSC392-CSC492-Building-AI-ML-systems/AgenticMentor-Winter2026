# Merge Plan: Architect Branches

This document summarizes differences between the two architect branches and how to merge them.

---

## Step-by-step: Changes on the LangGraph branch

Work on **agent-refactor-langchain**. These steps keep LangGraph and add our features.



1. **`src/agents/project_architect.py`**
   - **Imports:** Add `from pathlib import Path` and `from src.utils.mermaid_validator import validate_mermaid`. Optionally add `from src.protocols.schemas import MermaidLLMResponse` if you use JSON-with-diagram_type for retry.
   - **`__init__`:** Add `self._mermaid_store: Any = None`.
   - **`ArchitectState`:** Add `tech_stack_rationale: Optional[str]`.
   - **`process()`:** When building the return value, set `state_delta = {"architecture": architecture_dict, "requirements": final_state.get("requirements")}`. When building `ArchitectureDefinition`, pass `tech_stack_rationale=final_state.get("tech_stack_rationale")`.
   - **`_tech_stack_node`:** Make `_generate_tech_stack()` return `(tech_stack_dict, rationale_str)`. In the node, put both into the returned state (e.g. `return {"tech_stack": ..., "tech_stack_rationale": ...}`).
   - **`_generate_tech_stack()`:** Have it return a tuple `(dict, Optional[str])`; parse LLM for an `explanation`/`rationale` field and return it.
   - **`_generate_mermaid_diagram()`:**  
     - Add RAG: call `_get_mermaid_rag_snippets(diagram_kind)` and inject a "Relevant Mermaid syntax" block into the initial prompt.  
     - Use our ERD/system prompts (pipe-only edge labels, quoted node labels, no parens in edges).  
     - After getting mermaid from LLM: for system, run `mermaid = self._sanitize_mermaid_flowchart(mermaid)`.  
     - Call `valid, parse_error = validate_mermaid(mermaid)`. If not valid, retry once with a prompt that includes `parse_error` and optionally `_get_mermaid_rag_snippets(diagram_kind, query_override=parse_error)`. After 2 attempts, return `fallback_diagram`.
   - **Add methods (copy from mermaid-vector-store):** `_get_mermaid_store()`, `_get_mermaid_rag_snippets()`, `_sanitize_mermaid_flowchart()`, and either `_extract_mermaid_from_structured_response()` or keep `_extract_mermaid_code()` and adapt prompts.
   - **Progress logs (optional):** In each node or in `process()`, add prints like `[1/4] Drafting tech stack...`, `[diagram] Validating (mmdc)...`.


2. **Smoke-test**
   - Run integration tests; do one full run and optionally one selective-regen run. Confirm diagrams validate and output includes rationale and requirements.

---

## Branches

| Branch | Purpose |
|--------|--------|
| **project-architect-agent/mermaid-vector-store** (ours) | Linear flow, Mermaid RAG, mmdc validation, retry with error, `tech_stack_rationale`, `state_delta.requirements`, progress logs, flowchart sanitization |
| **origin/project-architect-agent/agent-refactor-langchain** (theirs) | LangGraph `StateGraph` with 5 nodes: `analyze_impact` → `generate_tech_stack` → `generate_system_diagram` → `generate_data_schema` → `generate_deployment`, selective regeneration, `RegenPlan`, `ArchitectState` |

---

## File-by-File Differences

### 1. `src/agents/project_architect.py` (~1100 lines changed)

**Structure**

| Ours (mermaid-vector-store) | Theirs (agent-refactor-langchain) |
|-----------------------------|-----------------------------------|
| Linear `process()`: tech stack → system diagram → ERD → build output | `process()` builds `ArchitectState`, runs `_graph.ainvoke()`, then builds `ArchitectureDefinition` from final state |
| `_draft_tech_stack()` → `_draft_tech_stack_with_llm()` returns `(dict, rationale)` | `_tech_stack_node()` calls `_generate_tech_stack()` (no rationale in state) |
| `_generate_mermaid_with_llm()` with RAG, validate_mermaid, retry, sanitize | `_generate_mermaid_diagram()` with simple prompt, `_is_valid_mermaid()` only, no RAG/retry/sanitize |
| `_get_mermaid_store()`, `_get_mermaid_rag_snippets()`, `_sanitize_mermaid_flowchart()`, `_extract_mermaid_from_structured_response()` | None of these; uses `_extract_mermaid_code()` and `MermaidDiagramOutput` |
| Uses `validate_mermaid()` from `src.utils.mermaid_validator` | No mmdc validation |
| Uses `MermaidLLMResponse` from `src.protocols.schemas` | Uses local `MermaidDiagramOutput` (mermaid_code only) |
| Progress logs: `[1/4]` … `[4/4]`, `[diagram] Validating (mmdc)` | No progress logs in nodes |

**Imports**

- Theirs: `Path`, `MermaidLLMResponse`, `validate_mermaid`.
- Ours: `TypedDict`, `Annotated`, `operator.add`, `pydantic.BaseModel`, `Field`, `langgraph.graph.StateGraph, END`; no `Path`, no `mermaid_validator`, no `MermaidLLMResponse`.


---

## Where Our Features Go in the LangGraph Version

After merging, **start from the LangGraph branch** and re-add our behavior as follows:

| # | Feature (ours) | Where it goes in LangGraph branch |
|---|----------------------------------|-----------------------------------|
| 1 | Progress logs `[1/4]`…`[4/4]`, `[diagram] Validating (mmdc)` | Inside `process()` before/after `_graph.ainvoke()`, or inside each node (e.g. at start of `_tech_stack_node`, `_system_diagram_node`, `_data_schema_node`, and before validation in diagram node). |
| 2 | `tech_stack_rationale` on `ArchitectureDefinition` + in summary | **State:** Add `tech_stack_rationale: Optional[str]` to `ArchitectState`. **Node:** In `_tech_stack_node`, have `_generate_tech_stack()` return `(dict, rationale)` (or a small wrapper type) and put both into state. **Output:** When building `ArchitectureDefinition` in `process()`, pass `tech_stack_rationale=final_state.get("tech_stack_rationale")`. **State model:** Keep `tech_stack_rationale` on `ArchitectureDefinition` in `project_state.py`. |
| 3 | `state_delta.requirements` in `process()` return | In `process()`, after building `architecture_dict`, set `state_delta = {"architecture": architecture_dict, "requirements": requirements}` (get `requirements` from `final_state["requirements"]` or from `initial_state`). |
| 4 | `validate_mermaid()` + retry once with error in prompt | Inside `_generate_mermaid_diagram()`: after getting `mermaid` from LLM, call `validate_mermaid(mermaid)` (from `src.utils.mermaid_validator`). If invalid, retry once with a prompt that includes the parse error (and optional error-based RAG). Cap at 2 attempts then fallback. |
| 5 | RAG: `_get_mermaid_store()`, `_get_mermaid_rag_snippets()`, `query_override` on retry | Add these methods to the merged agent. In `_generate_mermaid_diagram()`, call `_get_mermaid_rag_snippets(diagram_kind)` and inject into the initial prompt; on retry, call `_get_mermaid_rag_snippets(diagram_kind, query_override=last_parse_error)`. Lazy-init `_mermaid_store` in `__init__` (e.g. `self._mermaid_store = None`) and keep `_get_mermaid_store()` as-is. |
| 6 | Prompts: pipe-only edge labels, quoted node labels, no parens in edges | Replace the simple diagram prompts in `_generate_mermaid_diagram()` with the ERD/system prompts from our branch (including the “CRITICAL Mermaid syntax rules” and RAG block). |
| 7 | `_sanitize_mermaid_flowchart()` for system diagram | After extracting mermaid for `diagram_kind == "system"`, set `mermaid = self._sanitize_mermaid_flowchart(mermaid)` before validation. |
| 8 | Bounded: max 2 attempts per diagram, then DiagramGenerator fallback | Already present as fallback in their `_generate_mermaid_diagram()`. Add the retry loop (attempt 0 + 1 retry with error), then return `fallback_diagram` if both fail. |

---

## Quick Reference: Method Mapping

| Our method | Their equivalent | Action |
|-----------|------------------|--------|
| `_draft_tech_stack` / `_draft_tech_stack_with_llm` | `_tech_stack_node` + `_generate_tech_stack` | Make `_generate_tech_stack` return rationale; put it in state and in `ArchitectureDefinition`. |
| `_generate_mermaid_with_llm` | `_generate_mermaid_diagram` | Replace their implementation with our RAG + validation + retry + sanitize logic (keep their signature and fallback). |
| `_get_mermaid_store` / `_get_mermaid_rag_snippets` | — | Add as-is. |
| `_sanitize_mermaid_flowchart` | — | Add as-is; call for system diagram. |
| `_extract_mermaid_from_structured_response` | `_extract_mermaid_code` | Use ours when using JSON-with-diagram_type prompts; otherwise keep theirs and adapt. |
| `validate_mermaid` (from util) | `_is_valid_mermaid` only | Use both: `_is_valid_mermaid` for quick check; `validate_mermaid()` for real parse and retry message. |

---

Run `python scripts/compare_architect_branches.py` for a short checklist and branch pointers.
