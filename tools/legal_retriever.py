"""
Legal Retriever Tool - Integrated with ChromaDB RAG
Uses existing legal_rag_corpus at rag_v2/processed/chroma_db
"""

from smolagents.tools import Tool
import json
import os
from pathlib import Path

# Path to chroma_db - local agent folder first (for HF Spaces), then original location
BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_PATHS = [
    BASE_DIR / "chroma_db",
    BASE_DIR / "rag_v2" / "processed" / "chroma_db",
    Path("C:/Users/uday0/OneDrive/Desktop/code/odyssey/rag_v2/processed/chroma_db"),
]

CHROMA_DIR = None
for p in CHROMA_PATHS:
    if p.exists():
        CHROMA_DIR = p
        break

if CHROMA_DIR is None:
    CHROMA_DIR = CHROMA_PATHS[0]

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "legal_rag"


class LegalRetrieverTool(Tool):
    name = "legal_retriever"
    description = "Retrieves relevant legal information from the curated legal corpus. Use this to answer questions about legal procedures, laws, and workflows. Returns ranked results with source citations."
    inputs = {
        "query": {"type": "string", "description": "Search query about legal procedure or law"},
        "case_type": {"type": "string", "description": "Case type for context filtering", "nullable": True},
        "jurisdiction": {"type": "string", "description": "Jurisdiction for filtering", "nullable": True},
        "top_k": {"type": "number", "description": "Number of results to return", "nullable": True}
    }
    output_type = "string"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = None
        self._collection = None
        self._model = None

    def _get_client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        return self._client

    def _get_collection(self):
        if self._collection is None:
            self._collection = self._get_client().get_collection(COLLECTION_NAME)
        return self._collection

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model

    def forward(self, query: str, case_type: str = None, jurisdiction: str = None, top_k: int = 5) -> str:
        try:
            collection = self._get_collection()
            model = self._get_model()

            q_embed = model.encode([query], convert_to_numpy=True)
            results = collection.query(
                query_embeddings=q_embed.tolist(),
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )

            out_results = []
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                
                result = {
                    "chunk_id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "source_path": metadata.get("source_path", ""),
                    "category": metadata.get("category", ""),
                    "score": round(1 - distance, 4),
                }
                out_results.append(result)

            return json.dumps({
                "query": query,
                "results": out_results,
                "total_found": len(out_results),
            }, indent=2, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "error": str(e),
                "query": query,
                "results": [],
            })


class SourceCitationTool(Tool):
    name = "source_citation"
    description = "Returns source citation with URL, section, date for critical legal instructions. Marks uncertainty when confidence is low."
    inputs = {
        "topic": {"type": "string", "description": "Legal topic requiring citation"},
        "context": {"type": "string", "description": "User situation context", "nullable": True}
    }
    output_type = "string"

    def forward(self, topic: str, context: str = None) -> str:
        from tools.llm_utils import generate
        prompt = f"Topic: {topic}\nContext: {context or 'N/A'}"
        return generate(prompt, "Provide legal citations with section numbers, acts, and URLs where available. Return JSON with citations array and uncertainty_notes if low confidence.")