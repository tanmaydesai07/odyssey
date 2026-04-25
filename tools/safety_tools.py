from smolagents.tools import Tool
from tools.llm_utils import generate
import json


class SafetyGuardTool(Tool):
    name = "safety_guard"
    description = "Evaluates if user query contains harmful content, self-harm indicators, or requires immediate crisis intervention. Returns safety status and recommended actions."
    inputs = {
        "user_input": {"type": "string", "description": "User's input to evaluate"}
    }
    output_type = "string"

    def forward(self, user_input: str) -> str:
        safety_prompt = f"""Evaluate this user input for safety concerns:
        
{user_input}

Check for:
1. Self-harm or suicide indicators
2. Harm to others
3. Legal emergencies requiring immediate action
4. Sensitive topics requiring careful handling

Return JSON with:
- safe: boolean (true if no concerns)
- risk_level: "none", "low", "medium", "high"
- concerns: array of specific concerns
- recommended_action: what to do next"""
        return generate(safety_prompt, None)


class CrisisEscalatorTool(Tool):
    name = "crisis_escalator"
    description = "Detects crisis situations (domestic violence, immediate danger, child abuse, etc.) and provides emergency contacts, safe exit plans, or escalates to human support."
    inputs = {
        "situation_description": {"type": "string", "description": "Description of potential crisis"},
        "user_location": {"type": "string", "description": "User's state/city for local contacts", "nullable": True}
    }
    output_type = "string"

    def forward(self, situation_description: str, user_location: str = None) -> str:
        crisis_prompt = f"""Analyze this potential crisis situation and provide emergency assistance:
        
Situation: {situation_description}
Location: {user_location or "Not provided"}

Provide:
1. Risk assessment
2. Immediate safety steps
3. Relevant emergency contacts (police, women's helpline, child helpline, etc.)
4. Whether to escalate to human support
5. Resources for ongoing help"""
        return generate(crisis_prompt, None)


class DisclaimerEnforcerTool(Tool):
    name = "disclaimer_enforcer"
    description = "Ensures legal disclaimers are shown when needed - not legal advice, consult professionals, jurisdiction limitations."
    inputs = {
        "context": {"type": "string", "description": "Current conversation context"},
        "action": {"type": "string", "description": "Action: add, check, remove", "nullable": True}
    }
    output_type = "string"

    def forward(self, context: str, action: str = "check") -> str:
        return json.dumps({
            "disclaimer_needed": True,
            "disclaimer_text": "⚠️ IMPORTANT: This is not legal advice. For specific legal matters, please consult a qualified lawyer in your jurisdiction. This tool provides general information only.",
            "action_taken": action,
            "shown": action in ["add", "check"]
        })