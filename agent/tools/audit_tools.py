"""
Audit, session, dashboard, workflow progress, and analytics tools.
All backed by the persistent session_store — no hardcoded stubs.
"""
from smolagents.tools import Tool
from tools.llm_utils import generate
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Make session_store importable from tools/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import session_store as ss


# ---------------------------------------------------------------------------
# Audit Logger — writes to session file
# ---------------------------------------------------------------------------

class AuditLoggerTool(Tool):
    name = "audit_logger"
    description = (
        "Log an audit trail entry for an answer: which sources were used, "
        "confidence level, and tool calls made. Stored in the session file."
    )
    inputs = {
        "session_id": {"type": "string", "description": "Session identifier"},
        "answer_text": {"type": "string", "description": "The generated answer text"},
        "source_chunk_ids": {
            "type": "string",
            "description": "Comma-separated source chunk IDs used",
            "nullable": True,
        },
        "confidence": {
            "type": "string",
            "description": "Confidence level: high | medium | low",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self,
        session_id: str,
        answer_text: str,
        source_chunk_ids: str = None,
        confidence: str = "high",
    ) -> str:
        import hashlib

        trace_id = f"trace_{hashlib.md5(f'{session_id}{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:8]}"
        sources = [s.strip() for s in source_chunk_ids.split(",")] if source_chunk_ids else []

        entry = {
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat(),
            "answer_length": len(answer_text),
            "sources_used": sources,
            "source_count": len(sources),
            "confidence": confidence or "high",
        }

        # Append to session's audit log
        data = ss.load_session(session_id)
        if data:
            if "audit_log" not in data:
                data["audit_log"] = []
            data["audit_log"].append(entry)
            data["updated_at"] = datetime.utcnow().isoformat()
            ss._save_raw(session_id, data)

        return json.dumps({"logged": True, **entry})


# ---------------------------------------------------------------------------
# 8. Session Manager — wired to real session_store
# ---------------------------------------------------------------------------

class SessionManagerTool(Tool):
    name = "session_manager"
    description = (
        "Create, resume, or update a user session. Sessions are persisted to disk "
        "so the agent remembers the conversation across page refreshes and restarts."
    )
    inputs = {
        "action": {
            "type": "string",
            "description": "Action: create | resume | update | list",
        },
        "session_id": {
            "type": "string",
            "description": "Session ID (required for resume/update)",
            "nullable": True,
        },
        "user_label": {
            "type": "string",
            "description": "Human-readable label for the session, e.g. user name or case summary",
            "nullable": True,
        },
        "context_update": {
            "type": "string",
            "description": "JSON string of case context fields to update, e.g. '{\"location\": \"Mumbai\"}'",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self,
        action: str,
        session_id: str = None,
        user_label: str = None,
        context_update: str = None,
    ) -> str:
        action = action.lower().strip()

        if action == "create":
            sid = session_id or ss.new_session_id()
            data = ss.create_session(sid, user_label=user_label or "")
            return json.dumps({
                "action": "create",
                "session_id": sid,
                "created_at": data["created_at"],
                "message": f"New session created. Session ID: {sid}",
            })

        elif action == "resume":
            if not session_id:
                return json.dumps({"error": "session_id is required for resume"})
            data = ss.load_session(session_id)
            if data is None:
                return json.dumps({"error": f"Session '{session_id}' not found"})
            return json.dumps({
                "action": "resume",
                "session_id": session_id,
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "message_count": len(data.get("messages", [])),
                "step_count": len(data.get("agent_memory", [])),
                "case_context": data.get("case_context", {}),
                "message": f"Session '{session_id}' resumed with {len(data.get('messages', []))} messages.",
            })

        elif action == "update":
            if not session_id:
                return json.dumps({"error": "session_id is required for update"})
            if context_update:
                try:
                    ctx = json.loads(context_update)
                    ss.save_case_context(session_id, ctx)
                except Exception as e:
                    return json.dumps({"error": f"Invalid context_update JSON: {e}"})
            return json.dumps({
                "action": "update",
                "session_id": session_id,
                "updated": True,
                "message": "Session context updated.",
            })

        elif action == "list":
            sessions = ss.list_sessions()
            return json.dumps({
                "action": "list",
                "total": len(sessions),
                "sessions": sessions[:20],  # cap at 20
            })

        else:
            return json.dumps({"error": f"Unknown action '{action}'. Use: create | resume | update | list"})


# ---------------------------------------------------------------------------
# 9. Case Dashboard — reads real session data
# ---------------------------------------------------------------------------

class CaseDashboardTool(Tool):
    name = "case_dashboard"
    description = (
        "Show an overview of the user's current case: what has been done, "
        "current step, next action, and any saved documents."
    )
    inputs = {
        "session_id": {
            "type": "string",
            "description": "The session ID to load the dashboard for.",
        },
    }
    output_type = "string"

    def forward(self, session_id: str) -> str:
        data = ss.load_session(session_id)
        if data is None:
            return json.dumps({
                "error": f"Session '{session_id}' not found.",
                "tip": "Start a new conversation to create a session.",
            })

        ctx = data.get("case_context", {})
        steps = data.get("agent_memory", [])
        messages = data.get("messages", [])

        # Derive last action and next step from memory
        last_answer = ""
        last_tool_calls = []
        for step in reversed(steps):
            if step.get("final_answer"):
                last_answer = step["final_answer"][:300]
                break
            if step.get("tool_calls") and not last_tool_calls:
                last_tool_calls = [tc["name"] for tc in step["tool_calls"]]

        # Check for any exported drafts
        exports_dir = Path(__file__).resolve().parents[1] / "exports"
        exported_files = []
        if exports_dir.exists():
            exported_files = [f.name for f in exports_dir.iterdir() if f.is_file()]

        return json.dumps({
            "session_id": session_id,
            "created_at": data.get("created_at", ""),
            "last_active": data.get("updated_at", ""),
            "case_context": ctx,
            "conversation_turns": len([m for m in messages if m.get("role") == "user"]),
            "steps_completed": len(steps),
            "last_tools_used": last_tool_calls,
            "last_answer_preview": last_answer,
            "exported_documents": exported_files,
            "audit_entries": len(data.get("audit_log", [])),
        }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 10. Workflow Progress Tracker — persists step status to session
# ---------------------------------------------------------------------------

class WorkflowProgressTool(Tool):
    name = "workflow_progress"
    description = (
        "Track and update the completion status of workflow steps for a case. "
        "Persists progress to the session so it survives restarts."
    )
    inputs = {
        "session_id": {
            "type": "string",
            "description": "Session ID to track progress for.",
        },
        "case_id": {
            "type": "string",
            "description": "A short identifier for this case, e.g. 'consumer_001'.",
        },
        "step_number": {
            "type": "number",
            "description": "The step number being updated.",
        },
        "step_description": {
            "type": "string",
            "description": "What this step involves, e.g. 'File complaint at District Forum'.",
        },
        "status": {
            "type": "string",
            "description": "Status: pending | in_progress | completed | blocked",
        },
        "notes": {
            "type": "string",
            "description": "Any notes about this step, e.g. 'Submitted on 15 Jan, awaiting hearing date'.",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self,
        session_id: str,
        case_id: str,
        step_number: int,
        step_description: str,
        status: str,
        notes: str = None,
    ) -> str:
        data = ss.load_session(session_id)
        if data is None:
            return json.dumps({"error": f"Session '{session_id}' not found."})

        if "workflow_progress" not in data:
            data["workflow_progress"] = {}

        if case_id not in data["workflow_progress"]:
            data["workflow_progress"][case_id] = {"steps": {}}

        data["workflow_progress"][case_id]["steps"][str(step_number)] = {
            "step_number": step_number,
            "description": step_description,
            "status": status,
            "notes": notes or "",
            "updated_at": datetime.utcnow().isoformat(),
        }
        data["updated_at"] = datetime.utcnow().isoformat()
        ss._save_raw(session_id, data)

        # Summarise all steps for this case
        all_steps = data["workflow_progress"][case_id]["steps"]
        completed = sum(1 for s in all_steps.values() if s["status"] == "completed")
        total = len(all_steps)

        return json.dumps({
            "session_id": session_id,
            "case_id": case_id,
            "step_number": step_number,
            "status": status,
            "progress": f"{completed}/{total} steps completed",
            "all_steps": all_steps,
            "message": f"Step {step_number} marked as '{status}'.",
        })


# ---------------------------------------------------------------------------
# 11. Analytics Reporter — reads real session files for metrics
# ---------------------------------------------------------------------------

class AnalyticsReporterTool(Tool):
    name = "analytics_reporter"
    description = (
        "Report real usage analytics computed from session files: "
        "workflow completion rate, average session depth, language usage, "
        "most common case types, and drop-off points."
    )
    inputs = {
        "metric": {
            "type": "string",
            "description": (
                "Metric to report: completion_rate | session_depth | "
                "language_usage | case_types | dropoff | summary"
            ),
        },
        "date_range": {
            "type": "string",
            "description": "Date range: today | week | month | all",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, metric: str, date_range: str = "week") -> str:
        sessions = ss.list_sessions()
        if not sessions:
            return json.dumps({"metric": metric, "message": "No sessions found yet.", "value": 0})

        # Filter by date range
        now = datetime.utcnow()
        cutoffs = {"today": now - timedelta(days=1), "week": now - timedelta(days=7), "month": now - timedelta(days=30)}
        cutoff = cutoffs.get(date_range or "week")

        filtered = sessions
        if cutoff:
            filtered = []
            for s in sessions:
                try:
                    updated = datetime.fromisoformat(s.get("updated_at", ""))
                    if updated >= cutoff:
                        filtered.append(s)
                except Exception:
                    filtered.append(s)

        total = len(filtered)
        if total == 0:
            return json.dumps({"metric": metric, "date_range": date_range, "total_sessions": 0, "message": "No sessions in this date range."})

        metric = metric.lower().strip()

        if metric == "session_depth":
            depths = [s.get("step_count", 0) for s in filtered]
            avg = sum(depths) / len(depths) if depths else 0
            return json.dumps({
                "metric": "session_depth",
                "date_range": date_range,
                "total_sessions": total,
                "average_steps_per_session": round(avg, 2),
                "max_steps": max(depths) if depths else 0,
                "min_steps": min(depths) if depths else 0,
            })

        elif metric == "completion_rate":
            # A session is "complete" if it has >= 3 steps (classify + retrieve + answer)
            completed = sum(1 for s in filtered if s.get("step_count", 0) >= 3)
            rate = completed / total if total else 0
            return json.dumps({
                "metric": "completion_rate",
                "date_range": date_range,
                "total_sessions": total,
                "completed_sessions": completed,
                "completion_rate": round(rate, 3),
                "completion_rate_pct": f"{round(rate * 100, 1)}%",
            })

        elif metric in ("language_usage", "case_types", "dropoff", "summary"):
            # Load full session data for richer metrics
            case_types: dict = {}
            languages: dict = {}
            dropoff_steps: list = []

            for s in filtered:
                data = ss.load_session(s["session_id"])
                if not data:
                    continue
                ctx = data.get("case_context", {})
                ct = ctx.get("case_type", "unknown")
                case_types[ct] = case_types.get(ct, 0) + 1
                lang = ctx.get("language", "en")
                languages[lang] = languages.get(lang, 0) + 1
                steps = data.get("agent_memory", [])
                if steps and not any(s.get("final_answer") for s in steps):
                    dropoff_steps.append(len(steps))

            if metric == "language_usage":
                return json.dumps({"metric": "language_usage", "date_range": date_range, "total_sessions": total, "by_language": languages})
            elif metric == "case_types":
                return json.dumps({"metric": "case_types", "date_range": date_range, "total_sessions": total, "by_case_type": case_types})
            elif metric == "dropoff":
                avg_dropoff = sum(dropoff_steps) / len(dropoff_steps) if dropoff_steps else 0
                return json.dumps({"metric": "dropoff", "date_range": date_range, "total_sessions": total, "sessions_without_final_answer": len(dropoff_steps), "avg_steps_at_dropoff": round(avg_dropoff, 2)})
            else:  # summary
                completed = sum(1 for s in filtered if s.get("step_count", 0) >= 3)
                depths = [s.get("step_count", 0) for s in filtered]
                return json.dumps({
                    "metric": "summary",
                    "date_range": date_range,
                    "total_sessions": total,
                    "completion_rate_pct": f"{round(completed / total * 100, 1)}%" if total else "0%",
                    "avg_steps": round(sum(depths) / len(depths), 2) if depths else 0,
                    "case_types": case_types,
                    "languages": languages,
                    "dropoff_sessions": len(dropoff_steps),
                })
        else:
            return json.dumps({"error": f"Unknown metric '{metric}'. Use: completion_rate | session_depth | language_usage | case_types | dropoff | summary"})
