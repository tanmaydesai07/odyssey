"""
Advanced legal tools required by the problem statement.
All AI-powered via llm_utils.generate().

- ComplaintStrengthAnalyserTool
- EvidenceOrganiserTool
- HearingPreparationTool
- MultiDocumentSummariserTool
- EscalationRecommenderTool
- PIIScrubbingTool
"""
from smolagents.tools import Tool
from tools.llm_utils import generate
import json
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Complaint Strength Analyser
# ---------------------------------------------------------------------------

class ComplaintStrengthAnalyserTool(Tool):
    name = "complaint_strength_analyser"
    description = (
        "Before the user files anything, analyse how strong their case is. "
        "Tell them what evidence they have, what's missing, and how likely "
        "they are to succeed. Gives an honest assessment so they can prepare."
    )
    inputs = {
        "case_type": {
            "type": "string",
            "description": "Type of case: consumer_complaint | fir | rti | labour_complaint | civil_litigation",
        },
        "facts": {
            "type": "string",
            "description": "User's facts and evidence as plain text or JSON.",
        },
    }
    output_type = "string"

    def forward(self, case_type: str, facts: str) -> str:
        system = """You are a legal case strength analyst for Indian law.
Analyse the user's situation and give an honest assessment.

Return JSON:
{
  "strength_score": 0-10,
  "strength_label": "Strong / Moderate / Weak / Very Weak",
  "what_works_in_your_favour": ["..."],
  "what_weakens_your_case": ["..."],
  "critical_missing_evidence": ["..."],
  "recommended_actions_before_filing": ["..."],
  "realistic_outcome": "...",
  "time_sensitivity": "File immediately / Can wait / No urgency"
}
Be honest. Do not give false hope. Explain in plain language."""

        prompt = f"Case Type: {case_type}\n\nFacts and Evidence:\n{facts}"
        result = generate(prompt, system)
        try:
            return json.dumps(json.loads(result), ensure_ascii=False)
        except Exception:
            return json.dumps({"analysis": result}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Evidence Organiser
# ---------------------------------------------------------------------------

class EvidenceOrganiserTool(Tool):
    name = "evidence_organiser"
    description = (
        "Help the user catalogue and label their evidence "
        "(screenshots, receipts, messages, photos) in the format "
        "courts and authorities actually want. Tells them exactly "
        "how to organise, label, and present each piece of evidence."
    )
    inputs = {
        "case_type": {
            "type": "string",
            "description": "Type of case.",
        },
        "evidence_description": {
            "type": "string",
            "description": "User's description of what evidence they have.",
        },
    }
    output_type = "string"

    def forward(self, case_type: str, evidence_description: str) -> str:
        system = """You are a legal evidence organiser for Indian courts.
Help the user organise their evidence properly.

For each piece of evidence the user mentions, provide:
- What to label it (e.g. "Exhibit A — Purchase Receipt dated 15 Jan 2025")
- How many copies to make (original + certified copies)
- Whether it needs to be self-attested or notarised
- How to present it (physical printout / digital / both)
- Why this evidence matters legally

Also list any evidence they should try to obtain that they haven't mentioned.

Return JSON:
{
  "organised_evidence": [
    {
      "item": "...",
      "label": "Exhibit A — ...",
      "copies_needed": 3,
      "attestation": "self-attested / notarised / none",
      "format": "physical / digital / both",
      "legal_importance": "..."
    }
  ],
  "missing_evidence_to_obtain": ["..."],
  "evidence_checklist_summary": "..."
}"""

        prompt = f"Case Type: {case_type}\n\nEvidence the user has:\n{evidence_description}"
        result = generate(prompt, system)
        try:
            return json.dumps(json.loads(result), ensure_ascii=False)
        except Exception:
            return json.dumps({"guidance": result}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Hearing Preparation Guide
# ---------------------------------------------------------------------------

class HearingPreparationTool(Tool):
    name = "hearing_preparation"
    description = (
        "Once a complaint is filed, help the user prepare for their hearing. "
        "Tells them what to say, what documents to bring, what questions to expect, "
        "and how to present themselves."
    )
    inputs = {
        "case_type": {
            "type": "string",
            "description": "Type of case.",
        },
        "case_summary": {
            "type": "string",
            "description": "Brief summary of the case and what has been filed so far.",
        },
        "hearing_type": {
            "type": "string",
            "description": "Type of hearing: first_hearing | evidence_hearing | final_arguments | any",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, case_type: str, case_summary: str, hearing_type: str = "any") -> str:
        system = """You are a hearing preparation coach for Indian legal proceedings.
Help the user prepare for their upcoming hearing.

Return JSON:
{
  "what_to_bring": ["..."],
  "what_to_say": {
    "opening_statement": "...",
    "key_points_to_make": ["..."],
    "how_to_address_the_judge_or_officer": "..."
  },
  "questions_you_may_be_asked": [
    {"question": "...", "suggested_answer": "..."}
  ],
  "what_NOT_to_do": ["..."],
  "dress_code": "...",
  "arrive_time": "...",
  "if_you_dont_understand_something": "..."
}
Use plain language. The user is not a lawyer."""

        prompt = f"Case Type: {case_type}\nHearing Type: {hearing_type or 'any'}\n\nCase Summary:\n{case_summary}"
        result = generate(prompt, system)
        try:
            return json.dumps(json.loads(result), ensure_ascii=False)
        except Exception:
            return json.dumps({"guidance": result}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Multi-Document Summariser
# ---------------------------------------------------------------------------

class MultiDocumentSummariserTool(Tool):
    name = "multi_document_summariser"
    description = (
        "Upload or paste multiple legal documents (court notices, legal letters, "
        "agreements, orders) and get a plain-language summary of what they all "
        "mean together, what action is required, and by when."
    )
    inputs = {
        "documents_text": {
            "type": "string",
            "description": (
                "The text content of all documents, separated by '---DOCUMENT BREAK---'. "
                "Paste the full text of each document."
            ),
        },
        "user_question": {
            "type": "string",
            "description": "What the user wants to understand, e.g. 'What do I need to do?' or 'Am I in trouble?'",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, documents_text: str, user_question: str = None) -> str:
        system = """You are a legal document summariser for Indian citizens.
The user has provided one or more legal documents. Summarise them in plain language.

Return JSON:
{
  "document_count": 1,
  "overall_summary": "In simple words, what do these documents say together?",
  "documents": [
    {
      "document_number": 1,
      "type": "Court Notice / Legal Letter / Agreement / Order / etc.",
      "from": "...",
      "to": "...",
      "key_points": ["..."],
      "action_required": "...",
      "deadline": "... or null if none",
      "consequence_of_inaction": "..."
    }
  ],
  "immediate_actions": ["..."],
  "urgency": "Urgent (respond within days) / Normal / No action needed",
  "answer_to_user_question": "..."
}
Use plain language. Avoid legal jargon."""

        # Truncate if too long
        doc_text = documents_text[:6000]
        prompt = f"Documents:\n{doc_text}\n\nUser's question: {user_question or 'What do these documents mean and what should I do?'}"
        result = generate(prompt, system)
        try:
            return json.dumps(json.loads(result), ensure_ascii=False)
        except Exception:
            return json.dumps({"summary": result}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Escalation Recommender
# ---------------------------------------------------------------------------

class EscalationRecommenderTool(Tool):
    name = "escalation_recommender"
    description = (
        "If a complaint at one authority level has failed or been ignored, "
        "recommend the next authority to escalate to, the legal basis for escalating, "
        "and draft the escalation letter."
    )
    inputs = {
        "case_type": {
            "type": "string",
            "description": "Type of case.",
        },
        "current_situation": {
            "type": "string",
            "description": "What happened — e.g. 'Police refused to register FIR', 'Consumer forum not responding for 60 days', 'RTI not answered'.",
        },
        "steps_already_taken": {
            "type": "string",
            "description": "What the user has already tried.",
        },
        "jurisdiction": {
            "type": "string",
            "description": "State/city.",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, case_type: str, current_situation: str, steps_already_taken: str, jurisdiction: str = None) -> str:
        system = """You are a legal escalation expert for Indian law.
The user's complaint has been refused or ignored. Tell them exactly what to do next.

Return JSON:
{
  "escalation_options": [
    {
      "option_number": 1,
      "authority": "...",
      "legal_basis": "Section X of Act Y",
      "address_or_portal": "...",
      "how_to_file": "...",
      "timeline": "...",
      "cost": "...",
      "strength": "Strong / Moderate / Last resort"
    }
  ],
  "recommended_option": 1,
  "escalation_letter_draft": "Full text of escalation letter...",
  "important_note": "..."
}"""

        prompt = (
            f"Case Type: {case_type}\n"
            f"Jurisdiction: {jurisdiction or 'India'}\n"
            f"Current Situation: {current_situation}\n"
            f"Steps Already Taken: {steps_already_taken}"
        )
        result = generate(prompt, system)
        try:
            return json.dumps(json.loads(result), ensure_ascii=False)
        except Exception:
            return json.dumps({"guidance": result}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# PII Scrubbing Tool — privacy protection before storage
# ---------------------------------------------------------------------------

class PIIScrubbingTool(Tool):
    name = "pii_scrubber"
    description = (
        "Remove or mask personally identifiable information (PII) from text "
        "before storing in logs or session files. Protects user privacy. "
        "Call this before saving any user-provided text to disk."
    )
    inputs = {
        "text": {
            "type": "string",
            "description": "Text that may contain PII to be scrubbed.",
        },
        "mode": {
            "type": "string",
            "description": "Mode: mask (replace with ***) | redact (remove entirely) | tag (wrap in [PII:type])",
            "nullable": True,
        },
    }
    output_type = "string"

    # Regex patterns for common Indian PII
    _PATTERNS = [
        (r"\b[6-9]\d{9}\b", "PHONE"),                          # Indian mobile numbers
        (r"\b\d{4}\s?\d{4}\s?\d{4}\b", "AADHAAR"),            # Aadhaar
        (r"\b[A-Z]{5}\d{4}[A-Z]\b", "PAN"),                   # PAN card
        (r"\b[A-Z]\d{7}\b", "PASSPORT"),                       # Passport
        (r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", "EMAIL"),           # Email
        (r"\b\d{6}\b", "PINCODE"),                             # PIN code (6 digits)
    ]

    def forward(self, text: str, mode: str = "mask") -> str:
        mode = (mode or "mask").lower()
        scrubbed = text
        found_pii = []

        for pattern, pii_type in self._PATTERNS:
            matches = re.findall(pattern, scrubbed)
            if matches:
                found_pii.append({"type": pii_type, "count": len(matches)})
                if mode == "mask":
                    scrubbed = re.sub(pattern, f"[{pii_type}:***]", scrubbed)
                elif mode == "redact":
                    scrubbed = re.sub(pattern, "", scrubbed)
                elif mode == "tag":
                    scrubbed = re.sub(pattern, lambda m: f"[PII:{pii_type}:{m.group()[:3]}***]", scrubbed)

        return json.dumps({
            "scrubbed_text": scrubbed,
            "pii_found": found_pii,
            "pii_removed": len(found_pii) > 0,
        }, ensure_ascii=False)
