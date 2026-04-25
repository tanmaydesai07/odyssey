"""
Translation and legal glossary tools.
Both are AI-powered — no hardcoded word lists or echo stubs.
"""
from smolagents.tools import Tool
from tools.llm_utils import generate
import json


_LANG_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "kn": "Kannada",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "or": "Odia",
    "as": "Assamese",
}


# ---------------------------------------------------------------------------
# 6. Translator — AI-powered, legal-term-aware
# ---------------------------------------------------------------------------

class TranslatorTool(Tool):
    name = "translator"
    description = (
        "Translate text between English and any Indian regional language "
        "(Hindi, Marathi, Tamil, Telugu, Bengali, Kannada, Malayalam, Gujarati, etc.). "
        "Preserves legal terminology accurately — does not mistranslate procedural terms."
    )
    inputs = {
        "text": {
            "type": "string",
            "description": "The text to translate.",
        },
        "source_language": {
            "type": "string",
            "description": "Source language code: en | hi | mr | ta | te | bn | kn | ml | gu",
            "nullable": True,
        },
        "target_language": {
            "type": "string",
            "description": "Target language code: en | hi | mr | ta | te | bn | kn | ml | gu",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, text: str, source_language: str = "en", target_language: str = "hi") -> str:
        src = source_language or "en"
        tgt = target_language or "hi"
        src_name = _LANG_NAMES.get(src, src)
        tgt_name = _LANG_NAMES.get(tgt, tgt)

        system = f"""You are a professional legal translator specialising in Indian law documents.
Translate from {src_name} to {tgt_name}.

Rules:
- Preserve all legal section references exactly as-is (e.g. "Section 35 CPA 2019", "IPC 420", "RTI Act 2005").
- Keep proper nouns (names, place names, authority names) unchanged.
- Use the standard legal terminology used in Indian courts for {tgt_name}.
- Do NOT paraphrase — translate faithfully.
- Return a JSON object with keys: original_text, translated_text, source_lang, target_lang, legal_terms_preserved (list of terms kept unchanged)."""

        prompt = f"Translate the following text:\n\n{text}"
        result = generate(prompt, system)

        # Try to parse as JSON; if the model returned plain text, wrap it
        try:
            parsed = json.loads(result)
            return json.dumps(parsed, ensure_ascii=False)
        except Exception:
            return json.dumps({
                "original_text": text,
                "translated_text": result,
                "source_lang": src,
                "target_lang": tgt,
                "legal_terms_preserved": [],
            }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 7. Legal Term Glossary — AI-powered, covers all Indian legal terms
# ---------------------------------------------------------------------------

class LegalTermGlossaryTool(Tool):
    name = "legal_term_glossary"
    description = (
        "Look up any Indian legal term and get its plain-language definition, "
        "its usage in Indian law, and its equivalent in a regional language. "
        "Covers IPC, CrPC, BNS, CPA, RTI, labour laws, civil procedure, and more."
    )
    inputs = {
        "term": {
            "type": "string",
            "description": "The legal term to look up, e.g. 'FIR', 'cognizable offence', 'ex-parte', 'mandamus'.",
        },
        "language": {
            "type": "string",
            "description": "Language for the explanation: en | hi | mr | ta | te | bn | kn | ml | gu",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, term: str, language: str = "en") -> str:
        lang = language or "en"
        lang_name = _LANG_NAMES.get(lang, lang)

        system = """You are a legal terminology expert for Indian law.
For the given legal term, provide:
1. Plain-language definition (what it means in simple words)
2. Which law/act it comes from
3. How it is used in practice (example scenario)
4. The equivalent term in the requested language (if not English)
5. Common misconceptions about this term (if any)

Return a JSON object with keys: term, definition, source_law, practical_example, regional_equivalent, language, misconceptions."""

        prompt = f"Legal term: {term}\nExplain in: {lang_name}"
        result = generate(prompt, system)

        try:
            parsed = json.loads(result)
            return json.dumps(parsed, ensure_ascii=False)
        except Exception:
            return json.dumps({
                "term": term,
                "definition": result,
                "language": lang,
            }, ensure_ascii=False)
