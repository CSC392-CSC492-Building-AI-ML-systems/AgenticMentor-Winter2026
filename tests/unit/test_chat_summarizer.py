"""Unit tests for src.orchestrator.chat_summarizer."""

import pytest

from src.orchestrator.chat_summarizer import (
    estimate_tokens,
    get_effective_history,
    maybe_summarize,
)
from src.state.project_state import ProjectState


# ---------------------------------------------------------------------------
# estimate_tokens
# ---------------------------------------------------------------------------

def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_estimate_tokens_short():
    text = "Hello world"
    result = estimate_tokens(text)
    assert result == len(text) // 4


def test_estimate_tokens_long():
    text = "a" * 4000
    assert estimate_tokens(text) == 1000


# ---------------------------------------------------------------------------
# get_effective_history — no summary
# ---------------------------------------------------------------------------

def test_get_effective_history_no_summary():
    """When no summary exists, effective history equals the raw history."""
    state = ProjectState(
        session_id="t1",
        conversation_history=[
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ],
    )
    eff = get_effective_history(state)
    assert eff == state.conversation_history


def test_get_effective_history_with_summary():
    """When a summary exists, effective history starts with a system summary message followed by the tail."""
    state = ProjectState(
        session_id="t2",
        conversation_history=[
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "resp1"},
            {"role": "user", "content": "msg2"},
            {"role": "assistant", "content": "resp2"},
        ],
        conversation_summary="We discussed msg1.",
        conversation_summary_up_to_index=2,
    )
    eff = get_effective_history(state)
    assert len(eff) == 3  # 1 system + 2 tail
    assert eff[0]["role"] == "system"
    assert "We discussed msg1." in eff[0]["content"]
    assert eff[1] == {"role": "user", "content": "msg2"}
    assert eff[2] == {"role": "assistant", "content": "resp2"}


def test_get_effective_history_empty_state():
    """Effective history of a fresh state is an empty list."""
    state = ProjectState(session_id="t3")
    assert get_effective_history(state) == []


# ---------------------------------------------------------------------------
# maybe_summarize — below threshold
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_summarize_below_threshold():
    """Short history returns None (no-op)."""
    history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    result = await maybe_summarize(history, "", 0, None, token_threshold=4000)
    assert result is None


@pytest.mark.asyncio
async def test_no_summarize_empty_history():
    result = await maybe_summarize([], "", 0, None, token_threshold=100)
    assert result is None


# ---------------------------------------------------------------------------
# maybe_summarize — above threshold, no LLM (fallback)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_summarize_above_threshold_fallback():
    """When history exceeds the threshold and no LLM, falls back to truncation."""
    # Build a history that is definitely above 100 tokens (400 chars).
    history = []
    for i in range(60):
        history.append({"role": "user", "content": f"User message number {i} " + "x" * 40})
        history.append({"role": "assistant", "content": f"Assistant reply number {i} " + "y" * 40})

    result = await maybe_summarize(history, "", 0, None, token_threshold=100)
    assert result is not None
    new_summary, new_cursor = result
    assert isinstance(new_summary, str)
    assert len(new_summary) > 0
    # Cursor should advance, leaving only the last 2 messages unsummarized.
    assert new_cursor == len(history) - 2


# ---------------------------------------------------------------------------
# maybe_summarize — above threshold, with mock LLM
# ---------------------------------------------------------------------------

class _MockLLM:
    """Minimal LLM mock that returns a fixed summary."""

    def __init__(self, reply: str = "Summary of conversation."):
        self._reply = reply

    async def ainvoke(self, prompt: str) -> str:
        return self._reply


@pytest.mark.asyncio
async def test_summarize_above_threshold_with_llm():
    """When LLM is available, uses it to produce the summary."""
    history = []
    for i in range(60):
        history.append({"role": "user", "content": f"Message {i} " + "z" * 40})
        history.append({"role": "assistant", "content": f"Reply {i} " + "w" * 40})

    llm = _MockLLM("Condensed summary from LLM.")
    result = await maybe_summarize(history, "", 0, llm, token_threshold=100)
    assert result is not None
    new_summary, new_cursor = result
    assert new_summary == "Condensed summary from LLM."
    assert new_cursor == len(history) - 2


# ---------------------------------------------------------------------------
# Incremental summarization (two rounds)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_incremental_summarization():
    """Simulates two summarization rounds: existing summary + new messages."""
    # Round 1: build initial history above threshold.
    history = []
    for i in range(40):
        history.append({"role": "user", "content": f"Round1 msg {i} " + "a" * 50})
        history.append({"role": "assistant", "content": f"Round1 reply {i} " + "b" * 50})

    llm = _MockLLM("Round 1 summary.")
    r1 = await maybe_summarize(history, "", 0, llm, token_threshold=100)
    assert r1 is not None
    summary1, cursor1 = r1

    # Round 2: add more messages and summarize again.
    for i in range(40):
        history.append({"role": "user", "content": f"Round2 msg {i} " + "c" * 50})
        history.append({"role": "assistant", "content": f"Round2 reply {i} " + "d" * 50})

    llm2 = _MockLLM("Round 2 summary (merged with round 1).")
    r2 = await maybe_summarize(history, summary1, cursor1, llm2, token_threshold=100)
    assert r2 is not None
    summary2, cursor2 = r2
    assert cursor2 > cursor1
    assert summary2 == "Round 2 summary (merged with round 1)."
    # After round 2, only the last 2 messages should be unsummarized.
    assert cursor2 == len(history) - 2


# ---------------------------------------------------------------------------
# LLM edge cases
# ---------------------------------------------------------------------------

class _ExplodingLLM:
    """LLM mock that always raises an exception."""

    async def ainvoke(self, prompt: str) -> str:
        raise RuntimeError("LLM service unavailable")


class _EmptyLLM:
    """LLM mock that returns an empty string."""

    async def ainvoke(self, prompt: str) -> str:
        return ""


class _CapturingLLM:
    """LLM mock that records the prompt it received."""

    def __init__(self):
        self.last_prompt: str | None = None

    async def ainvoke(self, prompt: str) -> str:
        self.last_prompt = prompt
        return "Captured summary."


def _long_history(n: int = 60) -> list[dict]:
    """Generate a history list guaranteed to exceed a low token threshold."""
    history = []
    for i in range(n):
        history.append({"role": "user", "content": f"User msg {i} " + "x" * 40})
        history.append({"role": "assistant", "content": f"Asst reply {i} " + "y" * 40})
    return history


@pytest.mark.asyncio
async def test_summarize_llm_exception_falls_back():
    """When the LLM raises, maybe_summarize falls back to truncation instead of propagating."""
    history = _long_history()
    result = await maybe_summarize(history, "", 0, _ExplodingLLM(), token_threshold=100)
    assert result is not None
    new_summary, new_cursor = result
    # Fallback produces a non-empty truncation-based summary.
    assert isinstance(new_summary, str)
    assert len(new_summary) > 0
    assert new_cursor == len(history) - 2


@pytest.mark.asyncio
async def test_summarize_llm_empty_response_falls_back():
    """When the LLM returns an empty string, maybe_summarize falls back to truncation."""
    history = _long_history()
    result = await maybe_summarize(history, "", 0, _EmptyLLM(), token_threshold=100)
    assert result is not None
    new_summary, new_cursor = result
    assert isinstance(new_summary, str)
    assert len(new_summary) > 0
    assert new_cursor == len(history) - 2


@pytest.mark.asyncio
async def test_summarize_prompt_contains_existing_summary_and_messages():
    """The prompt sent to the LLM includes both the existing summary and the new messages."""
    history = _long_history(n=30)
    existing_summary = "Previously the user described a task management app."
    llm = _CapturingLLM()

    result = await maybe_summarize(history, existing_summary, 0, llm, token_threshold=100)
    assert result is not None
    assert result[0] == "Captured summary."

    # Verify the prompt contained the existing summary text.
    assert existing_summary in llm.last_prompt

    # Verify the prompt contained at least some of the message content.
    assert "User msg 0" in llm.last_prompt


# ---------------------------------------------------------------------------
# Realistic conversation — prints summarization output
# ---------------------------------------------------------------------------

# ~2 000 characters of realistic project-planning conversation.
_REALISTIC_CHAT: list[dict] = [
    {"role": "user", "content": "Hey, I want to build a personal finance tracker app."},
    {"role": "assistant", "content": "Great idea! What platform are you targeting — web, mobile, or both?"},
    {"role": "user", "content": "Let's go with a web app for now. I might add a mobile version later."},
    {"role": "assistant", "content": "Got it — web-first. Who will use the app? Just you, or other people too?"},
    {"role": "user", "content": "Mainly for myself, but I'd like to open it up to friends eventually."},
    {"role": "assistant", "content": "Understood. So we should plan for user accounts and basic auth from the start. What core features do you have in mind?"},
    {"role": "user", "content": "I want to track expenses, categorize them, set monthly budgets, and see charts showing my spending over time."},
    {"role": "assistant", "content": "Nice. That gives us four core modules: expense logging, categories, budgets, and analytics dashboards. Do you have any tech preferences?"},
    {"role": "user", "content": "I'd prefer React on the frontend and Python on the backend. Maybe FastAPI."},
    {"role": "assistant", "content": "Solid choices. For the database, would you like PostgreSQL or something lighter like SQLite to start?"},
    {"role": "user", "content": "Postgres sounds good. I want it production-ready from the start."},
    {"role": "assistant", "content": "Perfect. So the stack is React + FastAPI + PostgreSQL. Any timeline or budget constraints?"},
    {"role": "user", "content": "I'd like an MVP in about 6 weeks. No real budget — it's a side project."},
    {"role": "assistant", "content": "That's workable. I'll plan for a 6-week timeline with core features first. Should we include any non-functional requirements like dark mode or accessibility?"},
    {"role": "user", "content": "Yes, dark mode would be great. And basic accessibility — proper labels and keyboard navigation."},
    {"role": "assistant", "content": "Noted. I'll add dark mode and WCAG-level accessibility to the requirements. Anything else before I finalize?"},
    {"role": "user", "content": "I think that covers it. Let's move forward with this."},
    {"role": "assistant", "content": "Requirements captured. We have a web-based personal finance tracker using React, FastAPI, and PostgreSQL, targeting a 6-week MVP with expense tracking, budgets, analytics, dark mode, and accessibility. Say 'continue' when you're ready for architecture."},
]


@pytest.mark.asyncio
async def test_realistic_conversation_summarization(capsys):
    """Run summarization on a realistic ~2000-char conversation and print the results."""
    history = list(_REALISTIC_CHAT)

    # Show the raw character count.
    raw_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)
    char_count = len(raw_text)
    print(f"\n{'='*60}")
    print(f"ORIGINAL CONVERSATION  ({len(history)} messages, {char_count} chars)")
    print(f"{'='*60}")
    for m in history:
        print(f"  {m['role'].upper()}: {m['content']}")

    # Use a mock LLM that produces a realistic summary.
    class _RealisticSummaryLLM:
        async def ainvoke(self, prompt: str) -> str:
            return (
                "The user wants to build a personal finance tracker as a web app. "
                "Stack: React + FastAPI + PostgreSQL. Core features: expense tracking, "
                "categories, monthly budgets, analytics dashboards. Non-functional: "
                "dark mode, WCAG accessibility. Target users: personal use, eventually "
                "friends (needs auth). Timeline: 6-week MVP, side project with no budget. "
                "Requirements are complete and ready for architecture phase."
            )

    # Low threshold to force summarization on this short conversation.
    result = await maybe_summarize(history, "", 0, _RealisticSummaryLLM(), token_threshold=200)

    assert result is not None
    new_summary, new_cursor = result

    print(f"\n{'='*60}")
    print(f"SUMMARIZATION RESULT  (cursor at {new_cursor}/{len(history)})")
    print(f"{'='*60}")
    print(f"  Summary:\n    {new_summary}")
    print(f"\n  Unsummarized tail ({len(history) - new_cursor} messages):")
    for m in history[new_cursor:]:
        print(f"    {m['role'].upper()}: {m['content']}")

    # Build effective history as the orchestrator would see it.
    from src.state.project_state import ProjectState
    state = ProjectState(
        session_id="realistic-test",
        conversation_history=history,
        conversation_summary=new_summary,
        conversation_summary_up_to_index=new_cursor,
    )
    eff = get_effective_history(state)

    print(f"\n{'='*60}")
    print(f"EFFECTIVE HISTORY  ({len(eff)} entries)")
    print(f"{'='*60}")
    for m in eff:
        role_label = "SUMMARY" if m["role"] == "system" else m["role"].upper()
        print(f"  {role_label}: {m['content']}")
    print()

    # Assertions
    assert isinstance(new_summary, str)
    assert len(new_summary) > 0
    assert new_cursor == len(history) - 2
    assert eff[0]["role"] == "system"
    assert len(eff) == 3  # summary + last 2 messages


# ---------------------------------------------------------------------------
# Two-round realistic summarization (summary grows across rounds)
# ---------------------------------------------------------------------------

_ROUND1_CHAT: list[dict] = [
    {"role": "user", "content": "I want to build a personal finance tracker app."},
    {"role": "assistant", "content": "What platform — web, mobile, or both?"},
    {"role": "user", "content": "Web app for now. Maybe mobile later."},
    {"role": "assistant", "content": "Who will use the app?"},
    {"role": "user", "content": "Just me at first, then friends."},
    {"role": "assistant", "content": "Got it — user accounts needed. What core features?"},
    {"role": "user", "content": "Expense tracking, categories, monthly budgets, and spending charts."},
    {"role": "assistant", "content": "Four modules: expenses, categories, budgets, analytics. Tech preferences?"},
    {"role": "user", "content": "React frontend, FastAPI backend, PostgreSQL."},
    {"role": "assistant", "content": "Timeline or budget constraints?"},
    {"role": "user", "content": "6 week MVP, no budget — side project."},
    {"role": "assistant", "content": "Any non-functional requirements?"},
    {"role": "user", "content": "Dark mode and basic accessibility."},
    {"role": "assistant", "content": "Requirements complete. Say continue for architecture."},
]

_ROUND2_CHAT: list[dict] = [
    {"role": "user", "content": "continue"},
    {"role": "assistant", "content": "Starting architecture design. For the frontend, I recommend Next.js with React for SSR and routing. Sound good?"},
    {"role": "user", "content": "Yes, Next.js works. What about the API layer?"},
    {"role": "assistant", "content": "FastAPI with Pydantic models for request validation. We will use SQLAlchemy as the ORM with Alembic for migrations."},
    {"role": "user", "content": "Sounds solid. What about authentication?"},
    {"role": "assistant", "content": "JWT-based auth with refresh tokens. We can use python-jose for token handling and passlib for password hashing."},
    {"role": "user", "content": "What about the database schema?"},
    {"role": "assistant", "content": "Core tables: users, accounts, transactions, categories, budgets. Transactions link to categories and accounts. Budgets are per-category per-month."},
    {"role": "user", "content": "Should we add recurring transactions?"},
    {"role": "assistant", "content": "Good idea. We can add a recurrence_rule column to transactions and a background job that generates entries. I will add that to the schema."},
    {"role": "user", "content": "What about deployment?"},
    {"role": "assistant", "content": "Docker Compose for local dev. For production: the API on Railway or Fly.io, the frontend on Vercel, and PostgreSQL on Supabase or Neon."},
    {"role": "user", "content": "Perfect. Architecture looks good to me."},
    {"role": "assistant", "content": "Architecture complete. Stack: Next.js, FastAPI, PostgreSQL. Auth: JWT. Deployment: Docker + Vercel + Railway. Say continue for the execution plan."},
]


@pytest.mark.asyncio
async def test_two_round_summarization_realistic(capsys):
    """Simulates a full two-round summarization with realistic chat and prints each stage."""
    history = list(_ROUND1_CHAT)

    # --- Round 1: summarize requirements phase ---
    class _Round1LLM:
        async def ainvoke(self, prompt: str) -> str:
            return (
                "The user is building a personal finance tracker web app. "
                "Stack: React + FastAPI + PostgreSQL. Features: expense tracking, "
                "categories, monthly budgets, analytics. Needs dark mode and accessibility. "
                "Target: personal use expanding to friends. Timeline: 6-week MVP, no budget. "
                "Requirements are complete."
            )

    r1 = await maybe_summarize(history, "", 0, _Round1LLM(), token_threshold=100)
    assert r1 is not None
    summary1, cursor1 = r1

    print(f"\n{'='*60}")
    print(f"ROUND 1 — Requirements phase summarized")
    print(f"{'='*60}")
    print(f"  Cursor: {cursor1}/{len(history)}")
    print(f"  Summary: {summary1}")
    print(f"  Tail ({len(history) - cursor1} msgs):")
    for m in history[cursor1:]:
        print(f"    {m['role'].upper()}: {m['content']}")

    # --- Simulate continued chat (architecture phase) ---
    history.extend(_ROUND2_CHAT)

    print(f"\n  ... {len(_ROUND2_CHAT)} new architecture messages added ...")
    print(f"  Total history now: {len(history)} messages")

    # --- Round 2: summarize architecture on top of existing summary ---
    class _Round2LLM:
        async def ainvoke(self, prompt: str) -> str:
            return (
                "The user is building a personal finance tracker web app. "
                "Stack: Next.js + FastAPI + PostgreSQL with SQLAlchemy/Alembic. "
                "Features: expense tracking, categories, monthly budgets, analytics, "
                "recurring transactions. Auth: JWT with refresh tokens. "
                "Needs dark mode and accessibility. Target: personal use expanding to friends. "
                "Timeline: 6-week MVP, no budget. Deployment: Docker Compose locally, "
                "Vercel + Railway + Supabase in production. "
                "Requirements and architecture are both complete."
            )

    r2 = await maybe_summarize(history, summary1, cursor1, _Round2LLM(), token_threshold=200)
    assert r2 is not None
    summary2, cursor2 = r2

    print(f"\n{'='*60}")
    print(f"ROUND 2 — Architecture phase merged into summary")
    print(f"{'='*60}")
    print(f"  Cursor: {cursor2}/{len(history)}")
    print(f"  Summary: {summary2}")
    print(f"  Tail ({len(history) - cursor2} msgs):")
    for m in history[cursor2:]:
        print(f"    {m['role'].upper()}: {m['content']}")

    # --- Show effective history ---
    state = ProjectState(
        session_id="two-round-test",
        conversation_history=history,
        conversation_summary=summary2,
        conversation_summary_up_to_index=cursor2,
    )
    eff = get_effective_history(state)

    print(f"\n{'='*60}")
    print(f"EFFECTIVE HISTORY  ({len(eff)} entries)")
    print(f"{'='*60}")
    for m in eff:
        lbl = "SUMMARY" if m["role"] == "system" else m["role"].upper()
        print(f"  {lbl}: {m['content']}")
    print()

    # --- Assertions ---
    assert cursor2 > cursor1
    assert cursor2 == len(history) - 2
    assert "architecture" in summary2.lower()
    assert "requirements" in summary1.lower() or "finance tracker" in summary1.lower()
    assert eff[0]["role"] == "system"
    assert len(eff) == 3  # summary + last 2 messages


# ---------------------------------------------------------------------------
# Integration test — real Gemini LLM (skipped if no API key)
# ---------------------------------------------------------------------------

import os

_has_gemini_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


@pytest.mark.asyncio
@pytest.mark.skipif(not _has_gemini_key, reason="GEMINI_API_KEY not set — skipping real LLM test")
async def test_real_llm_summarization(capsys):
    """Call the real Gemini LLM to summarize a realistic conversation and print the output."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    llm = ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview",
        temperature=0.2,
        api_key=api_key,
    )

    # Full conversation: requirements + architecture phases.
    history = list(_ROUND1_CHAT) + list(_ROUND2_CHAT)

    print(f"\n{'='*60}")
    print(f"REAL LLM TEST — {len(history)} messages, {sum(len(m['content']) for m in history)} chars")
    print(f"{'='*60}")

    result = await maybe_summarize(history, "", 0, llm, token_threshold=100)
    assert result is not None
    summary, cursor = result

    print(f"\n>> GEMINI SUMMARY (cursor {cursor}/{len(history)}):")
    print(f"   {summary}")
    print(f"\n>> UNSUMMARIZED TAIL ({len(history) - cursor} messages):")
    for m in history[cursor:]:
        print(f"   {m['role'].upper()}: {m['content']}")

    # Build effective history.
    state = ProjectState(
        session_id="real-llm-test",
        conversation_history=history,
        conversation_summary=summary,
        conversation_summary_up_to_index=cursor,
    )
    eff = get_effective_history(state)

    print(f"\n>> EFFECTIVE HISTORY ({len(eff)} entries):")
    for m in eff:
        lbl = "SUMMARY" if m["role"] == "system" else m["role"].upper()
        print(f"   {lbl}: {m['content']}")
    print()

    # Basic sanity checks on the real output.
    assert isinstance(summary, str)
    assert len(summary) > 50  # should be a substantive summary
    assert cursor == len(history) - 2
    assert eff[0]["role"] == "system"
