# Agent Specification: Project Architect (`project_architect.py`)

**Version:** 1.0
**Role:** System Architect & Technical Lead
**Parent Class:** `src.agents.base_agent.BaseAgent`
**Primary Tool:** `src.tools.diagram_generator.DiagramGenerator`

---

## 1. Overview
The `ProjectArchitectAgent` is responsible for translating high-level user requirements (gathered by the `RequirementsCollector`) into a concrete technical specification. It effectively bridges the gap between the "What" (requirements) and the "How" (execution).

### Core Responsibilities
1.  **Tech Stack Selection:** Recommend languages, frameworks, and databases based on constraints.
2.  **System Design:** Define the high-level architecture (Monolith vs. Microservices, etc.).
3.  **Visual Documentation:** Generate Mermaid.js diagrams (C4 Model, Entity-Relationship).
4.  **State Updates:** Update the global `ProjectState` with architectural decisions.

---

## 2. Dependencies & Imports

The agent must interact with the following internal modules. Ensure these imports are present and utilized.

```python
from typing import Dict, Any, List, Optional

# Inheritance
from src.agents.base_agent import BaseAgent

# State Management
from src.state.project_state import ProjectState, ArchitectureDefinition

# Tools
from src.tools.diagram_generator import DiagramGenerator

# Protocols
from src.protocols.review_protocol import ReviewResult

## 3. Class Structure

The `ProjectArchitectAgent` must implement the abstract methods defined in `BaseAgent`.

### `class ProjectArchitectAgent(BaseAgent)`

#### Attributes
| Name | Type | Description |
| :--- | :--- | :--- |
| `diagram_gen` | `DiagramGenerator` | Instance of the diagram tool for generating Mermaid code. |
| `name` | `str` | "Project Architect" |
| `description` | `str` | "Defines technical stack and system diagrams." |

#### Methods

1.  **`__init__(self, state_manager: StateManager)`**
    * Initialize the parent `BaseAgent`.
    * Instantiate `self.diagram_gen = DiagramGenerator()`.

2.  **`async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]`**
    * **Input:** A dictionary containing `"requirements"` (or `ProjectState` with requirements populated).
    * **Logic:**
        1.  Analyze requirements for complexity and constraints.
        2.  Call internal LLM (via `self.llm_client` from Base) to draft a Tech Stack.
        3.  Call `self.diagram_gen` to generate a System Context Diagram (C4 Level 1).
        4.  Call `self.diagram_gen` to generate a Database Schema (ER Diagram).
        5.  Compile results into an `ArchitectureDefinition` object.
    * **Output:** A dictionary containing the architecture summary and diagram code.

3.  **`async def review(self, artifact: Any) -> ReviewResult`**
    * **Purpose:** Self-correction.
    * **Logic:** Validate that the generated diagrams are syntactically correct Mermaid code and that the tech stack covers all functional requirements.

---

## 4. Implementation Details (Step-by-Step)

### Step 4.1: Tech Stack Generation
The agent should construct a prompt to select the best technology.

* **System Prompt:** "You are a Senior Software Architect. Analyze the following requirements and output a JSON object defining the Frontend, Backend, Database, and DevOps stack. Justify each choice."
* **Constraint:** Must adhere to any constraints in `ProjectState` (e.g., "Must use Python").

### Step 4.1.1: LLM Integration (LangChain Adapters)
Use the shared adapters in `src/adapters/llm_clients.py` and inject them into the agent via `llm_client`.

```python
from src.adapters.llm_clients import GeminiClient, ClaudeClient, DeepSeekClient, OpenAIClient
from src.agents.project_architect import ProjectArchitectAgent

architect = ProjectArchitectAgent(state_manager=state_manager, llm_client=GeminiClient())
```

### Step 4.2: Diagram Generation Strategy
Do **not** generate the diagrams directly in the `process` method's main LLM call. Instead, delegate to the `DiagramGenerator` tool methods.

1.  **Identify Diagram Needs:** Based on the app type (e.g., if it's a data-heavy app, an ERD is mandatory. If it's a microservice app, a Container Diagram is mandatory).
2.  **Tool Invocation:**
    ```python
    # Example Logic
    diagram_code = await self.diagram_gen.generate_diagram(
        type="sequence",
        context=requirements_summary,
        participants=["User", "Frontend", "API", "DB"]
    )
    ```

### Step 4.3: State Updates
The agent must structure its output to match the `ProjectState` Pydantic models.

```python
# Expected Update Payload
{
    "architecture": {
        "frontend_framework": "React",
        "backend_framework": "FastAPI",
        "database": "PostgreSQL",
        "diagrams": {
            "c4_context": "graph TD...",
            "erd": "erDiagram..."
        }
    }
}

## 5. Error Handling & Recovery

* **Mermaid Syntax Errors:** If the `review()` method detects broken Mermaid syntax, the agent must trigger a retry loop. It should re-prompt the LLM with the message: "The previous diagram code failed validation. Fix the syntax errors: [Error Log]."
* **Missing Requirements:** If `input_data` lacks clear requirements, raise a `ValueError` or request clarification from the `RequirementsCollector`.
* **Token Limit Safeguards:** If the architectural context is too large, the agent should summarize the requirements using `utils.token_optimizer` before generating diagrams.

## 6. Example Interaction Flow

1.  **Orchestrator** calls `ProjectArchitectAgent.process(state)`.
2.  **Architect** reads `state.requirements`.
3.  **Architect** decides on the tech stack (e.g., `Next.js + Supabase`) based on the requirements.
4.  **Architect** uses the `DiagramGenerator` tool to draw the system flow (C4) and data structure (ERD).
5.  **Architect** compiles the stack decisions and diagram code into the `ArchitectureDefinition`.
6.  **Architect** returns the updated state to the Orchestrator.
