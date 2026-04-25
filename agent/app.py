"""
AI-Powered Legal Assistance Platform - Main Agent
Problem: Walk users through filing FIRs, raising complaints, understanding rights.
Multi-step workflows, situational understanding, explain-why, regional language support.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows encoding issues - MUST be before any other imports
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Load .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

os.environ["TOKENIZERS_PARALLELISM"] = "0"

from smolagents import CodeAgent, tool

# Import tools
from tools.final_answer import FinalAnswerTool
from tools.case_classifier import CaseClassifierTool
from tools.jurisdiction_resolver import JurisdictionResolverTool
from tools.intake_analyzer import IntakeAnalyzerTool, WorkflowPlannerTool
from tools.legal_retriever import LegalRetrieverTool, SourceCitationTool

# Import remaining tools from separate files
from tools.document_tools import DraftGeneratorTool, DraftEditorTool, DocumentExporterTool, AuthorityFinderTool, ChecklistGeneratorTool
from tools.safety_tools import SafetyGuardTool, CrisisEscalatorTool, DisclaimerEnforcerTool
from tools.translation_tools import TranslatorTool, LegalTermGlossaryTool, LanguageDetectorTool
from tools.audit_tools import AuditLoggerTool, SessionManagerTool, CaseDashboardTool, WorkflowProgressTool, AnalyticsReporterTool
from tools.web_tools import WebSearchTool, VisitWebpageTool
from tools.advanced_tools import (
    ComplaintStrengthAnalyserTool,
    EvidenceOrganiserTool,
    HearingPreparationTool,
    MultiDocumentSummariserTool,
    EscalationRecommenderTool,
    PIIScrubbingTool,
)

# Import custom streaming UI
from ui.gradio_ui import GradioUI


@tool
def get_current_time_in_timezone(timezone: str) -> str:
    """Get the current local time in a specified timezone.
    
    Args:
        timezone: A string representing a valid timezone (e.g., 'Asia/Kolkata', 'America/New_York').
    """
    import datetime
    import pytz
    try:
        tz = pytz.timezone(timezone)
        local_time = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        return f"The current local time in {timezone} is: {local_time}"
    except Exception as e:
        return f"Error fetching time for timezone '{timezone}': {str(e)}"


final_answer = FinalAnswerTool()

# Use OpenCode Zen's Big Pickle model — free, fast, optimized for coding agents
from zen_model import ZenModel

model = ZenModel(
    model_id="big-pickle",
    max_tokens=8192,
    temperature=0.3,
)

print(f"[Agent] Using model: {model.model_id}")


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
- Always include a disclaimer that this is informational guidance, not legal advice.
- If user asks about escalation (police refused, no response, etc.) use escalation_recommender.
- If user wants to analyse case strength, use complaint_strength_analyser.
- If user wants to organise evidence, use evidence_organiser.
- If user wants hearing prep, use hearing_preparation.
- If user pastes documents, use multi_document_summariser."""

agent = CodeAgent(
    model=model,
    tools=[
        final_answer,
        get_current_time_in_timezone,
        WebSearchTool(),
        VisitWebpageTool(),
        CaseClassifierTool(),
        JurisdictionResolverTool(),
        IntakeAnalyzerTool(),
        WorkflowPlannerTool(),
        LegalRetrieverTool(),
        SourceCitationTool(),
        DraftGeneratorTool(),
        DraftEditorTool(),
        DocumentExporterTool(),
        AuthorityFinderTool(),
        ChecklistGeneratorTool(),
        SafetyGuardTool(),
        CrisisEscalatorTool(),
        DisclaimerEnforcerTool(),
        TranslatorTool(),
        LegalTermGlossaryTool(),
        LanguageDetectorTool(),
        AuditLoggerTool(),
        SessionManagerTool(),
        CaseDashboardTool(),
        WorkflowProgressTool(),
        AnalyticsReporterTool(),
        ComplaintStrengthAnalyserTool(),
        EvidenceOrganiserTool(),
        HearingPreparationTool(),
        MultiDocumentSummariserTool(),
        EscalationRecommenderTool(),
        PIIScrubbingTool(),
    ],
    max_steps=12,
    verbosity_level=2,
    planning_interval=4,
    name="legal_assistant",
    description=SYSTEM_PROMPT,
    # Increase executor timeout — LLM tool calls (checklist, draft) can take >30s
    executor_timeout=120,
)


if __name__ == "__main__":
    # Use smolagents built-in GradioUI — it streams the agent's thought 
    # process (steps, tool calls, plans) in real-time to the chatbot
    GradioUI(agent).launch(share=False)