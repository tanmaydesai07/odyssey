"""
Persistent session store for the Legal AI Agent.

Saves the agent's full conversation memory to disk so sessions survive:
- Page refreshes
- Server restarts
- Browser tab closes

Storage layout:
    sessions/
        <session_id>.json   — one file per session

Each file contains a list of memory steps serialised as dicts.
The agent's smolagents memory is reconstructed from these on resume.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# Where session files live — relative to this file
SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def _load_raw(session_id: str) -> Optional[dict]:
    """Load raw session dict from disk. Returns None if not found."""
    path = _session_path(session_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[SessionStore] Failed to load {session_id}: {e}")
        return None


def _save_raw(session_id: str, data: dict) -> None:
    """Write raw session dict to disk atomically."""
    path = _session_path(session_id)
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        tmp.replace(path)
    except Exception as e:
        print(f"[SessionStore] Failed to save {session_id}: {e}")
        if tmp.exists():
            tmp.unlink()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def new_session_id() -> str:
    """Generate a fresh unique session ID."""
    return uuid.uuid4().hex[:12]


def create_session(session_id: str, user_label: str = "") -> dict:
    """Create a new empty session and persist it."""
    data = {
        "session_id": session_id,
        "user_label": user_label,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "messages": [],          # list of {role, content} dicts — the chat history
        "agent_memory": [],      # serialised smolagents memory steps
        "case_context": {},      # extracted facts: name, location, case_type, etc.
    }
    _save_raw(session_id, data)
    print(f"[SessionStore] Created session {session_id}")
    return data


def load_session(session_id: str) -> Optional[dict]:
    """Load a session. Returns None if it doesn't exist."""
    return _load_raw(session_id)


def save_messages(session_id: str, messages: list) -> None:
    """
    Persist the Gradio chat message list for a session.
    messages: list of gr.ChatMessage-like objects or plain dicts with role/content.
    """
    data = _load_raw(session_id)
    if data is None:
        data = create_session(session_id)

    # Serialise — gr.ChatMessage objects have .role and .content attributes
    serialised = []
    for m in messages:
        if isinstance(m, dict):
            serialised.append(m)
        else:
            serialised.append({
                "role": getattr(m, "role", "user"),
                "content": getattr(m, "content", str(m)),
                "metadata": getattr(m, "metadata", {}),
            })

    data["messages"] = serialised
    data["updated_at"] = datetime.utcnow().isoformat()
    _save_raw(session_id, data)


def save_agent_memory(session_id: str, agent) -> None:
    """
    Serialise the smolagents agent's memory steps to disk.

    smolagents stores history in agent.memory.steps — a list of step objects.
    We serialise each step as a plain dict so it can be stored as JSON.
    We don't need to reconstruct the full step objects on reload — instead we
    inject the history back as plain text messages (see restore_agent_memory).
    """
    data = _load_raw(session_id)
    if data is None:
        data = create_session(session_id)

    steps = []
    try:
        memory_steps = agent.memory.steps if hasattr(agent, "memory") else []
        for step in memory_steps:
            step_dict = {}
            # Common fields across all step types
            for attr in ("step_number", "model_output", "observations", "error"):
                val = getattr(step, attr, None)
                if val is not None:
                    step_dict[attr] = str(val)
            # Tool calls
            if hasattr(step, "tool_calls") and step.tool_calls:
                step_dict["tool_calls"] = [
                    {
                        "name": getattr(tc, "name", ""),
                        "arguments": str(getattr(tc, "arguments", "")),
                    }
                    for tc in step.tool_calls
                ]
            # Plan text
            if hasattr(step, "plan") and step.plan:
                step_dict["plan"] = str(step.plan)
            # Final answer
            if hasattr(step, "final_answer") and step.final_answer:
                step_dict["final_answer"] = str(step.final_answer)

            step_dict["type"] = type(step).__name__
            steps.append(step_dict)
    except Exception as e:
        print(f"[SessionStore] Warning: could not serialise agent memory: {e}")

    data["agent_memory"] = steps
    data["updated_at"] = datetime.utcnow().isoformat()
    _save_raw(session_id, data)
    print(f"[SessionStore] Saved {len(steps)} memory steps for session {session_id}")


def save_case_context(session_id: str, context: dict) -> None:
    """
    Save extracted case facts (name, location, case_type, etc.) for a session.
    Merges with existing context rather than replacing it.
    """
    data = _load_raw(session_id)
    if data is None:
        data = create_session(session_id)
    data["case_context"].update(context)
    data["updated_at"] = datetime.utcnow().isoformat()
    _save_raw(session_id, data)


def restore_agent_memory(session_id: str, agent) -> bool:
    """
    Restore a previous session into the agent's memory.

    Strategy: inject the saved conversation as a condensed system message
    prepended to the agent's memory. This is the most reliable approach
    because it doesn't require reconstructing smolagents internal step objects.

    Returns True if memory was restored, False if session not found.
    """
    data = _load_raw(session_id)
    if not data:
        return False

    steps = data.get("agent_memory", [])
    if not steps:
        return False

    # Build a compact summary of the previous conversation
    summary_lines = [
        "=== PREVIOUS SESSION CONTEXT (do not repeat this to the user) ===",
        f"Session ID: {session_id}",
        f"Started: {data.get('created_at', 'unknown')}",
        "",
    ]

    case_ctx = data.get("case_context", {})
    if case_ctx:
        summary_lines.append("Known facts about the user's case:")
        for k, v in case_ctx.items():
            summary_lines.append(f"  - {k}: {v}")
        summary_lines.append("")

    summary_lines.append("Previous conversation steps:")
    for step in steps:
        stype = step.get("type", "Step")
        if step.get("plan"):
            summary_lines.append(f"[Plan] {step['plan'][:300]}")
        if step.get("model_output"):
            summary_lines.append(f"[{stype}] Thought: {step['model_output'][:200]}")
        if step.get("tool_calls"):
            for tc in step["tool_calls"]:
                summary_lines.append(f"  -> Called {tc['name']}({str(tc['arguments'])[:150]})")
        if step.get("observations"):
            summary_lines.append(f"  -> Result: {step['observations'][:200]}")
        if step.get("final_answer"):
            summary_lines.append(f"[Answer] {step['final_answer'][:400]}")

    summary_lines.append("=== END OF PREVIOUS SESSION CONTEXT ===")
    summary = "\n".join(summary_lines)

    # Inject into agent memory as a system-level task memory entry
    # smolagents CodeAgent exposes agent.memory which has a .steps list
    try:
        from smolagents.memory import TaskStep
        # TaskStep is the initial "New task:" entry — we prepend a fake one
        # with our summary so the agent sees it as prior context
        task_step = TaskStep(task=summary)
        agent.memory.steps.insert(0, task_step)
        print(f"[SessionStore] Restored {len(steps)} steps into agent memory for session {session_id}")
        return True
    except Exception as e:
        print(f"[SessionStore] Could not inject memory steps: {e}")
        return False


def list_sessions() -> list:
    """Return a list of all session metadata (id, created_at, updated_at, label)."""
    sessions = []
    for path in sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions.append({
                "session_id": data.get("session_id", path.stem),
                "user_label": data.get("user_label", ""),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
                "step_count": len(data.get("agent_memory", [])),
                "message_count": len(data.get("messages", [])),
            })
        except Exception:
            pass
    return sessions


def delete_session(session_id: str) -> bool:
    """Delete a session file. Returns True if deleted."""
    path = _session_path(session_id)
    if path.exists():
        path.unlink()
        print(f"[SessionStore] Deleted session {session_id}")
        return True
    return False
