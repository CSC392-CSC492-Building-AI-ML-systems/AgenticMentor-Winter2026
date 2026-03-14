# Supabase Integration - Phase 2 Complete ✅

## What's Been Implemented

**Phase 2: Adapter Implementation** - All components ready for production use!

### 1. SupabaseAdapter Class
**Location**: [src/orchestrator/supabase_adapter.py](src/orchestrator/supabase_adapter.py)

Implements all 7 methods from `InMemoryPersistenceAdapter` interface:
- ✅ `get(session_id)` - Loads complete state with JOIN across 3 tables
- ✅ `save(session_id, state_dict)` - Atomic save to projects + messages + mockups
- ✅ `delete(session_id)` - Cascading delete
- ✅ `list_sessions()` - Get all session IDs
- ✅ `get_last_messages(session_id, n)` - Query recent messages
- ✅ `load_state(session_id)` - Returns ProjectState model
- ✅ `save_project_state(session_id, state)` - Convenience wrapper

**Key Features**:
- JSONB serialization for requirements, architecture, roadmap, export_artifacts
- Identity-based mockup merge by `screen_id` (upsert operation)
- Conversation message sync (delete + bulk insert)
- Graceful error handling with console logging

### 2. Persistence Factory
**Location**: [src/state/persistence.py](src/state/persistence.py)

Updated `get_default_adapter()` to:
- ✅ Auto-detect Supabase credentials from environment
- ✅ Return `SupabaseAdapter` when `SUPABASE_URL` and `SUPABASE_KEY` are set
- ✅ Fallback to `InMemoryPersistenceAdapter` if not configured
- ✅ Graceful error handling with console warnings

### 3. Test Suite
**Location**: [test_supabase_adapter.py](test_supabase_adapter.py)

6 comprehensive tests:
1. Connection verification
2. Save and load project state
3. Update operations (delta pattern)
4. Mockups identity-based merge
5. List all sessions
6. Delete and cleanup

---

## Getting Started

### Step 1: Configure Environment (if not done yet)

Ensure your `.env` file has Supabase credentials:

```bash
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-supabase-anon-key-here
```

**How to find these**:
1. Go to your Supabase project dashboard
2. Click Settings (gear icon) → API
3. Copy **Project URL** → `SUPABASE_URL`
4. Copy **anon/public key** → `SUPABASE_KEY`

### Step 2: Run the Migration (if not done yet)

In Supabase Dashboard:
1. Go to **SQL Editor** (left sidebar)
2. Click **New query**
3. Copy contents of [migrations/001_initial_schema.sql](migrations/001_initial_schema.sql)
4. Paste and click **Run**

You should see:
```
Success: No rows returned
```

Verify schema:
```sql
SELECT * FROM projects LIMIT 1;
SELECT * FROM conversation_messages LIMIT 1;
SELECT * FROM mockups LIMIT 1;
```

### Step 3: Test the Adapter

Run the test suite to verify everything works:

```bash
python test_supabase_adapter.py
```

Expected output:
```
======================================================================
SupabaseAdapter Test Suite
======================================================================

======================================================================
TEST 1: Supabase Connection
======================================================================
✅ SupabaseAdapter initialized successfully
   URL: https://your-project-ref.supabase.co
   Key: eyJhbGciOiJIUzI1NiI...

======================================================================
TEST 2: Save and Load Project State
======================================================================
📝 Saving test session: test-session-1709876543
✅ Save successful
📖 Loading test session: test-session-1709876543
✅ Load successful
   Project name: Test Project
   Current phase: initialization
   Requirements progress: 0.3
   Tech stack: {'frontend': 'React', 'backend': 'FastAPI', 'database': 'PostgreSQL'}
   Conversation messages: 2
   Decisions: 1
✅ Data integrity verified

... more tests ...

======================================================================
✅ ALL TESTS PASSED
======================================================================

SupabaseAdapter is ready to use!
```

### Step 4: Verify in Supabase Dashboard

After running tests, check your data:

1. Go to **Table Editor** (left sidebar)
2. Click on **projects** table - you should see test data
3. Click on **conversation_messages** - messages from the test
4. Click on **mockups** - mockup screens from the test

The test cleans up after itself (deletes test session), but you can comment out the cleanup step to inspect the data.

---

## How It Works

### Automatic Activation

The adapter is **automatically used** when Supabase credentials are configured. No code changes needed!

```python
# In your existing code, this just works:
from src.state.state_manager import StateManager
from src.state.persistence import get_default_adapter

# This will now use SupabaseAdapter if SUPABASE_URL and SUPABASE_KEY are set
state_manager = StateManager(get_default_adapter())
```

### Console Output

When the app starts, you'll see:
```
[persistence] Using SupabaseAdapter (Postgres backend)
```

Or if credentials are missing:
```
[persistence] Using InMemoryPersistenceAdapter (no database persistence)
```

### Data Flow

1. **Load**: `StateManager.load(session_id)`
   - Calls `SupabaseAdapter.get(session_id)`
   - JOINs projects + conversation_messages + mockups
   - Reconstructs `ProjectState` dict

2. **Update**: `StateManager.update(session_id, delta)`
   - Merges delta into cached state (existing logic)
   - Calls `SupabaseAdapter.save(session_id, merged_state)`
   - UPSERTs to all 3 tables atomically

3. **Conversation**: Orchestrator appends messages
   - Updates `ProjectState.conversation_history`
   - Direct write: `db.save(session_id, state.model_dump())`
   - Syncs to `conversation_messages` table

---

## Testing with Real Agents

### Test 1: Requirements Collector

The first agent to test (simplest data structure):

```bash
# If you have a script for requirements collection:
python run_requirements_collector.py
```

**What to verify**:
1. Talk to the agent through a few conversation turns
2. Check Supabase Dashboard > Table Editor > `projects`
   - Should see one row with your session_id
   - `requirements` JSONB should have your data
   - `decisions` and `assumptions` arrays populated
3. Check `conversation_messages` table
   - Should see all user/assistant messages
4. After closing and restarting, state should persist

### Test 2: Full Orchestrator Flow

```bash
# Run the full orchestrator
python main.py
```

**Flow to test**:
1. Describe a project (requirements_collector runs)
2. Ask for architecture (project_architect runs)
3. Ask for roadmap (execution_planner runs)
4. Ask for mockups (mockup_agent runs)
5. Ask to export (exporter runs)

**Verify in Supabase**:
- `projects` table has complete data in all JSONB columns
- `conversation_messages` has full conversation
- `mockups` table has all wireframe screens
- Can restart and continue the conversation (state persists)

---

## Troubleshooting

### Issue: "supabase package not installed"

```bash
pip install supabase
```

### Issue: "SUPABASE_URL and SUPABASE_KEY must be set"

Check your `.env` file:
```bash
cat .env | grep SUPABASE
```

Should show:
```
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiI...
```

### Issue: "No such table: projects"

Run the migration SQL in Supabase Dashboard:
1. SQL Editor → New query
2. Paste [migrations/001_initial_schema.sql](migrations/001_initial_schema.sql)
3. Run

### Issue: Test passes but no data in Supabase

The test cleans up after itself. To keep test data, edit `test_supabase_adapter.py`:

```python
# Comment out the cleanup test
# await test_cleanup(adapter, session_id)
```

### Issue: Error saving mockups

Check that mockups have required fields:
- `screen_id` (unique per session)
- `screen_name`
- `template_used`
- `wireframe_spec` (can be empty dict: `{}`)

---

## Architecture Notes

### Why 3 Tables?

**projects** (1:1 JSONB columns)
- Core metadata + agent outputs
- Efficient for atomic state loads
- JSONB for variable schemas

**conversation_messages** (1:N)
- High-volume, frequently queried
- Supports pagination
- Easy to add search later

**mockups** (1:N)
- Each screen is queryable
- Identity-based merge by `screen_id`
- Can add filters like "all auth templates"

### StateManager Integration

The adapter is **drop-in compatible** with existing code:
- Same 7 methods as `InMemoryPersistenceAdapter`
- StateManager's delta merge logic unchanged
- Cache behavior unchanged
- No agent modifications needed

### Performance Considerations

**Current implementation** (optimized for correctness):
- conversation_messages: delete-all + bulk-insert on save
- mockups: individual upserts per screen

**Future optimization** (if needed):
- Incremental message append (track last message ID)
- Batch mockup upserts
- Connection pooling (Supabase handles this)

---

## What's Next?

✅ **Phase 1 & 2 Complete** - Infrastructure ready!

**Phase 3: Testing & Validation** (Next Steps)
1. Test with requirements_collector agent
2. Test with project_architect agent (JSONB for tech_stack)
3. Run full orchestrator workflow
4. Verify state persistence across restarts
5. Test multi-session scenarios

**Phase 4: Production Readiness** (Optional)
1. Add row-level security (RLS) policies
2. Add indexes for common queries
3. Set up automated backups
4. Add monitoring/alerting
5. Load testing

---

## Files Created/Modified

**New Files**:
- `src/orchestrator/supabase_adapter.py` - Main adapter implementation
- `test_supabase_adapter.py` - Test suite

**Modified Files**:
- `src/state/persistence.py` - Auto-detect and wire in SupabaseAdapter
- `requirements.txt` - Added supabase package
- `.env.example` - Added Supabase credentials

**Migration Files**:
- `migrations/001_initial_schema.sql` - Database schema
- `migrations/SCHEMA_VERIFICATION.md` - Agent output mapping

---

## Questions?

The implementation follows the orchestrator flow documented in:
- [docs/orchestrator-agent.md](docs/orchestrator-agent.md)
- [docs/orchestrator_plan.md](docs/orchestrator_plan.md)

All agent outputs are verified and mapped to the schema in:
- [migrations/SCHEMA_VERIFICATION.md](migrations/SCHEMA_VERIFICATION.md)

Ready to test! 🚀
