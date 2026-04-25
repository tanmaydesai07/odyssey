from smolagents.tools import Tool
from tools.llm_utils import generate, SYSTEM_PROMPTS


class IntakeAnalyzerTool(Tool):
    name = "intake_analyzer"
    description = "Analyzes user-provided facts, extracts key information (who, what, when, where, evidence, outcome), and identifies missing required fields for the legal workflow."
    inputs = {
        "user_input": {"type": "string", "description": "User's description in plain language"},
        "case_type": {"type": "string", "description": "Identified case type"}
    }
    output_type = "string"

    def forward(self, user_input: str, case_type: str) -> str:
        prompt = f"User Input: {user_input}\nCase Type: {case_type}"
        return generate(prompt, SYSTEM_PROMPTS["intake_analyzer"])


class WorkflowPlannerTool(Tool):
    name = "workflow_planner"
    description = "Plans the next steps in the legal workflow with rationale, prerequisites, expected timeline, and escalation paths."
    inputs = {
        "case_type": {"type": "string", "description": "Classified case type"},
        "jurisdiction": {"type": "string", "description": "Resolved jurisdiction"},
        "extracted_facts": {"type": "string", "description": "Extracted user facts as JSON string"}
    }
    output_type = "string"

    def forward(self, case_type: str, jurisdiction: str, extracted_facts: str) -> str:
        prompt = f"Case Type: {case_type}\nJurisdiction: {jurisdiction}\nExtracted Facts: {extracted_facts}"
        return generate(prompt, SYSTEM_PROMPTS["workflow_planner"])