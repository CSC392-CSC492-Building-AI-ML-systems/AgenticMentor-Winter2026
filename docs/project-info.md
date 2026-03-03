# Agentic Project Mentor - Project Overview

## Project Identity
**Name:** Agentic Project Mentor  
**Type:** Multi-Agent System (MAS) for automated project planning  
**Purpose:** Transform user project ideas into comprehensive, architect-level implementation plans through conversational AI

## Core Problem Statement
Users struggle to translate vague project ideas into actionable technical plans. This system bridges the gap between concept and execution by systematically gathering requirements, designing architecture, creating mockups, and generating implementation roadmaps.

## System Architecture

### High-Level Design Pattern
- **Orchestration Model:** Master-Agent hierarchical pattern
- **State Management:** Centralized shared state with atomic updates
- **Quality Assurance:** Inline review protocol embedded in each agent's execution cycle
- **Optimization Strategy:** Context-aware token management with fragment extraction

### Core Components

#### 1. Master Orchestrator
- **Responsibility:** Route user requests to appropriate specialist agents
- **Key Functions:**
  - Intent classification from user prompts
  - Dynamic agent selection and sequencing
  - Execution plan generation (sequential or parallel)
  - Response synthesis from multi-agent outputs
- **Decision Logic:** Analyzes user input + current project phase → determines which agents to invoke with which tools

#### 2. Specialist Agent Suite
Five domain-specific agents, each with focused responsibilities:

- **Requirements Collector:** Extracts functional/non-functional requirements, identifies gaps, generates clarifying questions
- **Project Architect:** Designs tech stacks, system architecture, data schemas, API structures
- **Mockup Agent:** Creates UI/UX wireframes, user flow diagrams, interaction specifications
- **Execution Planner:** Generates roadmaps, milestones, sprint breakdowns, critical path analysis
- **Exporter:** Compiles final deliverables into Markdown, PDF, or Canvas formats

#### 3. Shared State (Project Brain)
- **Structure:** Single Pydantic model containing all project dimensions
- **Layers:**
  - Requirements Layer: functional, non-functional, constraints, user stories
  - Architecture Layer: tech stack, diagrams, data schemas, API design
  - Design Layer: mockups, wireframes, user flows
  - Execution Layer: roadmap, milestones, sprints
- **Access Pattern:** Agents read relevant fragments, write deltas back atomically
- **Persistence:** Database-backed with in-memory caching for active sessions

#### 4. Review Protocol (Quality Gatekeeper)
- **Integration:** Embedded within each agent's execution cycle
- **Validation Dimensions:**
  - Feasibility: Technical validity, real technologies, resource consistency
  - Clarity: Unambiguous outputs, well-structured data
  - Completeness: All required fields populated
  - Consistency: Cross-validates against existing state
- **Self-Correction Loop:** Failed validations trigger recursive refinement (max 3 attempts)

#### 5. Tool Library
Shared utilities available to agents:
- `generate_mermaid`: Creates architecture/ER/flow/Gantt diagrams
- `query_vector_store`: RAG-based tech stack knowledge retrieval
- `ui_wireframe`: ASCII/SVG wireframe generation
- `markdown_formatter`: Document structure optimization
- `pdf_exporter`: Multi-format export compilation
- `validation_tools`: Schema validators and consistency checkers

## Information Flow
```
User Input 
    ↓
Master Orchestrator
    ↓ (analyzes intent + project phase)
Intent Classifier
    ↓ (determines agent(s) + tools)
Execution Planner
    ↓
┌─────────────────────────────────┐
│  Parallel/Sequential Agent Exec │
│  - Extract state fragments      │
│  - Execute with tools           │
│  - Apply review protocol        │
│  - Generate output delta        │
└─────────────────────────────────┘
    ↓
State Manager (atomic update)
    ↓
Shared State (single source of truth)
    ↓
Response Synthesizer
    ↓
User Response
```

## Key Technical Decisions

### Token Optimization
- **Problem:** Full state context exceeds token limits for complex projects
- **Solution:** Context Extractor provides agents only relevant state fragments based on their role
- **Impact:** 50-70% reduction in token usage per agent invocation

### Review Protocol vs. Separate Reviewer Agent
- **Decision:** Inline validation within each agent
- **Rationale:** 
  - Eliminates extra orchestration overhead
  - Enables immediate self-correction
  - Reduces total system latency
  - Each agent knows its own quality criteria best

### Centralized vs. Distributed State
- **Decision:** Single shared state model
- **Rationale:**
  - Prevents state desynchronization across agents
  - Simplifies conflict resolution
  - Enables transactional updates
  - Provides clear audit trail

### Synchronous vs. Asynchronous Agent Execution
- **Decision:** Both, determined by orchestrator
- **Examples:**
  - Sequential: Requirements → Architecture → Roadmap (dependencies)
  - Parallel: Architecture + Mockup (independent outputs)

## User Interaction Model

### Conversation Flow
1. **Discovery Phase:** Requirements Collector asks clarifying questions, fills gaps
2. **Design Phase:** Architect + Mockup agents generate technical specifications
3. **Planning Phase:** Execution Planner creates implementation timeline
4. **Export Phase:** Exporter compiles comprehensive project plan

### State Transitions
- Project progresses through phases: `initialization → discovery → requirements_complete → architecture_complete → planning_complete → exportable`
- Phase gates ensure prerequisites are met before advancing
- Users can iterate within any phase without breaking continuity

## Technology Stack (Recommended)

### Core Framework
- **Orchestration:** LangGraph or custom state machine
- **LLM Client:** LangChain adapters in `src/adapters/llm_clients.py` (Gemini, Claude, DeepSeek, OpenAI)
- **State Models:** Pydantic (validation + serialization)

### LLM Initialization Pattern
**Problem:** Agents need LLM clients, but mixing client initialization with orchestration logic creates tight coupling and makes testing difficult.

**Solution:** Centralize LLM client creation in `src/config/` and inject clients into agents via the orchestrator.

```
src/
├── config/
│   ├── settings.py        # Env-based settings (Pydantic Settings)
│   └── llm_config.py      # LLM client factory/registry
├── orchestrator/
│   └── master_agent.py    # Imports from config, injects into agents
└── adapters/
    └── llm_clients.py     # Client wrappers (already exists)
```

**Flow:**
1. `llm_config.py` → Reads env vars, creates configured clients
2. `master_agent.py` → Imports `get_llm_client()` from config
3. Agent instantiation → Orchestrator passes `llm_client` to each agent's `__init__`

### Persistence
- **Development:** SQLite with JSON columns
- **Production:** PostgreSQL with JSONB for flexible schema evolution

### Tools & Libraries
- **Diagrams:** Mermaid.js (text-based, version-controllable)
- **Vector Store:** Chroma or Pinecone (tech stack knowledge base)
- **Export:** ReportLab (PDF), python-markdown (MD processing)

### Infrastructure
- **API Framework:** FastAPI (async support)
- **Caching:** Redis (session state caching)
- **Logging:** Structured logging with correlation IDs per session

## Success Metrics

### System Performance
- **Latency:** < 10s per agent invocation (p95)
- **Token Efficiency:** < 5,000 tokens per agent call (average)
- **Review Pass Rate:** > 80% first-attempt validation

### Output Quality
- **Plan Completeness:** All required sections populated (100%)
- **Technical Feasibility:** No undefined/invalid technologies
- **User Satisfaction:** Measured via feedback on exported plans

## Development Priorities

### MVP Scope (Weeks 1-4)
1. Orchestrator with intent classification
2. Requirements Collector + Project Architect agents
3. Shared state management (SQLite)
4. Basic Mermaid diagram generation
5. Markdown export

### Post-MVP (Weeks 5-8)
1. Mockup Agent + Execution Planner
2. PDF export with styling
3. Token optimization with context extractor
4. Enhanced review protocol with metrics
5. User authentication and project persistence

## Critical Implementation Notes

### State Update Pattern
```python
# Agents NEVER mutate state directly
# They return deltas that StateManager applies atomically
agent_output = {
    "state_delta": {
        "requirements.functional": ["New requirement"],
        "architecture.tech_stack.database": "PostgreSQL"
    }
}
```

### Agent Tool Access
```python
# Tools are passed to agents by orchestrator based on execution plan
# Agents don't have global tool access (security + clarity)
execution_plan.add_task(
    agent="project_architect",
    tools=["generate_mermaid", "query_vector_store"]
)
```

### Review Protocol Integration
```python
# Every agent inherits from BaseAgent with built-in review cycle
# Quality criteria are agent-specific
class ProjectArchitect(BaseAgent):
    def _get_quality_criteria(self):
        return {
            "feasibility": 0.5,  # Most critical for architecture
            "clarity": 0.3,
            "completeness": 0.2
        }
```

## Known Constraints & Considerations

### LLM Limitations
- **Hallucination Risk:** Mitigated by review protocol + vector store grounding
- **Context Limits:** Handled by fragment extraction
- **Consistency:** Enforced through shared state validation

### Scalability Bottlenecks
- **Sequential Dependencies:** Some agent chains cannot be parallelized
- **State Size Growth:** Large projects may require state pruning/summarization
- **Token Costs:** Complex projects require budget management

### Error Handling
- **Agent Failures:** Orchestrator implements fallback strategies (degraded mode)
- **Review Failures:** After max attempts, flag output for human review
- **State Conflicts:** Last-write-wins with conflict logging for later analysis

---

**This document serves as the canonical reference for the Agentic Project Mentor system architecture. All implementation decisions should align with these core principles and patterns.**

