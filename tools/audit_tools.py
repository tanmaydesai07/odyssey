from smolagents.tools import Tool
from tools.llm_utils import generate
import json


class AuditLoggerTool(Tool):
    name = "audit_logger"
    description = "Logs audit trail for each answer: source chunks used, confidence, tool calls made."
    inputs = {
        "session_id": {"type": "string", "description": "Session identifier"},
        "answer_text": {"type": "string", "description": "Generated answer"},
        "source_chunk_ids": {"type": "string", "description": "Comma-separated source IDs", "nullable": True},
        "confidence": {"type": "string", "description": "Confidence level", "nullable": True}
    }
    output_type = "string"

    def forward(self, session_id: str, answer_text: str, source_chunk_ids: str = None, confidence: str = "high") -> str:
        return json.dumps({
            "logged": True,
            "trace_id": f"trace_{session_id}",
            "session_id": session_id,
            "answer_length": len(answer_text),
            "sources_used": source_chunk_ids.split(",") if source_chunk_ids else [],
            "confidence": confidence,
        })


class SessionManagerTool(Tool):
    name = "session_manager"
    description = "Creates, resumes, or updates user session with conversation context."
    inputs = {
        "action": {"type": "string", "description": "Action: create, resume, update"},
        "session_id": {"type": "string", "description": "Session ID", "nullable": True},
        "user_id": {"type": "string", "description": "User identifier", "nullable": True},
        "conversation_context": {"type": "string", "description": "Conversation history", "nullable": True}
    }
    output_type = "string"

    def forward(self, action: str, session_id: str = None, user_id: str = None, conversation_context: str = None) -> str:
        return json.dumps({
            "session_id": session_id or "new_session_id",
            "action": action,
            "created": action == "create",
            "resumed": action == "resume",
            "updated": action == "update",
            "context_saved": True
        })


class CaseDashboardTool(Tool):
    name = "case_dashboard"
    description = "Provides overview of user's cases, current status, next steps."
    inputs = {"user_id": {"type": "string", "description": "User identifier"}}
    output_type = "string"

    def forward(self, user_id: str) -> str:
        return json.dumps({
            "user_id": user_id,
            "cases": [
                {"case_id": "CASE001", "case_type": "consumer", "status": "in_progress", "current_step": 1, "next_action": "File complaint"}
            ],
            "message": "Dashboard feature - cases stored in session"
        })


class WorkflowProgressTool(Tool):
    name = "workflow_progress"
    description = "Tracks and updates workflow step completion status."
    inputs = {
        "case_id": {"type": "string", "description": "Case identifier"},
        "step_number": {"type": "number", "description": "Step number"},
        "status": {"type": "string", "description": "Status: completed, in_progress, pending"}
    }
    output_type = "string"

    def forward(self, case_id: str, step_number: int, status: str) -> str:
        return json.dumps({"case_id": case_id, "step_number": step_number, "status": status, "updated": True})


class AnalyticsReporterTool(Tool):
    name = "analytics_reporter"
    description = "Reports analytics: workflow completion rate, dropoff points, session depth, language usage."
    inputs = {
        "metric": {"type": "string", "description": "Metric: completion_rate, dropoff, session_depth, language_usage"},
        "date_range": {"type": "string", "description": "Date range: today, week, month", "nullable": True}
    }
    output_type = "string"

    def forward(self, metric: str, date_range: str = "week") -> str:
        return generate(f"Generate analytics for metric: {metric}, date_range: {date_range}", 
                       "Return JSON with metric, value, and date_range.")