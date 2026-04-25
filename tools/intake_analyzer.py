from smolagents.tools import Tool
from tools.llm_utils import generate, SYSTEM_PROMPTS


class IntakeAnalyzerTool(Tool):
    name = "intake_analyzer"
    description = (
        "Analyzes user input to extract case facts AND identifies what critical information "
        "is still missing. Returns extracted facts plus a list of follow-up questions to ask "
        "the user before proceeding. Always call this FIRST before case_classifier."
    )
    inputs = {
        "user_input": {"type": "string", "description": "User's description in plain language"},
        "case_type": {"type": "string", "description": "Identified case type (use 'unknown' if not yet classified)", "nullable": True}
    }
    output_type = "string"

    def forward(self, user_input: str, case_type: str = "unknown") -> str:
        prompt = f"User Input: {user_input}\nCase Type: {case_type or 'unknown'}"
        return generate(prompt, SYSTEM_PROMPTS["intake_analyzer"])


class WorkflowPlannerTool(Tool):
    name = "workflow_planner"
    description = (
        "Plans the complete step-by-step legal workflow including: "
        "sequenced steps with rationale, prerequisites, expected timelines, "
        "AND escalation paths if the authority refuses or delays. "
        "Always include what to do if step fails."
    )
    inputs = {
        "case_type": {"type": "string", "description": "Classified case type"},
        "jurisdiction": {"type": "string", "description": "Resolved jurisdiction"},
        "extracted_facts": {"type": "string", "description": "Extracted user facts as JSON string"}
    }
    output_type = "string"

    def forward(self, case_type: str, jurisdiction: str, extracted_facts: str) -> str:
        prompt = f"Case Type: {case_type}\nJurisdiction: {jurisdiction}\nExtracted Facts: {extracted_facts}"
        return generate(prompt, SYSTEM_PROMPTS["workflow_planner"])