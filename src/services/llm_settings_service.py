"""Helpers for project-scoped LLM settings and verification."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from src.utils.config import get_settings

# Short UI names / legacy saved values -> Generative Language API model id
# See https://ai.google.dev/gemini-api/docs/models
_GEMINI_API_MODEL_ALIASES: dict[str, str] = {
    "gemini-3-flash": "gemini-3-flash-preview",
    "gemini-3.1-pro": "gemini-3.1-pro-preview",
    "gemini-3.1-prop": "gemini-3.1-pro-preview",  # common typo
    "gemini-3.1-flash-lite": "gemini-3.1-flash-lite-preview",
    # 2.0 Flash family (deprecated but still valid ids; shorthand without "2.0")
    "gemini-2-flash": "gemini-2.0-flash",
    "gemini-2-flash-lite": "gemini-2.0-flash-lite",
}


def normalize_gemini_model_id(model: str | None) -> str:
    """Map friendly or deprecated ids to the model string the API expects."""
    m = (model or "").strip()
    if not m:
        return ""
    return _GEMINI_API_MODEL_ALIASES.get(m, m)


def sanitize_llm_settings(
    raw: dict | Any,
    *,
    owner_uid: str | None = None,
    project_id: str | None = None,
) -> dict:
    """Return frontend-safe LLM settings (never includes raw API key)."""
    if hasattr(raw, "model_dump"):
        payload = raw.model_dump()
    elif isinstance(raw, dict):
        payload = dict(raw)
    else:
        payload = {}

    has_custom = False
    if owner_uid and project_id:
        from src.services.llm_custom_key_store import custom_key_is_set

        has_custom = custom_key_is_set(owner_uid, project_id)

    settings = get_settings()
    return {
        "mode": payload.get("mode", "default"),
        "model": payload.get("model"),
        "has_custom_key": has_custom,
        "verified": bool(payload.get("verified", False)),
        "verified_at": payload.get("verified_at"),
        "allowed_default_models": list(getattr(settings, "allowed_default_models", []) or []),
        "supported_custom_models": list(getattr(settings, "supported_custom_models", []) or []),
    }


def public_llm_runtime(project_state: Any, *, owner_uid: str | None = None) -> dict[str, str]:
    """Safe summary for API/UI: effective model and key source (no secrets).

    Pass ``owner_uid`` from the authenticated user when available; custom keys are stored under
    (owner_uid, project_id) and ``project_state.owner_uid`` may be missing on older rows.
    """
    cfg = resolve_effective_llm_config(project_state, owner_uid=owner_uid)
    return {
        "model": str(cfg.get("model") or ""),
        "source": str(cfg.get("source") or ""),
        "mode": str(cfg.get("mode") or ""),
    }


def public_llm_runtime_view(project_state: Any, *, owner_uid: str | None = None) -> dict[str, str | bool]:
    """Like ``public_llm_runtime`` plus saved (DB) settings for UI chips.

    The effective ``model`` may stay on an app-default id until custom key + verified; the console
    should prefer ``saved_model`` when ``saved_mode == custom`` and not yet ``source == custom``.
    """
    from src.services.llm_custom_key_store import custom_key_is_set

    eff = public_llm_runtime(project_state, owner_uid=owner_uid)
    llm = getattr(project_state, "llm_settings", None)
    pid = (getattr(project_state, "session_id", None) or "").strip()
    uid = (owner_uid or "").strip()

    saved_mode = "default"
    saved_model = ""
    saved_verified = False
    if llm is not None:
        saved_mode = (getattr(llm, "mode", None) or "default").strip() or "default"
        raw_saved = (getattr(llm, "model", None) or "").strip()
        saved_model = (normalize_gemini_model_id(raw_saved) or raw_saved) if raw_saved else ""
        saved_verified = bool(getattr(llm, "verified", False))

    has_custom_key = bool(uid and pid and custom_key_is_set(uid, pid))

    return {
        **eff,
        "saved_model": saved_model,
        "saved_mode": saved_mode,
        "saved_verified": saved_verified,
        "has_custom_key": has_custom_key,
    }


def _memory_key_for_state(project_state: Any, owner_uid: str | None = None) -> str | None:
    uid = (owner_uid or getattr(project_state, "owner_uid", None) or "").strip()
    pid = (getattr(project_state, "session_id", None) or "").strip()
    if not uid or not pid:
        return None
    from src.services.llm_custom_key_store import get_custom_key

    key = get_custom_key(uid, pid)
    return key if key else None


def resolve_effective_llm_config(
    project_state: Any,
    *,
    custom_api_key_memory: str | None = None,
    owner_uid: str | None = None,
) -> dict:
    """Resolve request-scoped key/model with safe fallback to defaults."""
    settings = get_settings()
    default_key = getattr(settings, "gemini_api_key", "")
    default_model = normalize_gemini_model_id(
        getattr(settings, "model_name", "gemini-2.5-flash")
    ) or getattr(settings, "model_name", "gemini-2.5-flash")
    allowed_default_models = {
        normalize_gemini_model_id(x) or x for x in (getattr(settings, "allowed_default_models", []) or [])
    }

    llm_settings = getattr(project_state, "llm_settings", None)
    if llm_settings is None:
        return {
            "api_key": default_key,
            "model": default_model,
            "mode": "default",
            "source": "default",
        }

    mode = getattr(llm_settings, "mode", "default") or "default"
    mem_key = ""
    if custom_api_key_memory is not None:
        mem_key = (custom_api_key_memory or "").strip()
    if not mem_key and project_state is not None:
        mem_key = (_memory_key_for_state(project_state, owner_uid) or "").strip()
    raw_model = (getattr(llm_settings, "model", None) or default_model).strip()
    model = normalize_gemini_model_id(raw_model) or raw_model or default_model
    verified = bool(getattr(llm_settings, "verified", False))

    if mode == "custom" and mem_key and verified:
        return {
            "api_key": mem_key,
            "model": normalize_gemini_model_id(model) or model,
            "mode": "custom",
            "source": "custom",
        }

    # Default mode can only use an allowlisted model.
    if allowed_default_models and model not in allowed_default_models:
        model = default_model if default_model in allowed_default_models else next(iter(allowed_default_models))
    model = normalize_gemini_model_id(model) or model

    return {
        "api_key": default_key,
        "model": model,
        "mode": "default",
        "source": "default",
    }


async def verify_gemini_key_model(api_key: str, model: str) -> tuple[bool, str]:
    """Run a lightweight generation call to verify key/model usability."""
    try:
        api_model = normalize_gemini_model_id(model) or model.strip()
        llm = ChatGoogleGenerativeAI(
            model=api_model,
            temperature=0.0,
            max_output_tokens=16,
            google_api_key=api_key,
        )
        response = await llm.ainvoke([HumanMessage(content="Reply with exactly: OK")])
        content = getattr(response, "content", "")
        if content:
            return True, "Key and model verified."
        return True, "Key verified (empty response content)."
    except Exception as exc:
        return False, f"Verification failed: {type(exc).__name__}: {exc}"


def now_iso() -> str:
    """UTC ISO timestamp helper."""
    return datetime.now(timezone.utc).isoformat()

