# Schema Design Verification

This document maps each agent's output structure to the database schema, verifying that persistence is exhaustive and follows the orchestrator flow.

## Agent Output → Database Mapping

### 1. requirements_collector

**Agent Output** ([src/agents/requirements_collector.py](../src/agents/requirements_collector.py)):
```python
{
    "response": str,
    "requirements": RequirementsState,  # Pydantic model
    "is_complete": bool,
    "progress": float,
    "decisions": list[str],
    "assumptions": list[str]
}
```

**state_delta Extracted**:
```python
{
    "requirements": RequirementsState.model_dump(),
    "decisions": list[str],  # NOTE: top-level on ProjectState
    "assumptions": list[str]  # NOTE: top-level on ProjectState
}
```

**Database Mapping**:
- `projects.requirements` (JSONB) ← `RequirementsState` with fields:
  - `project_type`, `functional`, `non_functional`, `constraints`
  - `user_stories`, `gaps`, `target_users`, `business_goals`
  - `timeline`, `budget`, `is_complete`, `progress`
- `projects.decisions` (TEXT[]) ← `decisions` array
- `projects.assumptions` (TEXT[]) ← `assumptions` array

**Verification**: ✅ All fields persisted

---

### 2. project_architect

**Agent Output** ([src/agents/project_architect.py](../src/agents/project_architect.py)):
```python
{
    "summary": str,
    "architecture": ArchitectureDefinition.model_dump(),
    "state_delta": {
        "architecture": ArchitectureDefinition.model_dump()
    }
}
```

**Database Mapping**:
- `projects.architecture` (JSONB) ← `ArchitectureDefinition` with fields:
  - `tech_stack` (dict: {frontend, backend, database, devops})
  - `tech_stack_rationale` (str)
  - `data_schema` (str, Mermaid ERD)
  - `system_diagram` (str, Mermaid system diagram)
  - `api_design` (list of APIEndpoint objects)
  - `deployment_strategy` (str)

**Verification**: ✅ All fields persisted

---

### 3. execution_planner

**Agent Output** ([src/agents/execution_planner_agent.py](../src/agents/execution_planner_agent.py)):
```python
{
    "summary": str,
    "roadmap": Roadmap.model_dump(),
    "execution_plan": Roadmap.model_dump(),  # backward-compatible
    "state_delta": {
        "roadmap": Roadmap.model_dump()
    }
}
```

**Database Mapping**:
- `projects.roadmap` (JSONB) ← `Roadmap` with nested fields:
  - `phases` (list of Phase: {name, description, order})
  - `milestones` (list of Milestone: {name, description, target_date})
  - `implementation_tasks` (list of ImplementationTask: {id, title, description, phase_name, milestone_name, depends_on, external_resources, order})
  - `sprints` (list of Sprint: {name, goal, tasks})
  - `critical_path` (str)
  - `external_resources` (list[str])

**Verification**: ✅ All fields persisted, complex nested structure in JSONB

---

### 4. mockup_agent

**Agent Output** ([src/agents/mockup_agent.py](../src/agents/mockup_agent.py)):
```python
MockupAgentResponse {
    "wireframe_spec": WireframeSpec,
    "excalidraw_json": dict,
    "export_paths": dict,
    "summary": str,
    "state_delta": {
        "mockups": list[MockupStateEntry.model_dump()]
    },
    "generation_metadata": dict
}
```

**MockupStateEntry structure**:
```python
{
    "screen_name": str,
    "screen_id": str,
    "wireframe_spec": dict,  # Serialized ScreenSpec
    "excalidraw_scene": dict,
    "screenshot_path": str,
    "user_flow": str,
    "interactions": list[str],
    "template_used": str,
    "version": str
}
```

**Database Mapping**:
- `mockups` table (1:N) with columns:
  - `session_id` (FK to projects)
  - `screen_id` (unique per session)
  - `screen_name`
  - `wireframe_spec` (JSONB)
  - `excalidraw_scene` (JSONB)
  - `screenshot_path`
  - `user_flow`
  - `interactions` (TEXT[])
  - `template_used`
  - `version`

**StateManager Merge Strategy**:
- Identity-based merge by `screen_id` (see [StateManager._merge_mockups](../src/state/state_manager.py))
- Allows selective regeneration: update existing screen or add new screen

**Verification**: ✅ All fields persisted, normalized for queryability

---

### 5. exporter

**Agent Output** ([src/agents/exporter_agent.py](../src/agents/exporter_agent.py)):
```python
{
    "content": str,
    "state_delta": {
        "export_artifacts": ExportArtifacts.model_dump()
    },
    "metadata": dict
}
```

**Database Mapping**:
- `projects.export_artifacts` (JSONB) ← `ExportArtifacts` with fields:
  - `executive_summary` (str)
  - `markdown_content` (str)
  - `saved_path` (str)
  - `generated_formats` (list[str])
  - `exported_at` (str, ISO timestamp)
  - `history` (list of export records)

**Verification**: ✅ All fields persisted

---

### 6. conversation_history

**Orchestrator Flow** ([src/orchestrator/master_agent.py](../src/orchestrator/master_agent.py#L260)):
```python
# After agent loop completes:
new_history = list(project_state.conversation_history or [])
new_history.append({"role": "user", "content": user_input})
new_history.append({"role": "assistant", "content": message})
project_state.conversation_history = new_history

# Direct write to db (bypasses StateManager delta merge):
await self.state.db.save(session_id, project_state.model_dump())
```

**Database Mapping**:
- `conversation_messages` table (1:N) with columns:
  - `session_id` (FK to projects)
  - `role` (user | assistant | system)
  - `content` (text)
  - `created_at` (timestamp)
  - `metadata` (JSONB, optional)

**Verification**: ✅ Normalized for efficient append, pagination, and querying

---

## Orchestrator Flow Verification

### State Update Flow

1. **Load** ([orchestrator/master_agent.py](../src/orchestrator/master_agent.py#L93)):
   ```python
   project_state = await self.state.load(session_id)
   ```

2. **Classify Intent** → ExecutionPlanner builds plan → Agent loop

3. **Per Agent** ([orchestrator/master_agent.py](../src/orchestrator/master_agent.py#L240)):
   ```python
   result = await self._run_agent(task, context, user_input, agent)
   state_delta = result.get("state_delta") or {}
   
   if state_delta:
       project_state = await self.state.update(session_id, state_delta)
   ```

4. **Phase Transition** ([orchestrator/master_agent.py](../src/orchestrator/master_agent.py#L248)):
   ```python
   next_phase = PHASE_TRANSITION_MAP.get(task.agent_id)
   if next_phase:
       project_state = await self.state.update(session_id, {"current_phase": next_phase})
   ```

5. **Conversation History** ([orchestrator/master_agent.py](../src/orchestrator/master_agent.py#L260)):
   ```python
   # Direct write (bypasses StateManager merge to avoid duplicates)
   await self.state.db.save(session_id, project_state.model_dump())
   ```

### StateManager Delta Update Pattern

**Dotted-path support** ([state/state_manager.py](../src/state/state_manager.py#L32)):
```python
# Example delta:
{
    "requirements.progress": 0.8,
    "architecture": {...},
    "current_phase": "architecture_complete"
}
```

**Merge strategies**:
- Top-level keys → direct set or merge
- Nested paths (e.g., `requirements.progress`) → traverse and set
- Lists → extend (except mockups use identity merge)
- Dicts → shallow merge
- Pydantic models → merge then rebuild

---

## Schema Coverage Matrix

| ProjectState Field | Type | Storage Location | Agent Producer |
|-------------------|------|------------------|----------------|
| `session_id` | str | `projects.session_id` | — (key) |
| `project_name` | str | `projects.project_name` | — (user input) |
| `created_at` | datetime | `projects.created_at` | — (auto) |
| `updated_at` | datetime | `projects.updated_at` | — (trigger) |
| `current_phase` | str | `projects.current_phase` | orchestrator |
| `agent_selection_mode` | str | `projects.agent_selection_mode` | orchestrator |
| `selected_agent_id` | str | `projects.selected_agent_id` | orchestrator |
| `requirements` | Requirements | `projects.requirements` | requirements_collector |
| `decisions` | list[str] | `projects.decisions` | requirements_collector |
| `assumptions` | list[str] | `projects.assumptions` | requirements_collector |
| `architecture` | ArchitectureDefinition | `projects.architecture` | project_architect |
| `mockups` | list[Mockup] | `mockups` table (1:N) | mockup_agent |
| `roadmap` | Roadmap | `projects.roadmap` | execution_planner |
| `conversation_history` | list[dict] | `conversation_messages` table (1:N) | orchestrator |
| `agent_interactions` | dict[str, int] | `projects.agent_interactions` | orchestrator |
| `export_artifacts` | ExportArtifacts | `projects.export_artifacts` | exporter |

**Coverage**: ✅ 16/16 fields persisted (100%)

---

## Database Design Decisions

### ✅ What's Normalized

1. **conversation_messages** (separate table)
   - **Why**: High-volume, frequently appended, queried independently
   - **Orchestrator pattern**: Direct write (bypasses StateManager)
   - **Query use-cases**: Pagination, chat history, message search

2. **mockups** (separate table)
   - **Why**: Each screen is a queryable entity, identity-based merge
   - **StateManager pattern**: List with special merge logic by `screen_id`
   - **Query use-cases**: "All screens using login template", preview generation

3. **decisions/assumptions** (TEXT[] arrays)
   - **Why**: Simple string lists, no nested structure
   - **StateManager pattern**: List extend

### ✅ What's JSONB

1. **requirements** (JSONB column)
   - **Why**: Variable schema (user_stories structure), dotted-path updates
   - **Update pattern**: `{"requirements.progress": 0.8}`

2. **architecture** (JSONB column)
   - **Why**: Variable tech_stack keys, Mermaid diagrams (long text), API design list
   - **Complete replacement**: Agent regenerates entire architecture atomically

3. **roadmap** (JSONB column)
   - **Why**: Complex nested dependencies (tasks depend on tasks), rarely queried piecemeal
   - **Complete replacement**: execution_planner generates entire roadmap atomically
   - **Alternative considered**: Separate tables for phases/milestones/tasks → rejected (over-normalization, join complexity)

4. **export_artifacts** (JSONB column)
   - **Why**: Simple 1:1, infrequently updated, consumed as whole by exporter

### ❌ What's NOT Normalized

1. **Roadmap phases/milestones/tasks** → kept in JSONB
   - Tasks have `depends_on` (list of task IDs) → self-referential relationships
   - execution_planner generates atomically
   - Consumed as whole by exporter
   - JSONB GIN index supports deep queries if needed

---

## Adapter Implementation Requirements

The `SupabaseAdapter` must implement:

### `get(session_id)` → dict
```sql
SELECT p.*,
       COALESCE(json_agg(DISTINCT cm.* ORDER BY cm.created_at) FILTER (WHERE cm.id IS NOT NULL), '[]') as conversation_history,
       COALESCE(json_agg(DISTINCT m.* ORDER BY m.created_at) FILTER (WHERE m.id IS NOT NULL), '[]') as mockups
FROM projects p
LEFT JOIN conversation_messages cm ON cm.session_id = p.session_id
LEFT JOIN mockups m ON m.session_id = p.session_id
WHERE p.session_id = $1
GROUP BY p.session_id;
```

### `save(session_id, state_dict)` → None

**1. Upsert projects table**:
```sql
INSERT INTO projects (session_id, project_name, current_phase, requirements, architecture, roadmap, ...)
VALUES ($1, $2, $3, $4, $5, $6, ...)
ON CONFLICT (session_id) DO UPDATE SET
    project_name = EXCLUDED.project_name,
    current_phase = EXCLUDED.current_phase,
    requirements = EXCLUDED.requirements,
    ...
    updated_at = NOW();
```

**2. Sync conversation_messages** (if conversation_history in state_dict):
```sql
-- Delete existing messages
DELETE FROM conversation_messages WHERE session_id = $1;

-- Insert new messages (batch)
INSERT INTO conversation_messages (session_id, role, content, created_at)
VALUES ($1, $2, $3, $4), ...;
```

**3. Sync mockups** (if mockups in state_dict):
```sql
-- Upsert each mockup by screen_id
INSERT INTO mockups (session_id, screen_id, screen_name, wireframe_spec, ...)
VALUES ($1, $2, $3, $4, ...)
ON CONFLICT (session_id, screen_id) DO UPDATE SET
    screen_name = EXCLUDED.screen_name,
    wireframe_spec = EXCLUDED.wireframe_spec,
    ...
    updated_at = NOW();
```

### Delta Update Support

StateManager calls `update(session_id, delta)`, which loads, merges, and saves.

**Example delta**:
```python
{
    "requirements.progress": 0.8,
    "current_phase": "requirements_complete"
}
```

**Adapter strategy**: Let StateManager handle merge logic (it already does), then `save()` writes the full merged state.

---

## Conclusion

**Schema validation**: ✅ PASS
- All agent outputs mapped to database
- All ProjectState fields persisted
- Follows orchestrator flow (load → delta update → phase transition → conversation append)
- Balanced normalization: 1:N tables for queryability, JSONB for variable schemas
- Efficient StateManager reconstruction: single JOIN query

**Next step**: Implement `SupabaseAdapter` class in Phase 2.
