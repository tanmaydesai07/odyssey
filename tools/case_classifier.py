from smolagents.tools import Tool
from tools.llm_utils import generate, SYSTEM_PROMPTS


class CaseClassifierTool(Tool):
    name = "case_classifier"
    description = "Classifies the user's legal matter into appropriate category: criminal, consumer, labour, civil, property, RTI, cyber, or other. Identifies likely matter type and confidence score."
    inputs = {
        "situation_description": {
            "type": "string",
            "description": "Plain language description of what happened: who, what, when, where, why, desired outcome"
        }
    }
    output_type = "string"

    def forward(self, situation_description: str) -> str:
        return generate(situation_description, SYSTEM_PROMPTS["case_classifier"])