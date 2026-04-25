from smolagents.tools import Tool
from tools.llm_utils import generate, SYSTEM_PROMPTS
import json


class DraftGeneratorTool(Tool):
    name = "draft_generator"
    description = "Generates draft document (FIR, complaint, RTI, labour complaint) from structured user facts."
    inputs = {
        "template_type": {"type": "string", "description": "Type: fir, consumer_complaint, rti, labour_complaint"},
        "extracted_facts": {"type": "string", "description": "User facts as JSON string"},
        "language": {"type": "string", "description": "Output language", "nullable": True}
    }
    output_type = "string"

    def forward(self, template_type: str, extracted_facts: str, language: str = "en") -> str:
        prompt = f"Template Type: {template_type}\nExtracted Facts: {extracted_facts}\nLanguage: {language}"
        return generate(prompt, SYSTEM_PROMPTS["draft_generator"])


class DraftEditorTool(Tool):
    name = "draft_editor"
    description = "Allows user to edit draft, preserves changes, regenerates clean final version."
    inputs = {
        "draft_id": {"type": "string", "description": "ID of draft to edit"},
        "user_edits": {"type": "string", "description": "User's edited content", "nullable": True},
        "regenerate": {"type": "boolean", "description": "Regenerate clean version after edits", "nullable": True}
    }
    output_type = "string"

    def forward(self, draft_id: str, user_edits: str = None, regenerate: bool = False) -> str:
        prompt = f"Draft ID: {draft_id}\nUser Edits: {user_edits}\nRegenerate: {regenerate}"
        return generate(prompt, "Edit and clean up the user's draft changes. Return updated draft.")


class DocumentExporterTool(Tool):
    name = "document_exporter"
    description = "Exports document to PDF, DOCX, or printable format."
    inputs = {
        "draft_id": {"type": "string", "description": "ID of draft to export"},
        "format": {"type": "string", "description": "Output format: pdf, docx, txt", "nullable": True}
    }
    output_type = "string"

    def forward(self, draft_id: str, format: str = "pdf") -> str:
        return json.dumps({
            "message": f"Draft {draft_id} ready for export in {format} format",
            "download_ready": True,
            "note": "Export feature coming soon - currently showing draft text for copy/paste"
        })


class AuthorityFinderTool(Tool):
    name = "authority_finder"
    description = "Finds relevant authority office, portal, or helpline with contact details."
    inputs = {
        "authority_type": {"type": "string", "description": "Type: police, consumer_court, labour_commission, etc."},
        "jurisdiction": {"type": "string", "description": "State/city"}
    }
    output_type = "string"

    def forward(self, authority_type: str, jurisdiction: str) -> str:
        prompt = f"Authority Type: {authority_type}\nJurisdiction: {jurisdiction}"
        return generate(prompt, SYSTEM_PROMPTS["authority_finder"])


class ChecklistGeneratorTool(Tool):
    name = "checklist_generator"
    description = "Generates checklist of required documents, IDs, fees, annexures for submission."
    inputs = {
        "workflow_step": {"type": "string", "description": "Current workflow step"},
        "case_type": {"type": "string", "description": "Case type"}
    }
    output_type = "string"

    def forward(self, workflow_step: str, case_type: str) -> str:
        prompt = f"Workflow Step: {workflow_step}\nCase Type: {case_type}"
        return generate(prompt, SYSTEM_PROMPTS["checklist_generator"])