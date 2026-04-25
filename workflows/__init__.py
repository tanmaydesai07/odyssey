# Legal Workflow Definitions
# Each workflow is a sequence of steps for different case types

WORKFLOWS = {
    "consumer_complaint": {
        "name": "Consumer Complaint",
        "steps": [
            {"id": 1, "name": "Intake Analysis", "description": "Understand user's complaint details"},
            {"id": 2, "name": "Jurisdiction Check", "description": "Determine correct consumer court"},
            {"id": 3, "name": "Document Collection", "description": "Gather bills, receipts, correspondence"},
            {"id": 4, "name": "Draft Complaint", "description": "Prepare consumer complaint petition"},
            {"id": 5, "name": "Filing", "description": "Submit to appropriate forum"},
        ]
    },
    "fir": {
        "name": "Police FIR",
        "steps": [
            {"id": 1, "name": "Intake Analysis", "description": "Understand incident details"},
            {"id": 2, "name": "Jurisdiction Check", "description": "Determine police station"},
            {"id": 3, "name": "Draft FIR", "description": "Prepare FIR application"},
            {"id": 4, "name": "Filing", "description": "Submit to police station"},
        ]
    },
    "rti": {
        "name": "RTI Application",
        "steps": [
            {"id": 1, "name": "Identify Authority", "description": "Find correct public authority"},
            {"id": 2, "name": "Draft Application", "description": "Prepare RTI query"},
            {"id": 3, "name": "Payment", "description": "Pay RTI fee"},
            {"id": 4, "name": "Filing", "description": "Submit application"},
        ]
    },
    "labour_complaint": {
        "name": "Labour Complaint",
        "steps": [
            {"id": 1, "name": "Intake Analysis", "description": "Understand labour dispute"},
            {"id": 2, "name": "Jurisdiction Check", "description": "Find labour commissioner"},
            {"id": 3, "name": "Document Collection", "description": "Gather employment documents"},
            {"id": 4, "name": "Draft Complaint", "description": "Prepare labour complaint"},
            {"id": 5, "name": "Filing", "description": "Submit to labour court"},
        ]
    },
}

def get_workflow(case_type: str):
    return WORKFLOWS.get(case_type, WORKFLOWS["consumer_complaint"])

def get_workflow_steps(case_type: str):
    workflow = get_workflow(case_type)
    return workflow.get("steps", [])