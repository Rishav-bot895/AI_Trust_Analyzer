from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar, cast

from app.core.config import settings

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:  # pragma: no cover - dependency/import safety for local test environments
    ChatGoogleGenerativeAI = None  # type: ignore[assignment]


DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"
DEFAULT_TEMPERATURE = 0.0

# Shared baseline instruction blocks agents can compose into final prompts.
SYSTEM_PROMPT_FACTUALITY = (
    "You are a factuality and evidence analysis assistant. "
    "Return concise, structured outputs and avoid speculation."
)
SYSTEM_PROMPT_JSON_ONLY = (
    "Return valid JSON only. Do not wrap your answer in markdown fences."
)
SYSTEM_PROMPT_EVIDENCE_POLICY = (
    "Prefer verifiable claims, cite evidence provenance, and clearly indicate uncertainty."
)

P = ParamSpec("P")
R = TypeVar("R")


def get_llm(
    model_name: str = DEFAULT_GEMINI_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
) -> Any:
    """Create a Gemini chat model instance for agent calls."""
    if ChatGoogleGenerativeAI is None:
        raise RuntimeError(
            "langchain-google-genai is not available. Install dependencies from requirements.txt"
        )

    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=settings.GEMINI_API_KEY,
    )


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summarize_state_payload(payload: Any) -> str:
    if isinstance(payload, dict):
        keys = sorted(payload.keys())
        return f"keys={keys}"
    if isinstance(payload, list):
        return f"list(len={len(payload)})"
    if isinstance(payload, str):
        return payload[:120]
    return type(payload).__name__


def timed_agent(agent_name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator that appends and finalizes a timeline event around an agent call."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if _is_async_callable(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                state = _get_state_argument(args, kwargs)
                event = _start_timeline_event(agent_name, state)
                try:
                    result = await cast(Any, func)(*args, **kwargs)
                    _complete_timeline_event(event, result)
                    return result
                except Exception as exc:
                    _complete_timeline_event(event, {"error": str(exc)})
                    raise

            return cast(Callable[P, R], async_wrapper)

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            state = _get_state_argument(args, kwargs)
            event = _start_timeline_event(agent_name, state)
            try:
                result = func(*args, **kwargs)
                _complete_timeline_event(event, result)
                return result
            except Exception as exc:
                _complete_timeline_event(event, {"error": str(exc)})
                raise

        return cast(Callable[P, R], sync_wrapper)

    return decorator


def _is_async_callable(func: Callable[..., Any]) -> bool:
    return getattr(func, "__code__", None) is not None and bool(
        func.__code__.co_flags & 0x80
    )


def _get_state_argument(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    state = kwargs.get("state")
    if state is None and args:
        state = args[0]
    if not isinstance(state, dict):
        raise ValueError("timed_agent expects the first argument to be a state dictionary")
    return state


def _start_timeline_event(agent_name: str, state: dict[str, Any]) -> dict[str, str]:
    timeline = state.setdefault("timeline", [])
    if not isinstance(timeline, list):
        raise ValueError("state['timeline'] must be a list")

    event: dict[str, str] = {
        "agent": agent_name,
        "started_at": _utc_iso_now(),
        "completed_at": "",
        "input_summary": _summarize_state_payload(state),
        "output_summary": "",
    }
    timeline.append(event)
    return event


def _complete_timeline_event(event: dict[str, str], result: Any) -> None:
    event["completed_at"] = _utc_iso_now()
    event["output_summary"] = _summarize_state_payload(result)


def parse_json_response(content: str) -> dict[str, Any]:
    """Parse JSON responses and strip optional markdown code fences."""
    if not isinstance(content, str):
        raise TypeError("content must be a string")

    raw = content.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object at top level")
    return data
