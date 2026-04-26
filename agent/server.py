# -*- coding: utf-8 -*-
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
import re
import asyncio
import shutil
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional


def _looks_like_raw_code(text: str) -> bool:
    """Returns True if text looks like raw Python code or XML tool calls, not a human answer."""
    if not text:
        return False
    # Detect XML-style tool call blocks (MiniMax model format)
    if re.search(r'<(?:minimax:)?tool_call>|<invoke\s+name=', text):
        return True
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return False
    code_line_count = 0
    for line in lines[:15]:
        if re.match(r'^[\w_]+ ?= ?[\w_]+\(', line):  # var = tool(
            code_line_count += 1
        elif re.match(r'^print\(', line):
            code_line_count += 1
        elif line.lower() in ('code', 'code:'):
            code_line_count += 1
        elif re.match(r'^[\w_]+\(.*\)$', line) and '=' not in line:
            code_line_count += 1
    return code_line_count >= max(1, len(lines[:15]) * 0.3)


def _looks_like_raw_json(text: str) -> bool:
    """Check if text is raw JSON output from a tool (not human-readable)."""
    stripped = text.strip()
    if not stripped:
        return False
    # Detect JSON objects or arrays
    if (stripped.startswith('{') and stripped.endswith('}')) or \
       (stripped.startswith('[') and stripped.endswith(']')):
        try:
            parsed = json.loads(stripped)
            # JSON with keys like query, results, case_type, chunk_id = raw tool output
            if isinstance(parsed, dict):
                tool_keys = {'query', 'results', 'case_type', 'chunk_id', 'confidence',
                             'reasoning', 'total_found', 'error', 'source_path',
                             'score', 'category', 'text'}
                if tool_keys & set(parsed.keys()):
                    return True
                # Any JSON with mostly snake_case keys is likely raw tool output
                snake_keys = sum(1 for k in parsed.keys() if '_' in k or k.islower())
                if snake_keys >= len(parsed.keys()) * 0.6 and len(parsed.keys()) >= 2:
                    return True
            elif isinstance(parsed, list):
                return True
            return True  # any parseable JSON in a final answer is suspicious
        except (json.JSONDecodeError, ValueError):
            pass
    return False


def _clean_final_answer(text: str) -> str:
    """
    Strip raw Python code, code fences, tool call lines, and smolagents
    internal markers from the final answer so only human-readable text
    reaches the frontend chat bubble.
    """
    if not text:
        return text

    # If the entire answer is raw JSON from a tool, return empty to trigger synthesis
    if _looks_like_raw_json(text):
        print(f"[Server] Detected raw JSON in final answer, will synthesize instead")
        return ''

    was_all_code = _looks_like_raw_code(text)

    # Remove XML-style tool call blocks (MiniMax/big-pickle model format)
    text = re.sub(r'<(?:minimax:)?tool_call>[\s\S]*?</(?:minimax:)?tool_call>', '', text)
    text = re.sub(r'<invoke\s+name=["\'][^\'"]+["\']>[\s\S]*?</invoke>', '', text)
    text = re.sub(r'<parameter\s+name=["\'][^\'"]+["\']>[\s\S]*?</parameter>', '', text)
    # Remove fenced code blocks (```py ... ``` or ```python ... ```)
    text = re.sub(r'```(?:py|python)?[\s\S]*?```', '', text)
    # Remove <end_code> markers
    text = re.sub(r'<end_code>', '', text)
    # Remove lines that look like Python tool calls: identifier(... or variable = tool(...
    text = re.sub(r'^[\w_]+ ?= ?[\w_]+\(.*\)\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^print\(.*\)\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\w_]+\(.*\)\s*$', '', text, flags=re.MULTILINE)
    # Remove lone "code" header (model sometimes emits just the word "code" on a line)
    text = re.sub(r'^code\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    # Remove "Thought:" prefix lines
    text = re.sub(r'^Thought\s*:.*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    # Remove "Code:" header lines
    text = re.sub(r'^Code\s*:\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    cleaned = text.strip()
    # If the original was raw code and nothing meaningful remains, return empty
    # so caller can substitute a proper fallback
    if was_all_code and len(cleaned) < 60:
        return ''
    return cleaned


def _extract_thought_only(model_output: str) -> str:
    """
    From a full model output (Thought: ... \n\nCode:\n```py\n...```),
    extract only the Thought portion for display in the thinking panel.
    """
    if not model_output:
        return ''
    # Extract text before "Code:" section
    code_section = re.search(r'\n\nCode\s*:', model_output, re.IGNORECASE)
    if code_section:
        thought = model_output[:code_section.start()].strip()
    else:
        thought = model_output.strip()
    # Strip leading "Thought:" label
    thought = re.sub(r'^Thought\s*:\s*', '', thought, flags=re.IGNORECASE).strip()
    return thought[:300]

# Thread-local storage for session_id
_thread_local = threading.local()

def set_current_session_id(session_id: str):
    """Store session_id in thread-local storage for tools to access."""
    _thread_local.session_id = session_id

def get_current_session_id() -> Optional[str]:
    """Get session_id from thread-local storage."""
    return getattr(_thread_local, 'session_id', None)

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
_shared_model = None
_shared_tools = None

def get_shared_resources():
    global _shared_model, _shared_tools
    if _shared_model is not None and _shared_tools is not None:
        return _shared_model, _shared_tools

    print("[Server] Initializing shared model and tools...")
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

    _shared_model = ZenModel(model_id="big-pickle", max_tokens=8192, temperature=0.3)
    _shared_tools = [
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
    ]
    return _shared_model, _shared_tools

def get_agent():
    # Deprecated for per-session use, but used for preloading at startup
    get_shared_resources()
    return None

SYSTEM_PROMPT = """You are NyayaMitr, an AI Legal Assistance Agent for Indian citizens.
Help users navigate FIRs, consumer complaints, RTI applications, landlord disputes, wage issues, and legal processes.

WORKFLOW - follow this order every time:
1. DETECT LANGUAGE using language_detector - respond in the user's language throughout
2. INTAKE using intake_analyzer - extract facts, identify missing info (especially city/state)
3. If intake says ready_to_proceed=false - ask the user the follow_up_questions only, wait for answers
4. CLASSIFY using case_classifier
5. RETRIEVE relevant laws using legal_retriever
6. PLAN steps using workflow_planner
7. Call final_answer() with a complete, formatted human-readable response

CRITICAL CODE FORMAT - follow this EXACTLY every single time:

Thought: <your reasoning here>

Code:
```py
result = some_tool(arg="value")
print(result)
```<end_code>

FINAL ANSWER FORMAT - EXTREMELY IMPORTANT:
- The final_answer() call MUST contain ONLY human-readable text, NEVER code or variable names
- CORRECT:  final_answer("Here are your legal options:\n1. File a complaint...")
- WRONG:    final_answer(case_result)   <- never pass a variable
- WRONG:    final_answer("result = case_classifier(...)...")  <- never pass code
- Build your answer as a string variable, then call final_answer(answer_text)

EXAMPLE of correct final step:
Thought: I have all the info. Now I will give the final answer.

Code:
```py
answer = "Based on your situation in Mumbai:\n\n"
answer += "## Your Legal Options\n"
answer += "1. File a consumer complaint at the Consumer Forum\n"
answer += "2. Send a legal notice to the seller\n\n"
answer += "**Disclaimer**: This is informational guidance only, not legal advice."
final_answer(answer)
```<end_code>

RULES:
- ALWAYS wrap code in ```py ... ``` fences. NEVER write bare code after "Code:".
- NEVER assume the user's location - always ask if city/state is missing.
- Keep tool calls to max 4-5, then give the final answer.
- When calling final_answer(), build the answer as a string with + concatenation, NOT triple quotes.
- ALWAYS end your code block with the closing ``` then <end_code> on the same line.
- Always include a disclaimer that this is informational guidance, not legal advice.
- Format your final answer with ## headings, bullet points, and numbered steps.

DOCUMENT GENERATION - when user asks for a draft, complaint, FIR, RTI, notice, PDF, or DOCX:
1. First call draft_generator(template_type=..., extracted_facts=...) to create the draft
2. Parse the draft_id from the JSON result
3. Then ALWAYS call document_exporter(draft_id=draft_id, format="pdf") to export the file
4. Include the download_url or file_path in your final_answer so the user can access it
- NEVER skip the document_exporter step. The user expects a downloadable file, not just text."""




# ── Per-session agent memory store ───────────────────────────────────────────
# Each session_id gets its own isolated agent memory so users don't bleed into each other
_session_agents: dict = {}

def get_session_agent(session_id: str):
    """Get or create an agent instance for a specific session."""
    if session_id not in _session_agents:
        from smolagents import CodeAgent
        model, tools = get_shared_resources()
        
        base = CodeAgent(
            model=model,
            tools=tools,
            max_steps=12,
            verbosity_level=1,
            planning_interval=4,
            name="legal_assistant",
            description="NyayaMitr legal assistant",
        )
        base.prompt_templates["system_prompt"] += "\n\n" + SYSTEM_PROMPT
        base.initialize_system_prompt()
        
        # Restore memory from disk if session exists
        ss.restore_agent_memory(session_id, base)
        # Store session_id in agent's memory for tools to access
        base.session_id = session_id
        _session_agents[session_id] = base
        print(f"[Server] Created fresh agent for session {session_id}")
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
    from cloud_storage import is_cloudinary_enabled
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "storage": "cloudinary" if is_cloudinary_enabled() else "local",
    }


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
        final_answer_text = ""
        step_count = 0
        max_retries = 2
        retry_count = 0

        try:
            # Run agent in a thread (it's synchronous) and yield steps
            loop = asyncio.get_event_loop()

            from smolagents.agents import ActionStep, PlanningStep, FinalAnswerStep
            import concurrent.futures

            step_queue = asyncio.Queue()
            collected_observations = []  # accumulate tool results for fallback synthesis

            def _run():
                try:
                    # Set session_id in thread-local storage for tools to access
                    set_current_session_id(session_id)
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
                    error_msg = str(step_log)
                    yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
                    
                    # If no answer was generated, provide a fallback
                    if not final_answer_text:
                        final_answer_text = "I apologize, but I encountered an error processing your request. Please try rephrasing your question or contact support for assistance."
                        yield f"data: {json.dumps({'type': 'answer', 'content': final_answer_text})}\n\n"
                    break

                step_count += 1

                if isinstance(step_log, PlanningStep):
                    plan = str(step_log.plan or "")[:500]
                    yield f"data: {json.dumps({'type': 'plan', 'content': plan})}\n\n"

                elif isinstance(step_log, ActionStep):
                    # Thinking
                    if step_log.model_output:
                        thought = _extract_thought_only(str(step_log.model_output))
                        if thought:  # only stream if there's actual thought content
                            yield f"data: {json.dumps({'type': 'step', 'step': step_log.step_number, 'content': thought})}\n\n"

                    # Tool calls
                    if step_log.tool_calls:
                        for tc in step_log.tool_calls:
                            tool_name = getattr(tc, "name", "")
                            yield f"data: {json.dumps({'type': 'tool', 'name': tool_name})}\n\n"

                    # Observations
                    if step_log.observations:
                        obs = str(step_log.observations)[:400]
                        collected_observations.append(obs)  # save for fallback
                        yield f"data: {json.dumps({'type': 'observation', 'content': obs})}\n\n"

                elif isinstance(step_log, FinalAnswerStep):
                    # FinalAnswerStep is a dataclass with a single `output` field
                    raw = step_log.output

                    if isinstance(raw, str):
                        final_answer_text = _clean_final_answer(raw)
                    elif isinstance(raw, dict):
                        # If it has tool-output keys, it's raw tool output — don't format, synthesize
                        tool_keys = {'query', 'results', 'case_type', 'chunk_id', 'confidence',
                                     'reasoning', 'total_found', 'error'}
                        if tool_keys & set(raw.keys()):
                            print(f"[Server] Raw dict with tool keys detected in final answer, will synthesize")
                            final_answer_text = ''  # trigger synthesis below
                            collected_observations.append(json.dumps(raw, indent=2, ensure_ascii=False)[:600])
                        else:
                            # Format dict output nicely
                            parts = []
                            for k, v in raw.items():
                                key = k.replace('_', ' ').title()
                                if isinstance(v, list):
                                    parts.append(f"**{key}:**\n" + '\n'.join(f"- {item}" for item in v))
                                else:
                                    parts.append(f"**{key}:** {v}")
                            final_answer_text = _clean_final_answer('\n\n'.join(parts))
                    else:
                        final_answer_text = _clean_final_answer(str(raw)) if raw is not None else ""

                    # If cleaning removed everything meaningful, build from observations or use fallback
                    if not final_answer_text or len(final_answer_text) < 10:
                        if collected_observations:
                            # Use the LLM to synthesize a proper answer from what tools returned
                            obs_text = '\n---\n'.join(collected_observations[:5])
                            try:
                                from tools.llm_utils import generate
                                synthesis_prompt = (
                                    f"User asked: {message}\n\n"
                                    f"Tool results collected:\n{obs_text}\n\n"
                                    f"Write a clear, helpful legal guidance response in markdown format "
                                    f"with ## headings and bullet points. Include specific next steps. "
                                    f"End with a disclaimer about informational guidance only."
                                )
                                final_answer_text = generate(synthesis_prompt, "You are NyayaMitr, an Indian legal assistance AI. Give clear, practical legal guidance.")
                            except Exception:
                                final_answer_text = "I have analyzed your situation. Please ask me specific questions about your legal options, such as how to file a complaint or what documents you need.\n\n**Disclaimer**: This is informational guidance only, not legal advice."
                        else:
                            final_answer_text = "I have analyzed your situation. Please ask me specific questions about your legal options, such as how to file a complaint or what documents you need.\n\n**Disclaimer**: This is informational guidance only, not legal advice."

                    yield f"data: {json.dumps({'type': 'answer', 'content': final_answer_text})}\n\n"

            # If agent ran but produced no final answer, synthesize from observations
            if step_count > 0 and not final_answer_text:
                if collected_observations:
                    obs_text = '\n---\n'.join(collected_observations[:5])
                    try:
                        from tools.llm_utils import generate
                        synthesis_prompt = (
                            f"User asked: {message}\n\n"
                            f"Tool results collected:\n{obs_text}\n\n"
                            f"Write a clear, helpful legal guidance response in markdown format "
                            f"with ## headings and bullet points. Include specific next steps. "
                            f"End with a disclaimer about informational guidance only."
                        )
                        final_answer_text = generate(synthesis_prompt, "You are NyayaMitr, an Indian legal assistance AI. Give clear, practical legal guidance.")
                    except Exception:
                        final_answer_text = "I have analyzed your situation. Please ask me a specific question like 'What steps should I take?' or 'What documents do I need?'\n\n**Disclaimer**: This is informational guidance only, not legal advice."
                else:
                    final_answer_text = """I understand you need legal assistance. Let me help you properly.\n\nCould you please provide more details about your situation? Specifically:\n1. What happened?\n2. Where did it happen? (City and State)\n3. When did it happen?\n4. What outcome are you seeking?\n\n**Disclaimer**: This is informational guidance only, not legal advice."""
                yield f"data: {json.dumps({'type': 'answer', 'content': final_answer_text})}\n\n"

            # Persist session after agent finishes
            _persist_session(session_id, agent, message, final_answer_text)

            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

        except Exception as e:
            error_msg = f"Server error: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
            
            # Provide fallback answer
            if not final_answer_text:
                final_answer_text = "I apologize, but I'm having trouble processing your request right now. Please try again or contact support."
                yield f"data: {json.dumps({'type': 'answer', 'content': final_answer_text})}\n\n"
                _persist_session(session_id, agent, message, final_answer_text)

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
    Generate a DOCX/PDF from a draft and upload to Cloudinary (or local fallback).
    Returns a public download_url.
    """
    from tools.document_tools import DocumentExporterTool, _load_draft
    from cloud_storage import upload_document

    draft = _load_draft(req.draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=f"Draft {req.draft_id} not found")

    ttype = draft.get("template_type", "document")

    # Generate the file locally first
    exp = DocumentExporterTool()
    result = json.loads(exp.forward(draft_id=req.draft_id, format=req.format, session_id=req.session_id))

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    src = Path(result["file_path"])
    filename = src.name

    # Upload to Cloudinary (or keep local)
    cloud = upload_document(src, req.session_id, filename)

    # Record document in session
    data = ss.load_session(req.session_id)
    if data:
        docs = data.get("documents", [])
        doc_entry = {
            "draft_id":    req.draft_id,
            "filename":    filename,
            "format":      req.format,
            "template":    ttype,
            "created_at":  datetime.utcnow().isoformat(),
            "download_url": cloud["url"],
            "storage":     cloud["storage"],
            "public_id":   cloud["public_id"],
        }
        docs = [d for d in docs if not (d["draft_id"] == req.draft_id and d["format"] == req.format)]
        docs.append(doc_entry)
        data["documents"] = docs
        data["updated_at"] = datetime.utcnow().isoformat()
        ss._save_raw(req.session_id, data)

    return {
        "session_id":   req.session_id,
        "draft_id":     req.draft_id,
        "filename":     filename,
        "format":       req.format,
        "download_url": cloud["url"],
        "storage":      cloud["storage"],
    }


@app.get("/document/{session_id}/{filename}")
def download_document(session_id: str, filename: str):
    """Serve a generated document file from session-grouped folder."""
    from tools.document_exporter_new import get_session_exports_dir

    # Check session folder first
    file_path = get_session_exports_dir(session_id) / filename
    if not file_path.exists():
        # Fallback: global exports dir
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


# ── Voice message transcription ───────────────────────────────────────────────

class TranscribeRequest(BaseModel):
    audio_url: str
    language: str = "en"
    auth_user: Optional[str] = None  # Twilio account SID for auth
    auth_pass: Optional[str] = None  # Twilio auth token for auth

@app.post("/transcribe")
async def transcribe_audio(req: TranscribeRequest):
    """
    Download an audio file (OGG from WhatsApp/Twilio) and transcribe it to text.
    Uses Google Speech Recognition (free, no API key required).
    """
    import tempfile
    import subprocess

    audio_url = req.audio_url
    print(f"[Transcribe] Downloading audio from: {audio_url[:80]}...")

    try:
        # Download the audio file (Twilio URLs require basic auth)
        headers = {}
        auth = None
        if req.auth_user and req.auth_pass:
            auth = (req.auth_user, req.auth_pass)

        import requests as req_lib
        resp = req_lib.get(audio_url, auth=auth, timeout=30)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to download audio: HTTP {resp.status_code}")

        # Save to temp file
        suffix = ".ogg"
        content_type = resp.headers.get("content-type", "")
        if "mp4" in content_type or "m4a" in content_type:
            suffix = ".mp4"
        elif "wav" in content_type:
            suffix = ".wav"
        elif "mpeg" in content_type or "mp3" in content_type:
            suffix = ".mp3"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name

        print(f"[Transcribe] Audio saved ({len(resp.content)} bytes, type={content_type})")

        # Convert to WAV using ffmpeg (required for speech_recognition)
        wav_path = tmp_path.rsplit(".", 1)[0] + ".wav"

        # Find ffmpeg — use imageio-ffmpeg (bundled binary, always works)
        ffmpeg_bin = None
        try:
            import imageio_ffmpeg
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass

        if not ffmpeg_bin:
            # Fallback to system/conda ffmpeg
            for p in [
                os.path.join(sys.prefix, "Library", "bin", "ffmpeg.exe"),
                "ffmpeg",
            ]:
                if p == "ffmpeg" or os.path.exists(p):
                    ffmpeg_bin = p
                    break

        print(f"[Transcribe] ffmpeg binary: {ffmpeg_bin}")

        conversion_ok = False

        # Try ffmpeg first
        if ffmpeg_bin:
            try:
                result = subprocess.run(
                    [ffmpeg_bin, "-y", "-i", tmp_path, "-ar", "16000", "-ac", "1", "-f", "wav", wav_path],
                    capture_output=True, timeout=30
                )
                if result.returncode == 0 and os.path.exists(wav_path):
                    conversion_ok = True
                    print(f"[Transcribe] ffmpeg conversion OK → {wav_path}")
                else:
                    stderr_msg = result.stderr.decode(errors='replace')[:300]
                    print(f"[Transcribe] ffmpeg failed (rc={result.returncode}): {stderr_msg}")
            except FileNotFoundError:
                print("[Transcribe] ffmpeg binary not found at runtime")
            except Exception as e:
                print(f"[Transcribe] ffmpeg error: {e}")

        # Fallback to pydub (also needs ffmpeg, but set its path explicitly)
        if not conversion_ok:
            try:
                from pydub import AudioSegment
                import pydub.utils
                # Tell pydub where ffmpeg is
                if ffmpeg_bin and ffmpeg_bin != "ffmpeg" and os.path.exists(ffmpeg_bin):
                    AudioSegment.converter = ffmpeg_bin
                    ffprobe = ffmpeg_bin.replace("ffmpeg", "ffprobe")
                    if os.path.exists(ffprobe):
                        AudioSegment.ffprobe = ffprobe
                audio = AudioSegment.from_file(tmp_path)
                audio = audio.set_frame_rate(16000).set_channels(1)
                audio.export(wav_path, format="wav")
                if os.path.exists(wav_path):
                    conversion_ok = True
                    print(f"[Transcribe] pydub conversion OK → {wav_path}")
            except Exception as e:
                print(f"[Transcribe] pydub also failed: {e}")

        if not conversion_ok:
            raise HTTPException(
                status_code=500,
                detail="Audio conversion failed. Install ffmpeg: conda install -c conda-forge ffmpeg"
            )

        # Transcribe using speech_recognition
        import speech_recognition as sr
        recognizer = sr.Recognizer()

        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)

        # Map language codes to Google Speech Recognition language codes
        lang_map = {
            "en": "en-IN", "hi": "hi-IN", "mr": "mr-IN", "ta": "ta-IN",
            "te": "te-IN", "bn": "bn-IN", "kn": "kn-IN", "ml": "ml-IN",
            "gu": "gu-IN", "pa": "pa-IN",
        }
        lang_code = lang_map.get(req.language, "en-IN")

        text = recognizer.recognize_google(audio_data, language=lang_code)
        print(f"[Transcribe] Result ({lang_code}): {text[:100]}...")

        # Cleanup temp files
        try:
            os.unlink(tmp_path)
            os.unlink(wav_path)
        except:
            pass

        return {"text": text, "language": req.language}

    except HTTPException:
        raise
    except sr.UnknownValueError:
        return {"text": "", "language": req.language, "error": "Could not understand audio"}
    except sr.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Speech recognition service error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")



# ── Text Extraction (OCR/PDF) ────────────────────────────────────────────────

from fastapi import UploadFile, File, Form
import fitz # PyMuPDF

@app.post("/extract-text")
async def extract_text(file: UploadFile = File(...)):
    """
    Extract text from a document. Handles both native PDFs and scanned PDFs/Images via OCR.
    Uses PyMuPDF to render PDF pages and pytesseract for OCR.
    """
    import tempfile
    import pytesseract
    from PIL import Image
    import io

    print(f"[Extract] Processing file: {file.filename} ({file.content_type})")
    
    contents = await file.read()
    filename_lower = file.filename.lower()
    extracted_text = ""
    method = ""
    confidence_sum = 0
    pages_processed = 0

    try:
        # Determine file type
        is_pdf = filename_lower.endswith('.pdf') or file.content_type == 'application/pdf'
        is_image = any(filename_lower.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']) or (file.content_type and file.content_type.startswith('image/'))

        # Set tesseract command if on Windows and needed
        if os.name == 'nt':
            # Check common locations: conda env and system
            conda_tess = os.path.join(sys.prefix, 'Library', 'bin', 'tesseract.exe')
            sys_tess = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.path.exists(conda_tess):
                pytesseract.pytesseract.tesseract_cmd = conda_tess
            elif os.path.exists(sys_tess):
                pytesseract.pytesseract.tesseract_cmd = sys_tess

        if is_pdf:
            print("[Extract] Detected PDF, processing with PyMuPDF...")
            doc = fitz.open(stream=contents, filetype="pdf")
            pages_processed = len(doc)
            
            for page_num in range(pages_processed):
                page = doc.load_page(page_num)
                # Try native text first
                native_text = page.get_text()
                
                # If very little native text, it's likely a scanned page, fallback to OCR
                if len(native_text.strip()) < 50:
                    print(f"[Extract] Page {page_num+1} has little text, running OCR...")
                    # Render page to image
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 2x zoom for better OCR
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    
                    try:
                        # Attempt to get text and data (for confidence)
                        data = pytesseract.image_to_data(img, lang='eng+hin', output_type=pytesseract.Output.DICT)
                        text = pytesseract.image_to_string(img, lang='eng+hin')
                        
                        extracted_text += f"\n--- Page {page_num+1} ---\n{text}"
                        
                        # Calculate rough confidence
                        confs = [int(c) for c in data['conf'] if int(c) != -1]
                        if confs:
                            confidence_sum += sum(confs) / len(confs)
                            
                        method = "pdf-parse + OCR (Tesseract)"
                    except Exception as e:
                        print(f"[Extract] OCR failed on page {page_num+1}: {e}")
                        # Fallback to native even if sparse
                        extracted_text += f"\n--- Page {page_num+1} ---\n{native_text}"
                else:
                    extracted_text += f"\n--- Page {page_num+1} ---\n{native_text}"
                    method = "pdf-parse (Native)"
            
            # Average confidence
            if confidence_sum > 0:
                confidence_sum /= pages_processed
            
        elif is_image:
             print("[Extract] Detected image, processing with Tesseract OCR...")
             img = Image.open(io.BytesIO(contents))
             pages_processed = 1
             
             data = pytesseract.image_to_data(img, lang='eng+hin', output_type=pytesseract.Output.DICT)
             text = pytesseract.image_to_string(img, lang='eng+hin')
             
             extracted_text = text
             method = "image OCR (Tesseract)"
             
             confs = [int(c) for c in data['conf'] if int(c) != -1]
             if confs:
                 confidence_sum = sum(confs) / len(confs)
        else:
             # Try raw text extraction
             extracted_text = contents.decode('utf-8', errors='ignore')
             method = "raw text"
             pages_processed = 1

        print(f"[Extract] Done. Extracted {len(extracted_text)} chars.")
        return {
            "filename": file.filename,
            "text": extracted_text.strip() if extracted_text else "[No text could be extracted]",
            "method": method,
            "pages": pages_processed,
            "confidence": confidence_sum,
            "textLength": len(extracted_text)
        }

    except Exception as e:
        print(f"[Extract] Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    # Pre-load agent on startup so first request isn't slow
    print("[Server] Pre-loading agent...")
    get_agent()
    print("[Server] Starting FastAPI on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
