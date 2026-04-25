from smolagents.tools import Tool
from tools.llm_utils import generate, SYSTEM_PROMPTS


class JurisdictionResolverTool(Tool):
    name = "jurisdiction_resolver"
    description = "Resolves the appropriate jurisdiction (state, city, authority) for the user's legal matter based on location, case type, and matter specifics."
    inputs = {
        "state": {"type": "string", "description": "State name (e.g., Delhi, Maharashtra, Karnataka)"},
        "city": {"type": "string", "description": "City name (e.g., Mumbai, Bangalore)"},
        "case_type": {"type": "string", "description": "Type of legal matter"},
        "amount_in_dispute": {"type": "number", "description": "Amount in rupees (if applicable)", "nullable": True}
    }
    output_type = "string"

    def forward(self, state: str, city: str, case_type: str, amount_in_dispute: float = None) -> str:
        prompt = f"State: {state}\nCity: {city}\nCase Type: {case_type}\nAmount in Dispute: {amount_in_dispute}"
        return generate(prompt, SYSTEM_PROMPTS["jurisdiction_resolver"])