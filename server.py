"""
FastAPI server for the Legal AI Agent.

Exposes the agent over HTTP so Node.js backend (and React frontend)
can talk to it. Runs alongside or instead of the Gradio UI.

Start with:
    conda run -n shrishtiai python agent/server.py

Endpoints:
    POST /session/new           — create a new case session
    GET  /session/{id}          — load session (history + docs + context)
    DELETE /session/{id}        — delete a session
    POST /chat                  — send a message, get SSE stream back
    POST /export                — generate DOCX/PDF for a draft
    GET  /document/{session_id}/{filename} — download a generated document
    POST /upload/{session_id}   — upload evidence file into a session
    GET  /health                — health check

All session data is stored in agent/sessions/{session_id}.json
All documents are stored in agent/exports/{session_id}/
"""

import os
import sys
import json
import asyncio
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ["PYTHONIOENCODING"] = "utf-8"

os.environ["TOKENIZERS_PARALLELISM"] = "0"

# Add agent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import session_store as ss

# ── Lazy-load the agent (heavy — only once) ───────────────────────────────
_agent = None

def get_agent():
    global _agent
    if _agent is not None:
        return _agent

    print("[Server] Loading agent...")
    from smolagents import CodeAgent, tool
    from tools.final_answer import FinalAnswerTool
    from tools.case_classifier import CaseClassifierTool
    from tools.jurisdiction_resolver import JurisdictionResolverTool
    from tools.intake_analyzer import IntakeAnalyzerTool, WorkflowPlannerTool
    from tools.legal_retriever import LegalRetrieverTool, SourceCitationTool
    from tools.document_tools import (DraftGeneratorTool, DraftEditorTool,
                                       DocumentExporterTool, AuthorityFinderTool,
                                       ChecklistGeneratorTool)
    from tools.safety_tools import SafetyGuardTool, CrisisEscalatorTool, DisclaimerEnforcerTool
    from tools.translation_tools import TranslatorTool, LegalTermGlossaryTool, LanguageDetectorTool
    from tools.audit_tools import (AuditLoggerTool, SessionManagerTool, CaseDashboardTool,
                                    WorkflowProgressTool, AnalyticsReporterTool)
    from tools.web_tools import WebSearchTool, VisitWebpageTool
    from tools.advanced_tools import (ComplaintStrengthAnalyserTool, EvidenceOrganiserTool,
                                       HearingPreparationTool, MultiDocumentSummariserTool,
                                       EscalationRecommenderTool, PIIScrubbingTool)
    from zen_model import ZenModel

    model = ZenModel(model_id="big-pickle", max_tokens=8192, temperature=0.3)

    SYSTEM_PROMPT = """You are a Legal Assistance Agent for Indian citizens. Help users with FIRs, consumer complaints, RTI applications, and legal processes.

WORKFLOW — follow this order every time:
1. DETECT LANGUAGE using language_detector — respond in the user's language throughout
2. INTAKE using intake_analyzer — extract facts, identify missing info (especially city/state)
3. If intake says ready_to_proceed=false — ask the user the follow_up_questions, wait for answers
4. CLASSIFY using case_classifier
5. RETRIEVE using legal_retriever
6. PLAN using workflow_planner (includes escalation paths)
7. Give final_answer with complete guidance

CRITICAL CODE FORMAT — follow this EXACTLY every single time:

Thought: <your reasoning here>

Code:
```py
result = some_tool(arg="value")
print(result)
```<end_code>

RULES:
- ALWAYS wrap code in ```py ... ``` fences. NEVER write bare code after "Code:".
- NEVER assume the user's location — always ask if city/state is missing.
- Keep tool calls to max 4-5, then give the final answer.
- When calling final_answer(), use a SINGLE string with \\n for newlines.
- Do NOT use triple-quoted strings inside final_answer().
- ALWAYS end your code block with the closing ``` then <end_code> on the same line.
- Always include a disclaimer that this is informational guidance, not legal advice."""

    _agent = CodeAgent(
        model=model,
        tools=[
            FinalAnswerTool(), WebSearchTool(), VisitWebpageTool(),
            CaseClassifierTool(), JurisdictionResolverTool(),
            IntakeAnalyzerTool(), WorkflowPlannerTool(),
            LegalRetrieverTool(), SourceCitationTool(),
            DraftGeneratorTool(), DraftEditorTool(), DocumentExporterTool(),
            AuthorityFinderTool(), ChecklistGeneratorTool(),
            SafetyGuardTool(), CrisisEscalatorTool(), DisclaimerEnforcerTool(),
            TranslatorTool(), LegalTermGlossaryTool(), LanguageDetectorTool(),
            AuditLoggerTool(), SessionManagerTool(), CaseDashboardTool(),
            WorkflowProgressTool(), AnalyticsReporterTool(),
            ComplaintStrengthAnalyserTool(), EvidenceOrganiserTool(),
            HearingPreparationTool(), MultiDocumentSummariserTool(),
            EscalationRecommenderTool(), PIIScrubbingTool(),
        ],
        max_steps=12,
        verbosity_level=1,
        planning_interval=4,
        name="legal_assistant",
        description=SYSTEM_PROMPT,
    )
    print("[Server] Agent loaded.")
    return _agent


# ── Per-session agent memory store ───────────────────────────────────────────
# Each session_id gets its own isolated agent memory so users don't bleed into each other
_session_agents: dict = {}

def get_session_agent(session_id: str):
    """Get or create an agent instance for a specific session."""
    if session_id not in _session_agents:
        # Clone the base agent's config for this session
        base = get_agent()
        from smolagents import CodeAgent
        from zen_model import ZenModel
        model = ZenModel(model_id="big-pickle", max_tokens=8192, temperature=0.3)
        session_agent = CodeAgent(
            model=model,
            tools=base.tools,
            max_steps=12,
            verbosity_level=1,
            planning_interval=4,
            name="legal_assistant",
            description=base.description,
        )
        # Restore memory from disk if session exists
        ss.restore_agent_memory(session_id, session_agent)
        _session_agents[session_id] = session_agent
        print(f"[Server] Created agent for session {session_id}")
    return _session_agents[session_id]


# ── Exports directory (per-session) ──────────────────────────────────────────
EXPORTS_BASE = Path(__file__).parent / "exports"
UPLOADS_BASE = Path(__file__).parent / "uploads"
EXPORTS_BASE.mkdir(exist_ok=True)
UPLOADS_BASE.mkdir(exist_ok=True)

def session_exports_dir(session_id: str) -> Path:
    d = EXPORTS_BASE / session_id
    d.mkdir(exist_ok=True)
    return d

def session_uploads_dir(session_id: str) -> Path:
    d = UPLOADS_BASE / session_id
    d.mkdir(exist_ok=True)
    return d


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Legal AI Agent API",
    description="AI-powered legal assistance for Indian citizens",
    version="1.0.0",
)

# CORS — allow Node.js backend and React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production to your Node.js URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response models ───────────────────────────────────────────────────

class NewSessionRequest(BaseModel):
    user_id: str                    # from Node.js auth (MongoDB user _id)
    case_title: str = "New Case"    # user-given name like "Flipkart complaint"
    language: str = "en"

class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    message: str
    language: str = "en"            # detected or user-selected language

class ExportRequest(BaseModel):
    session_id: str
    draft_id: str
    format: str = "docx"            # docx | pdf | txt


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── Session endpoints ─────────────────────────────────────────────────────────

@app.post("/session/new")
def create_session(req: NewSessionRequest):
    """
    Create a new case session.
    Called by Node.js when user clicks "New Case".
    Returns session_id which Node.js stores in MongoDB against the user.
    """
    session_id = ss.new_session_id()
    data = ss.create_session(session_id, user_label=req.case_title)
    # Store user_id and metadata in session
    data["user_id"]    = req.user_id
    data["case_title"] = req.case_title
    data["language"]   = req.language
    data["documents"]  = []   # list of generated docs bound to this session
    data["uploads"]    = []   # list of uploaded evidence files
    ss._save_raw(session_id, data)

    return {
        "session_id":  session_id,
        "case_title":  req.case_title,
        "created_at":  data["created_at"],
        "user_id":     req.user_id,
    }


@app.get("/session/{session_id}")
def get_session(session_id: str):
    """
    Load a full session — history, documents, case context.
    Called by Node.js when user opens a case from the dashboard.
    """
    data = ss.load_session(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Build clean message history for React chat UI
    messages = []
    for m in data.get("messages", []):
        role    = m.get("role", "user")
        content = m.get("content", "")
        # Only include user and final assistant messages (skip tool call steps)
        meta = m.get("metadata", {})
        if role == "user" or (role == "assistant" and not meta):
            messages.append({"role": role, "content": content})

    return {
        "session_id":   session_id,
        "case_title":   data.get("case_title", "Case"),
        "user_id":      data.get("user_id", ""),
        "language":     data.get("language", "en"),
        "created_at":   data.get("created_at", ""),
        "updated_at":   data.get("updated_at", ""),
        "case_context": data.get("case_context", {}),
        "messages":     messages,
        "documents":    data.get("documents", []),
        "uploads":      data.get("uploads", []),
        "step_count":   len(data.get("agent_memory", [])),
    }


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    """Delete a session and all its files."""
    deleted = ss.delete_session(session_id)
    # Clean up exports and uploads
    for d in [session_exports_dir(session_id), session_uploads_dir(session_id)]:
        if d.exists():
            shutil.rmtree(d)
    return {"deleted": deleted, "session_id": session_id}


@app.get("/sessions/user/{user_id}")
def list_user_sessions(user_id: str):
    """
    List all sessions for a user.
    Node.js calls this to populate the case dashboard.
    """
    all_sessions = ss.list_sessions()
    user_sessions = [s for s in all_sessions
                     if ss.load_session(s["session_id"]) and
                     ss.load_session(s["session_id"]).get("user_id") == user_id]
    return {"user_id": user_id, "cases": user_sessions}


# ── Chat endpoint (SSE streaming) ─────────────────────────────────────────────

@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Send a message to the agent and stream the response back as SSE.

    Node.js proxies this stream to React.
    React uses EventSource or fetch with ReadableStream to render it.

    SSE event format:
        data: {"type": "step", "content": "Thinking..."}
        data: {"type": "tool", "name": "case_classifier", "result": "..."}
        data: {"type": "answer", "content": "Here is your guidance..."}
        data: {"type": "done", "session_id": "abc123"}
        data: {"type": "error", "content": "Something went wrong"}
    """
    session_id = req.session_id
    message    = req.message

    # Ensure session exists
    if not ss.load_session(session_id):
        ss.create_session(session_id, user_label="Case")

    # Get the per-session agent
    agent = get_session_agent(session_id)

    async def event_stream():
        collected_steps = []
        final_answer_text = ""

        try:
            # Run agent in a thread (it's synchronous) and yield steps
            loop = asyncio.get_event_loop()

            def run_agent():
                steps = []
                for step_log in agent.run(task=message, stream=True, reset=False):
                    steps.append(step_log)
                return steps

            # Stream steps as they come using run_in_executor
            from smolagents.agents import ActionStep, PlanningStep, FinalAnswerStep
            import concurrent.futures

            step_queue = asyncio.Queue()

            def _run():
                try:
                    for step_log in agent.run(task=message, stream=True, reset=False):
                        asyncio.run_coroutine_threadsafe(
                            step_queue.put(step_log), loop
                        )
                except Exception as e:
                    asyncio.run_coroutine_threadsafe(
                        step_queue.put(Exception(str(e))), loop
                    )
                finally:
                    asyncio.run_coroutine_threadsafe(
                        step_queue.put(None), loop  # sentinel
                    )

            import threading
            t = threading.Thread(target=_run, daemon=True)
            t.start()

            while True:
                step_log = await step_queue.get()

                if step_log is None:
                    break  # done

                if isinstance(step_log, Exception):
                    yield f"data: {json.dumps({'type': 'error', 'content': str(step_log)})}\n\n"
                    break

                if isinstance(step_log, PlanningStep):
                    plan = str(step_log.plan or "")[:500]
                    yield f"data: {json.dumps({'type': 'plan', 'content': plan})}\n\n"

                elif isinstance(step_log, ActionStep):
                    # Thinking
                    if step_log.model_output:
                        thought = str(step_log.model_output)[:300]
                        yield f"data: {json.dumps({'type': 'step', 'step': step_log.step_number, 'content': thought})}\n\n"

                    # Tool calls
                    if step_log.tool_calls:
                        for tc in step_log.tool_calls:
                            tool_name = getattr(tc, "name", "")
                            yield f"data: {json.dumps({'type': 'tool', 'name': tool_name})}\n\n"

                    # Observations
                    if step_log.observations:
                        obs = str(step_log.observations)[:400]
                        yield f"data: {json.dumps({'type': 'observation', 'content': obs})}\n\n"

                elif isinstance(step_log, FinalAnswerStep):
                    final_answer_text = str(step_log.final_answer or "")
                    yield f"data: {json.dumps({'type': 'answer', 'content': final_answer_text})}\n\n"

            # Persist session after agent finishes
            _persist_session(session_id, agent, message, final_answer_text)

            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering
        },
    )


def _persist_session(session_id: str, agent, user_message: str, agent_answer: str):
    """Save messages and agent memory after each turn."""
    try:
        data = ss.load_session(session_id) or ss.create_session(session_id)

        # Append this turn's messages
        messages = data.get("messages", [])
        messages.append({"role": "user",      "content": user_message,  "metadata": {}})
        messages.append({"role": "assistant", "content": agent_answer,  "metadata": {}})
        data["messages"] = messages
        data["updated_at"] = datetime.utcnow().isoformat()
        ss._save_raw(session_id, data)

        # Save full agent memory
        ss.save_agent_memory(session_id, agent)
    except Exception as e:
        print(f"[Server] Warning: could not persist session {session_id}: {e}")


# ── Document export endpoint ──────────────────────────────────────────────────

@app.post("/export")
def export_document(req: ExportRequest):
    """
    Generate a DOCX/PDF from a draft and bind it to the session.
    Node.js calls this, then serves the file to React for download.
    """
    from tools.document_tools import DocumentExporterTool, DRAFTS_DIR, _load_draft, _save_draft

    draft = _load_draft(req.draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=f"Draft {req.draft_id} not found")

    # Export to session-specific directory
    exports_dir = session_exports_dir(req.session_id)
    ttype = draft.get("template_type", "document")
    filename_base = f"{ttype}_{req.draft_id}"

    # Temporarily override DRAFTS_DIR parent to session exports dir
    # by saving a copy of the draft and exporting from there
    exp = DocumentExporterTool()
    result = json.loads(exp.forward(draft_id=req.draft_id, format=req.format))

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    # Move the file into the session's exports folder
    src = Path(result["file_path"])
    dst = exports_dir / src.name
    if src != dst:
        shutil.copy2(src, dst)

    # Record document in session
    data = ss.load_session(req.session_id)
    if data:
        docs = data.get("documents", [])
        doc_entry = {
            "draft_id":   req.draft_id,
            "filename":   dst.name,
            "format":     req.format,
            "template":   ttype,
            "created_at": datetime.utcnow().isoformat(),
            "path":       str(dst),
        }
        # Replace if same draft_id + format already exists
        docs = [d for d in docs if not (d["draft_id"] == req.draft_id and d["format"] == req.format)]
        docs.append(doc_entry)
        data["documents"] = docs
        data["updated_at"] = datetime.utcnow().isoformat()
        ss._save_raw(req.session_id, data)

    return {
        "session_id": req.session_id,
        "draft_id":   req.draft_id,
        "filename":   dst.name,
        "format":     req.format,
        "download_url": f"/document/{req.session_id}/{dst.name}",
    }


@app.get("/document/{session_id}/{filename}")
def download_document(session_id: str, filename: str):
    """
    Serve a generated document file.
    Node.js proxies this to React as a file download.
    """
    file_path = session_exports_dir(session_id) / filename
    if not file_path.exists():
        # Fallback: check global exports dir
        file_path = EXPORTS_BASE / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    media_types = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf":  "application/pdf",
        ".txt":  "text/plain",
    }
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
    )


# ── File upload endpoint ──────────────────────────────────────────────────────

@app.post("/upload/{session_id}")
async def upload_evidence(session_id: str, file: UploadFile = File(...)):
    """
    Upload an evidence file (photo, receipt, screenshot) into a session.
    Node.js calls this when user attaches a file in React.
    The file is stored in uploads/{session_id}/ and recorded in the session.
    """
    if not ss.load_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    uploads_dir = session_uploads_dir(session_id)
    # Sanitise filename
    safe_name = Path(file.filename).name.replace(" ", "_")
    dest = uploads_dir / safe_name

    # Save file
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)

    # Record in session
    data = ss.load_session(session_id)
    uploads = data.get("uploads", [])
    uploads.append({
        "filename":    safe_name,
        "original":    file.filename,
        "size_bytes":  len(content),
        "content_type": file.content_type,
        "uploaded_at": datetime.utcnow().isoformat(),
        "path":        str(dest),
    })
    data["uploads"] = uploads
    data["updated_at"] = datetime.utcnow().isoformat()
    ss._save_raw(session_id, data)

    return {
        "session_id": session_id,
        "filename":   safe_name,
        "size_bytes": len(content),
        "url":        f"/upload/{session_id}/{safe_name}",
    }


@app.get("/upload/{session_id}/{filename}")
def get_upload(session_id: str, filename: str):
    """Serve an uploaded evidence file."""
    file_path = session_uploads_dir(session_id) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=filename)


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    # Pre-load agent on startup so first request isn't slow
    print("[Server] Pre-loading agent...")
    get_agent()
    print("[Server] Starting FastAPI on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
