# Orchestrator hardening – implementation status

This doc summarizes what is **implemented** vs what the original Commit 7/8 and related plans described. As of the current codebase, **all of the below are implemented.**

---

## Mockup encoding fix (Windows)

| Item | Status | Where |
|------|--------|--------|
| JSON file write with UTF-8 | Done | `src/agents/mockup_agent.py` line 271: `open(json_path, "w", encoding="utf-8")` |
| HTML file write with UTF-8 | Done | `src/agents/mockup_agent.py` line 462: `open(html_path, 'w', encoding='utf-8')` |
| Console output ASCII-only | Done | Lines 472–475: `[OK]`, `[WARN]`, `->` (no ✓/⚠/→ in print) |

---

## Orchestrator message formatting

| Item | Status | Where |
|------|--------|--------|
| Pass `agent_results` into synthesizer | Done | `master_agent.py` line 253: `_synthesize_response(results, agent_results)` |
| Labeled lines (**AgentName:** content) | Done | `_synthesize_response`: `**{label}:** {c}` when `agent_results` matches |
| Join with newlines | Done | `"\n\n".join(parts)` |
| Truncation for display | Done | `max_display_chars = 500`, full content still in `agent_results` / artifacts |

---

## Commit 7 – Regression and confidence pass

| Goal | Status | Where |
|------|--------|--------|
| Vague follow-up stays on requirements_collector | Done | `tests/unit/test_orchestrator_graph.py`: `test_vague_follow_up_still_stays_on_requirements_collector` |
| Unknown → requirements_collector only | Done | `test_unknown_intent_plans_requirements_collector_only` (same file) |
| Mockup twice same screen_id → single stored screen | Done | `tests/integration/test_orchestrator_state_transitions.py`: "Two mockup generations for the same screen_id should keep one stored mockup entry" |
| Issue summaries visible when agent failures occur | Done | `tests/integration/test_orchestrator_full.py`: `test_failure_message_surfaces_issue_summary` (asserts "Issues:" and status in message) |
| Structured statuses (skipped_unavailable, failed_timeout, blocked_dependency) | Done | Covered in `test_orchestrator_downstream.py` and full/orchestrator tests |
| Export persistence in main orchestration path | Done | `test_export_artifacts_persist_when_exporter_runs`, state_transitions export reload tests |

---

## Commit 8 – Manual mode and availability hardening

| Goal | Status | Where |
|------|--------|--------|
| `available_agents` readiness-aware | Done | `master_agent.py` `_get_available_agents()` returns `is_available`, `unmet_requires`, `blocked_by`, `is_phase_compatible` |
| Manual mode: selected agent + upstream only | Done | Manual path builds plan via `_resolve_upstream([selected_agent_id])` only; no downstream expansion |
| Tests: readiness-aware assertions | Done | `test_available_agents_include_readiness_metadata` asserts `is_available`, `unmet_requires`, `blocked_by` for all agents |
| Manual-mode test (no downstream expansion) | Done | `test_manual_mode_runs_selected_agent_without_downstream_expansion` – architect runs, execution_planner not in call_log |
| Reject unavailable agent selection | Done | `test_manual_mode_rejects_unavailable_agent_selection` – architect unavailable when requirements missing, message and `unmet_requires` asserted |

---

## Summary

- **Mockup encoding:** UTF-8 for JSON/HTML writes; ASCII-only in preview-step prints.
- **Message formatting:** Single user-facing message built from agent results with labels, newlines, and truncation.
- **Commit 7:** Regression tests for vague follow-up, mockup dedup, issue summary visibility, structured statuses, export persistence.
- **Commit 8:** Readiness-aware `available_agents`, manual mode upstream-only, and tests for readiness and manual mode.

The CHANGELOG “Remaining” section (Commit 7 and 8) was written when those commits were still planned; the code and tests above show they are **already implemented**. You can update the CHANGELOG to move those items into “What is in place” or mark them as completed.
