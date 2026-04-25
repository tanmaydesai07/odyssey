"""
Langfuse observability for the Legal AI Agent.

OPTIONAL — only activates when LANGFUSE_SECRET_KEY is set in .env.
If keys are missing, every function here is a silent no-op.
The agent runs identically with or without this.

Setup (free cloud account — 50k observations/month free):
  1. Go to https://cloud.langfuse.com and sign up (free, no credit card)
  2. Create a project, copy the keys
  3. Add to agent/.env:
       LANGFUSE_SECRET_KEY=sk-lf-...
       LANGFUSE_PUBLIC_KEY=pk-lf-...
       LANGFUSE_HOST=https://cloud.langfuse.com

What gets traced:
  - Every agent run (one trace per user message)
  - Every LLM call (token counts + latency)
  - Errors
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

_secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
_public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
_host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").strip()

_langfuse = None
_enabled = False


def _init():
    """Lazy-init Langfuse client. Called once on first use."""
    global _langfuse, _enabled
    if _langfuse is not None:
        return

    if not _secret_key or not _public_key:
        print("[Observability] Langfuse keys not set — tracing disabled.")
        print("[Observability] To enable: add LANGFUSE_SECRET_KEY + LANGFUSE_PUBLIC_KEY to agent/.env")
        _enabled = False
        return

    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            secret_key=_secret_key,
            public_key=_public_key,
            host=_host,
        )
        # Verify connection
        _langfuse.auth_check()
        _enabled = True
        print(f"[Observability] Langfuse tracing ENABLED -> {_host}")
    except Exception as e:
        print(f"[Observability] Langfuse init failed: {e} — tracing disabled.")
        _enabled = False


# ---------------------------------------------------------------------------
# Simple trace context — wraps one user turn
# ---------------------------------------------------------------------------

class _TraceContext:
    """Holds the trace_id and observation for one user turn."""
    def __init__(self, trace_id: str, observation=None):
        self.trace_id = trace_id
        self.observation = observation

    def end(self, output: str = None, error: str = None):
        if self.observation is None:
            return
        try:
            if error:
                self.observation.__exit__(Exception, error, None)
            else:
                # Update output then exit cleanly
                if output and _langfuse:
                    _langfuse.update_current_span(output=output)
                self.observation.__exit__(None, None, None)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_trace(name: str, session_id: str = None, user_query: str = None, metadata: dict = None):
    """
    Start a new trace for one user interaction.
    Returns a _TraceContext (or None if disabled).
    """
    _init()
    if not _enabled or _langfuse is None:
        return None
    try:
        trace_id = _langfuse.create_trace_id()
        obs = _langfuse.start_as_current_observation(
            as_type="span",
            name=name,
            input={"query": user_query or ""},
            metadata={**(metadata or {}), "session_id": session_id or ""},
        )
        obs.__enter__()
        return _TraceContext(trace_id=trace_id, observation=obs)
    except Exception as e:
        print(f"[Observability] start_trace error: {e}")
        return None


def end_trace(trace, output: str = None, error: str = None):
    """Finalise a trace."""
    if trace is None:
        return
    try:
        trace.end(output=output, error=error)
    except Exception as e:
        print(f"[Observability] end_trace error: {e}")


def log_llm_call(trace, model: str, prompt_tokens: int, completion_tokens: int,
                 input_preview: str = None, output_preview: str = None, latency_ms: int = None):
    """Log an LLM generation. Called from ZenModel after each API response."""
    if not _enabled or _langfuse is None:
        return
    try:
        trace_id = getattr(trace, "trace_id", None) if trace else None
        obs = _langfuse.start_as_current_observation(
            as_type="generation",
            name="llm_call",
            model=model,
            input=input_preview or "",
            output=output_preview or "",
            usage_details={
                "input": prompt_tokens,
                "output": completion_tokens,
                "total": prompt_tokens + completion_tokens,
            },
            metadata={"latency_ms": latency_ms} if latency_ms else {},
        )
        with obs:
            pass  # immediately close — data already set
    except Exception as e:
        print(f"[Observability] log_llm_call error: {e}")


def log_score(trace, name: str, value: float, comment: str = None):
    """Attach a 0-1 score to a trace (e.g. RAG relevance)."""
    if not _enabled or _langfuse is None or trace is None:
        return
    try:
        _langfuse.create_score(
            trace_id=trace.trace_id,
            name=name,
            value=value,
            comment=comment,
        )
    except Exception as e:
        print(f"[Observability] log_score error: {e}")


def flush():
    """Flush pending events. Call on app shutdown or after each turn."""
    if _langfuse is not None:
        try:
            _langfuse.flush()
        except Exception:
            pass


def is_enabled() -> bool:
    _init()
    return _enabled
