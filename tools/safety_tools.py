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
    description = "Generates a context-aware legal disclaimer. Call this before delivering any legal guidance to ensure the user understands this is process information, not legal advice."
    inputs = {
        "context": {"type": "string", "description": "Current conversation context — what topic or advice is being given"},
        "action": {"type": "string", "description": "Action: add, check, remove", "nullable": True}
    }
    output_type = "string"

    def forward(self, context: str, action: str = "check") -> str:
        system = (
            "You are a legal disclaimer generator for an Indian legal assistance platform. "
            "Generate a short, plain-language disclaimer (2-3 sentences) tailored to the context. "
            "It must: (1) state this is process/informational guidance only, not legal advice, "
            "(2) recommend consulting a qualified advocate for the specific matter, "
            "(3) mention that laws and procedures may vary by state. "
            "Return JSON with keys: disclaimer_needed (bool), disclaimer_text (string)."
        )
        result = generate(f"Context: {context}", system)
        try:
            parsed = json.loads(result)
            parsed["action_taken"] = action
            return json.dumps(parsed)
        except Exception:
            return json.dumps({
                "disclaimer_needed": True,
                "disclaimer_text": result,
                "action_taken": action,
            })