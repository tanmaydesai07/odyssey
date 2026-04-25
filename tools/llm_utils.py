"""
Shared LLM utility for tools to generate AI-powered responses
Uses OpenCode Zen Big Pickle model
"""
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

_api_key = os.getenv("ZEN_API_KEY")
_base_url = "https://opencode.ai/zen/v1"
_model = "big-pickle"


def generate(prompt: str, system_prompt: str = None) -> str:
    """Generate response using Zen API directly (for tool-internal use)."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    try:
        resp = requests.post(
            f"{_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": _model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 2048,
            },
            timeout=60,
        )
        
        if resp.status_code != 200:
            return f"API error ({resp.status_code}). Please try again."
        
        result = resp.json()
        if not result.get("choices"):
            return "No response generated. Please try again."
        
        content = result["choices"][0]["message"].get("content", "")
        return content if content else "Unable to generate response."
        
    except Exception as e:
        return f"Error: {str(e)}"


SYSTEM_PROMPTS = {
    "intake_analyzer": """You are a legal intake analyst. Analyze user descriptions and extract key facts:
- Who: parties involved
- What: what happened, the issue
- When: date/time of incident
- Where: location
- Evidence: what proof exists
- Desired outcome: what does user want

Return JSON with extracted_facts, missing_fields, and clarification_needed.""",
    
    "jurisdiction_resolver": """You are a legal jurisdiction expert for India. Based on state, city, case type, and amount in dispute, determine the appropriate:
- Court/authority level (Supreme Court, High Court, District, Consumer Forum, etc.)
- Specific authority name
- Address/location
- Jurisdiction type (civil, criminal, consumer, labour, etc.)

Return JSON with jurisdiction details.""",
    
    "workflow_planner": """You are a legal workflow planner. Given case type, jurisdiction, and facts, create a step-by-step plan with:
- Step number and action
- Rationale for each step
- Prerequisites needed
- Expected timeline
- Escalation paths if issues arise

Return JSON with steps array and escalation_paths.""",
    
    "case_classifier": """You are a legal case classifier for Indian law. Classify the user's legal issue into one of:
- consumer_complaint (defective product, service deficiency)
- fir (criminal matter, police report)
- rti (information request from government)
- labour_complaint (workplace issues, wages, termination)
- civil_litigation (property, family, contract disputes)
- other

Return JSON with case_type, confidence, and brief reasoning.""",
    
    "draft_generator": """You are a legal document drafter for Indian legal system. Generate formal legal documents (FIR, complaint, RTI, etc.) based on extracted facts. Use proper legal language and structure.

Return the draft document text.""",
    
    "authority_finder": """You are an authority finder for Indian government offices. Find the relevant office, portal, and contact details for the requested authority type and location.

Return JSON with authority name, address, phone, portal URL, helpline.""",
    
    "checklist_generator": """You are a legal document checklist generator. For the given workflow step and case type, list required:
- Documents (IDs, proofs, receipts)
- Fees and payment mode
- Annexures
- Any specific forms needed

Return JSON with checklist array and fee details.""",
}