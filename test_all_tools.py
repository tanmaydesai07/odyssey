# -*- coding: utf-8 -*-
"""Test all AI tools to verify they work end-to-end."""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent', 'tools'))

results = {}

def test(name, fn):
    print(f"\n{'='*60}")
    print(f"TESTING: {name}")
    print('='*60)
    start = time.time()
    try:
        result = fn()
        elapsed = round(time.time() - start, 1)
        # Check if result is non-empty
        if result and len(str(result)) > 10:
            results[name] = "PASS"
            print(f"  PASS ({elapsed}s) - {str(result)[:200]}")
        else:
            results[name] = "EMPTY"
            print(f"  EMPTY ({elapsed}s) - Got: {result}")
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        results[name] = f"FAIL: {e}"
        print(f"  FAIL ({elapsed}s) - {e}")

# 1. Case Classifier
def t_case_classifier():
    from tools.case_classifier import CaseClassifierTool
    t = CaseClassifierTool()
    return t.forward(user_input="My landlord won't return my deposit in Mumbai")
test("1. Case Classifier", t_case_classifier)

# 2. Jurisdiction Resolver
def t_jurisdiction():
    from tools.jurisdiction_resolver import JurisdictionResolverTool
    t = JurisdictionResolverTool()
    return t.forward(case_type="consumer_complaint", user_location="Mumbai, Maharashtra")
test("2. Jurisdiction Resolver", t_jurisdiction)

# 3. Intake Analyzer
def t_intake():
    from tools.intake_analyzer import IntakeAnalyzerTool
    t = IntakeAnalyzerTool()
    return t.forward(user_input="Bought defective laptop from Flipkart for 65000 in Mumbai, refused refund")
test("3. Intake Analyzer", t_intake)

# 4. Workflow Planner
def t_workflow():
    from tools.intake_analyzer import WorkflowPlannerTool
    t = WorkflowPlannerTool()
    return t.forward(case_type="consumer_complaint", jurisdiction="Maharashtra, Mumbai", extracted_facts='{"item":"laptop","amount":65000}')
test("4. Workflow Planner", t_workflow)

# 5. Legal Retriever (RAG)
def t_legal_retriever():
    from tools.legal_retriever import LegalRetrieverTool
    t = LegalRetrieverTool()
    return t.forward(query="consumer complaint filing process", case_type="consumer_complaint")
test("5. Legal Retriever (RAG)", t_legal_retriever)

# 6. Draft Generator
def t_draft_gen():
    from tools.document_tools import DraftGeneratorTool
    t = DraftGeneratorTool()
    return t.forward(template_type="consumer_complaint", extracted_facts='Name: Test User, Item: Laptop, Amount: 65000, Seller: Flipkart, City: Mumbai, Date: 1 Jan 2025')
test("6. Draft Generator", t_draft_gen)

# 7. Document Exporter (PDF)
def t_doc_export_pdf():
    from tools.document_tools import DraftGeneratorTool, DocumentExporterTool, _load_draft
    from pathlib import Path
    # Find the draft we just created
    drafts_dir = Path(__file__).parent / "agent" / "drafts"
    draft_files = sorted(drafts_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not draft_files:
        return "No drafts found"
    draft_id = draft_files[0].stem
    # Export as PDF
    from tools.document_exporter_new import export_pdf, get_session_exports_dir
    draft = _load_draft(draft_id)
    exports = get_session_exports_dir("test_session")
    out = exports / f"test_{draft_id}.pdf"
    export_pdf(draft["draft_text"], out, title="Test Consumer Complaint")
    return f"PDF created: {out} ({out.stat().st_size} bytes)"
test("7. Document Exporter (PDF)", t_doc_export_pdf)

# 8. Document Exporter (DOCX)
def t_doc_export_docx():
    from tools.document_tools import _load_draft
    from pathlib import Path
    drafts_dir = Path(__file__).parent / "agent" / "drafts"
    draft_files = sorted(drafts_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not draft_files:
        return "No drafts found"
    draft_id = draft_files[0].stem
    from tools.document_exporter_new import export_docx, get_session_exports_dir
    draft = _load_draft(draft_id)
    exports = get_session_exports_dir("test_session")
    out = exports / f"test_{draft_id}.docx"
    export_docx(draft["draft_text"], out, title="Test Consumer Complaint")
    return f"DOCX created: {out} ({out.stat().st_size} bytes)"
test("8. Document Exporter (DOCX)", t_doc_export_docx)

# 9. Complaint Strength Analyser
def t_strength():
    from tools.advanced_tools import ComplaintStrengthAnalyserTool
    t = ComplaintStrengthAnalyserTool()
    return t.forward(case_type="consumer_complaint", facts="Bought laptop 65000 from Flipkart, stopped working in 2 weeks, they refused refund. Have invoice and emails.")
test("9. Complaint Strength Analyser", t_strength)

# 10. Evidence Organiser
def t_evidence():
    from tools.advanced_tools import EvidenceOrganiserTool
    t = EvidenceOrganiserTool()
    return t.forward(case_type="consumer_complaint", evidence_description="I have the Flipkart invoice, bank statement showing payment, screenshots of chat with customer care, and photos of the defective laptop screen")
test("10. Evidence Organiser", t_evidence)

# 11. Hearing Preparation
def t_hearing():
    from tools.advanced_tools import HearingPreparationTool
    t = HearingPreparationTool()
    return t.forward(case_type="consumer_complaint", case_summary="Filed consumer complaint against Flipkart for defective laptop worth 65000. First hearing scheduled.", hearing_type="first_hearing")
test("11. Hearing Preparation", t_hearing)

# 12. Multi-Document Summariser
def t_multi_doc():
    from tools.advanced_tools import MultiDocumentSummariserTool
    t = MultiDocumentSummariserTool()
    docs = """NOTICE: You are hereby informed that complaint no. CC/123/2025 has been registered against Flipkart. 
The first hearing is scheduled for 15 March 2025 at District Consumer Forum, Mumbai.
---DOCUMENT BREAK---
RECEIPT: Filing fee of Rs 500 paid via demand draft no. DD789456. Case registered under Consumer Protection Act 2019."""
    return t.forward(documents_text=docs, user_question="What do I need to do next?")
test("12. Multi-Document Summariser", t_multi_doc)

# 13. Escalation Recommender
def t_escalation():
    from tools.advanced_tools import EscalationRecommenderTool
    t = EscalationRecommenderTool()
    return t.forward(case_type="consumer_complaint", current_situation="District forum dismissed my case saying insufficient evidence", steps_already_taken="Filed complaint at district forum, attended 2 hearings", jurisdiction="Mumbai, Maharashtra")
test("13. Escalation Recommender", t_escalation)

# 14. Translator
def t_translator():
    from tools.translation_tools import TranslatorTool
    t = TranslatorTool()
    return t.forward(text="You have the right to file a consumer complaint within 2 years of purchase.", source_language="en", target_language="hi")
test("14. Translator (EN->HI)", t_translator)

# 15. Legal Term Glossary
def t_glossary():
    from tools.translation_tools import LegalTermGlossaryTool
    t = LegalTermGlossaryTool()
    return t.forward(term="FIR", language="en")
test("15. Legal Term Glossary", t_glossary)

# 16. Language Detector
def t_lang_detect():
    from tools.translation_tools import LanguageDetectorTool
    t = LanguageDetectorTool()
    return t.forward(text="mera makan malik mera deposit wapas nahi kar raha")
test("16. Language Detector", t_lang_detect)

# 17. Safety Guard
def t_safety():
    from tools.safety_tools import SafetyGuardTool
    t = SafetyGuardTool()
    return t.forward(user_input="My employer is threatening me and I feel unsafe at work")
test("17. Safety Guard", t_safety)

# 18. PII Scrubber
def t_pii():
    from tools.advanced_tools import PIIScrubbingTool
    t = PIIScrubbingTool()
    return t.forward(text="My name is Rahul, phone 9876543210, Aadhaar 1234 5678 9012, PAN ABCDE1234F, email rahul@test.com", mode="mask")
test("18. PII Scrubber", t_pii)

# 19. Authority Finder
def t_authority():
    from tools.document_tools import AuthorityFinderTool
    t = AuthorityFinderTool()
    return t.forward(authority_type="consumer_court", jurisdiction="Mumbai, Maharashtra")
test("19. Authority Finder", t_authority)

# 20. Checklist Generator
def t_checklist():
    from tools.document_tools import ChecklistGeneratorTool
    t = ChecklistGeneratorTool()
    return t.forward(workflow_step="filing consumer complaint at district forum", case_type="consumer_complaint", jurisdiction="Mumbai")
test("20. Checklist Generator", t_checklist)

# ── SUMMARY ──
print("\n\n" + "="*60)
print("FINAL RESULTS")
print("="*60)
passed = sum(1 for v in results.values() if v == "PASS")
failed = sum(1 for v in results.values() if v.startswith("FAIL"))
empty = sum(1 for v in results.values() if v == "EMPTY")
for name, status in results.items():
    icon = "✓" if status == "PASS" else ("✗" if status.startswith("FAIL") else "⚠")
    print(f"  {icon} {name}: {status}")
print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed} | Empty: {empty}")
