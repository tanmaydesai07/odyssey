from smolagents.tools import Tool
from tools.llm_utils import generate
import json


class TranslatorTool(Tool):
    name = "translator"
    description = "Translates text between English and Indian regional languages (Hindi, Tamil, Telugu, Bengali, Marathi, Kannada, Malayalam, Gujarati)."
    inputs = {
        "text": {"type": "string", "description": "Text to translate"},
        "source_language": {"type": "string", "description": "Source language code: en, hi, ta, te, bn, mr, kn, ml, gu", "nullable": True},
        "target_language": {"type": "string", "description": "Target language code: en, hi, ta, te, bn, mr, kn, ml, gu", "nullable": True}
    }
    output_type = "string"

    def forward(self, text: str, source_language: str = "en", target_language: str = "hi") -> str:
        prompt = f"Translate the following from {source_language} to {target_language}:\n\n{text}"
        
        lang_names = {
            "en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
            "bn": "Bengali", "mr": "Marathi", "kn": "Kannada", "ml": "Malayalam", "gu": "Gujarati"
        }
        
        system = f"You are a translator. Translate accurately to {lang_names.get(target_language, target_language)}. Return JSON with original_text, translated_text, source_lang, target_lang."
        return generate(prompt, system)


class LegalTermGlossaryTool(Tool):
    name = "legal_term_glossary"
    description = "Returns consistent legal terminology across languages. Ensures accurate translation of procedural terms."
    inputs = {
        "term": {"type": "string", "description": "Legal term to look up"},
        "language": {"type": "string", "description": "Target language", "nullable": True}
    }
    output_type = "string"

    def forward(self, term: str, language: str = "en") -> str:
        prompt = f"Explain legal term '{term}' in {language}"
        return generate(prompt, "Provide definition, usage in legal context, and equivalent terms in Indian law. Return JSON.")