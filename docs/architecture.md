# AgenticMentor Architecture

## 1. Overview

The system has transitioned from a **stateless In-Memory model** to a fully **persistent, multi-agent architecture**. The backend is now powered by **Supabase (Postgres)** for long-term storage and a custom **LRU caching layer** for high-performance session management.

---

## 2. State & Persistence Layer

### Supabase (Postgres)

We use **Supabase** as our primary **source of truth** to ensure project progress survives server restarts.

- **JSONB Storage**  
  Complex agent outputs, such as **Implementation Roadmaps** and **Wireframe Specs**, are stored as native `JSONB` objects. This maintains deep data integrity without requiring complex flattening or schema migrations.

- **Relational Mapping**  
  Mockups are managed in a relational **`mockups` table** linked by `session_id`, allowing efficient retrieval and versioning of UI assets.

### StateManager & Caching

To optimize performance and minimize database round-trips, we implemented a **Session Cache**.

- **Strategy:** LRU (Least Recently Used) with a **100-session limit** to manage memory efficiently.
- **TTL:** **1-hour time-to-live (TTL)** for inactive sessions to ensure stale data is periodically cleared.
- **Consistency:** A **write-through logic** ensures that every `update()` call persists to the database successfully **before updating the local cache**, guaranteeing data safety.

---

## 3. Orchestration Flow

The **MasterOrchestrator** handles the logic for agent transitions.

---

## 4. Export System

The **Exporter Agent** compiles the project state into final documentation.

- **Formats:** Generates **Markdown** and **HTML** artifacts by default.