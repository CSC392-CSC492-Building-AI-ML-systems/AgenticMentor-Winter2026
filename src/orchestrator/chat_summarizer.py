"""Rolling chat summarization for the orchestrator.

Provides token estimation, conditional summarization, and an effective-history
helper that replaces raw conversation history with [summary] + unsummarized tail.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Cheap heuristic: ~4 characters per token (GPT/Gemini average)."""
    return max(0, len(text) // 4)


def _history_text(messages: list[dict]) -> str:
    """Concatenate message contents for token estimation."""
    return "\n".join(
        f"{(m.get('role') or 'user').upper()}: {m.get('content') or ''}"
        for m in messages
    )


# ---------------------------------------------------------------------------
# Effective history (summary + tail)
# ---------------------------------------------------------------------------

def get_effective_history(project_state: Any) -> list[dict]:
    """Return conversation history with summarized portion replaced by a single system message.

    If no summary exists yet, returns the raw history unchanged.
    """
    summary: str = getattr(project_state, "conversation_summary", "") or ""
    cursor: int = getattr(project_state, "conversation_summary_up_to_index", 0) or 0
    history: list[dict] = list(getattr(project_state, "conversation_history", None) or [])

    tail = history[cursor:]

    if summary:
        return [
            {"role": "system", "content": f"[Conversation summary up to this point]\n{summary}"},
        ] + tail
    return tail


# ---------------------------------------------------------------------------
# Summarization prompt
# ---------------------------------------------------------------------------

_SUMMARIZE_PROMPT = (
    "You are a conversation summarizer for a project-planning assistant. "
    "Combine the existing summary and the new messages into a single concise "
    "summary that replaces the previous one.\n\n"
    "You MUST preserve:\n"
    "- All user preferences and explicit choices (tech stack, tools, frameworks, design preferences)\n"
    "- User ideas, suggestions, and opinions they expressed — even if tentative or exploratory\n"
    "  (e.g. 'I was thinking maybe...', 'I'd prefer...', 'I like the idea of...')\n"
    "- Things the user said they might want to do later or are considering\n"
    "- Key decisions made and the reasoning behind them\n"
    "- Requirements, constraints, and non-functional needs\n"
    "- Architecture details, schema decisions, and deployment choices\n"
    "- Anything the user might reference back to later in the conversation\n\n"
    "You SHOULD drop:\n"
    "- Greetings, chit-chat, and filler acknowledgements\n"
    "- Redundant back-and-forth that led to an already-captured decision\n\n"
    "Keep the summary under 800 words.\n\n"
    "Existing summary:\n{existing_summary}\n\n"
    "New messages to incorporate:\n{new_messages}\n\n"
    "Updated summary:"
)


# ---------------------------------------------------------------------------
# Core summarization logic
# ---------------------------------------------------------------------------

async def maybe_summarize(
    history: list[dict],
    existing_summary: str,
    summary_up_to_index: int,
    llm: Any | None,
    *,
    token_threshold: int = 4_000,
) -> tuple[str, int] | None:
    """Summarize unsummarized history if it exceeds *token_threshold*.

    Args:
        history: Full ``conversation_history`` list.
        existing_summary: Current rolling summary (may be empty on first call).
        summary_up_to_index: Index into *history* up to which the summary covers.
        llm: LangChain-compatible LLM (must support ``ainvoke``/``invoke``).
             If ``None``, uses a truncation fallback.
        token_threshold: Minimum estimated token count of the unsummarized tail
            before summarization triggers.

    Returns:
        ``(new_summary, new_cursor_index)`` if summarization was performed,
        or ``None`` if the tail is still below the threshold.
    """
    tail = history[summary_up_to_index:]
    if not tail:
        return None

    tail_text = _history_text(tail)
    # Count tokens for the full effective context: existing summary + unsummarized tail.
    effective_text = f"{existing_summary}\n{tail_text}" if existing_summary else tail_text
    effective_tokens = estimate_tokens(effective_text)

    if effective_tokens < token_threshold:
        return None

    # New cursor: everything up to (but not including) the very last 2 messages
    # (the most recent user+assistant pair) stays summarized, so the user always
    # sees their last exchange verbatim.
    keep_recent = min(2, len(tail))
    new_cursor = summary_up_to_index + len(tail) - keep_recent
    messages_to_summarize = history[summary_up_to_index:new_cursor]

    if not messages_to_summarize:
        return None

    new_messages_text = _history_text(messages_to_summarize)

    if llm is not None:
        try:
            prompt = _SUMMARIZE_PROMPT.format(
                existing_summary=existing_summary or "(none)",
                new_messages=new_messages_text,
            )
            if hasattr(llm, "ainvoke"):
                response = await llm.ainvoke(prompt)
            else:
                response = llm.invoke(prompt)
            text = _extract_text(response)
            if text:
                return (text, new_cursor)
        except Exception:
            pass

    # Fallback: truncation-based "summary" when no LLM is available.
    max_chars = token_threshold * 2  # ~token_threshold/2 tokens worth
    combined = f"{existing_summary}\n\n{new_messages_text}" if existing_summary else new_messages_text
    if len(combined) > max_chars:
        combined = combined[-max_chars:]
    return (combined.strip(), new_cursor)


def _extract_text(response: Any) -> str:
    """Pull plain text from a LangChain response object."""
    if response is None:
        return ""
    if isinstance(response, str):
        return response.strip()
    content = getattr(response, "content", None)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item.strip())
            elif isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]).strip())
            elif hasattr(item, "text"):
                parts.append(str(getattr(item, "text")).strip())
        return "\n".join(part for part in parts if part).strip()
    return str(response).strip()

