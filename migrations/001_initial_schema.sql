-- ============================================================================
-- AgenticMentor Database Schema - Initial Migration
-- ============================================================================
-- Normalized schema for AgenticMentor orchestrator with:
-- - Core project metadata in main table
-- - JSONB for complex/variable-schema agent outputs (requirements, architecture, roadmap)
-- - Separate tables for high-volume 1:N relationships (messages, mockups)
--
-- Migration: 001_initial_schema.sql
-- Date: March 7, 2026
-- ============================================================================

-- ============================================================================
-- Table: projects
-- ============================================================================
-- Core project metadata and 1:1 agent outputs (requirements, architecture, roadmap, export)

CREATE TABLE IF NOT EXISTS projects (
    -- Primary Key
    session_id TEXT PRIMARY KEY,
    
    -- Core Metadata
    project_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_phase TEXT NOT NULL DEFAULT 'initialization',
    
    -- Agent Selection Mode (auto vs manual)
    agent_selection_mode TEXT NOT NULL DEFAULT 'auto' CHECK (agent_selection_mode IN ('auto', 'manual')),
    selected_agent_id TEXT,
    
    -- Agent Interaction Tracking (simple dict: {agent_id: count})
    agent_interactions JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- ========================================================================
    -- Agent Outputs (1:1 JSONB columns)
    -- ========================================================================
    
    -- Requirements (from requirements_collector agent)
    -- src/state/project_state.py::Requirements
    requirements JSONB NOT NULL DEFAULT '{
        "project_type": null,
        "functional": [],
        "non_functional": [],
        "constraints": [],
        "user_stories": [],
        "gaps": [],
        "target_users": [],
        "business_goals": [],
        "timeline": null,
        "budget": null,
        "is_complete": false,
        "progress": 0.0
    }'::jsonb,
    
    -- Decisions and Assumptions (top-level on ProjectState, populated by requirements_collector)
    decisions TEXT[] DEFAULT ARRAY[]::TEXT[],
    assumptions TEXT[] DEFAULT ARRAY[]::TEXT[],
    
    -- Architecture (from project_architect agent)
    -- src/state/project_state.py::ArchitectureDefinition
    architecture JSONB NOT NULL DEFAULT '{
        "tech_stack": {},
        "tech_stack_rationale": null,
        "data_schema": null,
        "system_diagram": null,
        "api_design": [],
        "deployment_strategy": null
    }'::jsonb,
    
    -- Roadmap (from execution_planner agent)
    -- src/state/project_state.py::Roadmap
    -- Complex nested structure: phases, milestones, implementation_tasks, sprints
    roadmap JSONB NOT NULL DEFAULT '{
        "phases": [],
        "milestones": [],
        "implementation_tasks": [],
        "sprints": [],
        "critical_path": null,
        "external_resources": []
    }'::jsonb,
    
    -- Export Artifacts (from exporter agent)
    -- src/state/project_state.py::ExportArtifacts
    export_artifacts JSONB NOT NULL DEFAULT '{
        "executive_summary": null,
        "markdown_content": null,
        "saved_path": null,
        "generated_formats": [],
        "exported_at": null,
        "history": []
    }'::jsonb
);

-- ============================================================================
-- Table: conversation_messages
-- ============================================================================
-- High-volume conversation history (1:N relationship with projects)
-- Separated for efficient querying, pagination, and targeted updates

CREATE TABLE IF NOT EXISTS conversation_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES projects(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Optional metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

-- ============================================================================
-- Table: mockups
-- ============================================================================
-- UI wireframe screens (1:N relationship with projects)
-- Each screen is a queryable entity with wireframe spec and Excalidraw scene

CREATE TABLE IF NOT EXISTS mockups (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES projects(session_id) ON DELETE CASCADE,
    
    -- Screen Identity
    screen_id TEXT NOT NULL,
    screen_name TEXT NOT NULL,
    
    -- Mockup Data (from mockup_agent)
    -- src/models/mockup_contract.py::MockupStateEntry
    wireframe_spec JSONB NOT NULL,          -- Serialized ScreenSpec (components, layout)
    excalidraw_scene JSONB,                 -- Full Excalidraw JSON for this screen
    
    -- Export Paths and Metadata
    screenshot_path TEXT,                    -- Path to PNG/HTML preview
    user_flow TEXT,                          -- Mermaid diagram showing navigation
    interactions TEXT[] DEFAULT ARRAY[]::TEXT[],
    template_used TEXT NOT NULL,
    version TEXT DEFAULT '1.0',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure unique screen_id per session (for identity-based merging)
    UNIQUE(session_id, screen_id)
);

-- ============================================================================
-- Indexes
-- ============================================================================

-- Projects table indexes
CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_projects_current_phase ON projects(current_phase);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);

-- JSONB GIN indexes for deep querying
CREATE INDEX IF NOT EXISTS idx_projects_requirements_gin ON projects USING GIN (requirements);
CREATE INDEX IF NOT EXISTS idx_projects_architecture_gin ON projects USING GIN (architecture);
CREATE INDEX IF NOT EXISTS idx_projects_roadmap_gin ON projects USING GIN (roadmap);

-- Conversation messages indexes
CREATE INDEX IF NOT EXISTS idx_conversation_messages_session_id ON conversation_messages(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_created_at ON conversation_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_role ON conversation_messages(session_id, role);

-- Mockups indexes
CREATE INDEX IF NOT EXISTS idx_mockups_session_id ON mockups(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_mockups_screen_id ON mockups(screen_id);
CREATE INDEX IF NOT EXISTS idx_mockups_template_used ON mockups(template_used);

-- JSONB GIN indexes on mockups for querying wireframe components
CREATE INDEX IF NOT EXISTS idx_mockups_wireframe_spec_gin ON mockups USING GIN (wireframe_spec);

-- ============================================================================
-- Triggers
-- ============================================================================

-- Auto-update updated_at timestamp on projects table
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at timestamp on mockups table
CREATE TRIGGER trigger_update_mockups_updated_at
    BEFORE UPDATE ON mockups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Comments (Schema Documentation)
-- ============================================================================

COMMENT ON TABLE projects IS 
    'Core project metadata and 1:1 agent outputs (requirements, architecture, roadmap, export). Each row represents a single project session.';

COMMENT ON COLUMN projects.session_id IS 
    'Unique identifier for the project session (primary key)';

COMMENT ON COLUMN projects.current_phase IS 
    'Current phase in the workflow: initialization, discovery, requirements_complete, architecture_complete, planning_complete, design_complete, exportable';

COMMENT ON COLUMN projects.requirements IS 
    'Requirements fragment (RequirementsState) - project type, features, constraints, user stories, completion status';

COMMENT ON COLUMN projects.decisions IS 
    'Design decisions made during requirements collection (array of text)';

COMMENT ON COLUMN projects.assumptions IS 
    'Assumptions documented during requirements collection (array of text)';

COMMENT ON COLUMN projects.architecture IS 
    'Architecture definition (ArchitectureDefinition) - tech stack, system diagrams, API design, deployment strategy';

COMMENT ON COLUMN projects.roadmap IS 
    'Execution plan (Roadmap) - phases, milestones, implementation tasks with dependencies, sprints';

COMMENT ON COLUMN projects.export_artifacts IS 
    'Final exported artifacts (ExportArtifacts) - markdown, PDFs, export history';

COMMENT ON TABLE conversation_messages IS 
    'Conversation history messages (1:N with projects). Stores user, assistant, and system messages with timestamps.';

COMMENT ON COLUMN conversation_messages.role IS 
    'Message sender role: user, assistant, or system';

COMMENT ON COLUMN conversation_messages.metadata IS 
    'Optional metadata for the message (agent_id, intent, etc.)';

COMMENT ON TABLE mockups IS 
    'UI wireframe screens (1:N with projects). Each screen has wireframe spec and Excalidraw scene.';

COMMENT ON COLUMN mockups.wireframe_spec IS 
    'Structured wireframe specification (ScreenSpec) - components, layout, template-based design';

COMMENT ON COLUMN mockups.excalidraw_scene IS 
    'Complete Excalidraw JSON scene for visual rendering';

COMMENT ON COLUMN mockups.screen_id IS 
    'Unique identifier for the screen within the project (slug format: login, dashboard, etc.)';

-- ============================================================================
-- Sample Queries (Reference)
-- ============================================================================

-- Find all projects in requirements phase
-- SELECT session_id, project_name, created_at, current_phase
-- FROM projects
-- WHERE current_phase = 'requirements_complete'
-- ORDER BY updated_at DESC;

-- Find projects with specific tech stack
-- SELECT session_id, project_name, 
--        architecture->'tech_stack'->>'backend' as backend,
--        architecture->'tech_stack'->>'frontend' as frontend
-- FROM projects
-- WHERE architecture->'tech_stack'->>'backend' = 'FastAPI';

-- Get recent conversation for a session
-- SELECT role, content, created_at
-- FROM conversation_messages
-- WHERE session_id = 'your-session-id'
-- ORDER BY created_at DESC
-- LIMIT 10;

-- Check requirements completion across all projects
-- SELECT session_id, project_name,
--        requirements->>'is_complete' as is_complete,
--        (requirements->>'progress')::float as progress
-- FROM projects
-- WHERE requirements->>'is_complete' = 'true';

-- Get all mockup screens for a project
-- SELECT screen_id, screen_name, template_used,
--        jsonb_array_length(wireframe_spec->'components') as component_count
-- FROM mockups
-- WHERE session_id = 'your-session-id'
-- ORDER BY created_at;

-- Find implementation tasks with dependencies (within roadmap JSONB)
-- SELECT session_id, project_name,
--        jsonb_array_length(roadmap->'implementation_tasks') as task_count,
--        roadmap->'critical_path' as critical_path
-- FROM projects
-- WHERE roadmap->'implementation_tasks' != '[]'::jsonb;

-- Count messages per session
-- SELECT session_id, COUNT(*) as message_count,
--        COUNT(*) FILTER (WHERE role = 'user') as user_messages,
--        COUNT(*) FILTER (WHERE role = 'assistant') as assistant_messages
-- FROM conversation_messages
-- GROUP BY session_id
-- ORDER BY message_count DESC;

-- Get full project state for StateManager reconstruction
-- SELECT p.*,
--        COALESCE(json_agg(DISTINCT cm.*) FILTER (WHERE cm.id IS NOT NULL), '[]') as conversation_history,  
--        COALESCE(json_agg(DISTINCT m.*) FILTER (WHERE m.id IS NOT NULL), '[]') as mockups
-- FROM projects p
-- LEFT JOIN conversation_messages cm ON cm.session_id = p.session_id
-- LEFT JOIN mockups m ON m.session_id = p.session_id  
-- WHERE p.session_id = 'your-session-id'
-- GROUP BY p.session_id;

-- ============================================================================
-- Schema Design Rationale
-- ============================================================================
--
-- This schema balances normalization with the orchestrator's atomic state update pattern:
--
-- 1. PROJECTS TABLE (core + 1:1 JSONB columns)
--    - Core metadata as regular columns for efficient indexing and querying
--    - Requirements, architecture, roadmap, export_artifacts as JSONB:
--      * Variable schema (especially roadmap with nested phases/milestones/tasks)
--      * StateManager loads entire fragments atomically
--      * JSONB allows dotted-path updates (e.g., "requirements.progress")
--    - decisions/assumptions as TEXT[] for simple array operations
--
-- 2. CONVERSATION_MESSAGES TABLE (1:N normalized)
--    - High-volume, frequently appended
--    - Queried independently for pagination and chat history
--    - Orchestrator bypasses StateManager for conversation updates (direct write)
--
-- 3. MOCKUPS TABLE (1:N normalized)
--    - Each screen is a queryable entity
--    - mockup_agent uses identity-based merge (by screen_id)
--    - wireframe_spec and excalidraw_scene as JSONB (variable component structure)
--    - Enables queries like "all screens using template X" or "screens with login form"
--
-- StateManager Adapter Strategy:
--    - get(session_id): Single JOIN to reconstruct ProjectState
--    - save(session_id, state_dict):
--      * UPDATE projects SET requirements = $1, architecture = $2, ...
--      * UPSERT conversation_messages (identity: order within session)
--      * UPSERT mockups (identity: screen_id)
--    - Delta updates map to specific column updates or row inserts
--
-- Why NOT fully normalized roadmap (separate tables for phases/milestones/tasks)?
--    - Roadmap has complex nested dependencies (tasks depend on other tasks)
--    - execution_planner generates the entire roadmap atomically
--    - Rarely queried piecemeal (consumed as whole by exporter)
--    - JSONB keeps it simple; GIN index supports deep queries if needed
--
-- ============================================================================

