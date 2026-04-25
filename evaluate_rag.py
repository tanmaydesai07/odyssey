"""
RAG Quality Evaluation using Ragas.

Run this SEPARATELY from the agent — it does not affect the running app.
It evaluates whether the ChromaDB retriever is returning relevant chunks.

Usage:
    conda run -n shrishtiai python agent/evaluate_rag.py

What it measures:
    - context_precision   : are retrieved chunks actually relevant to the question?
    - context_recall      : does the retrieved context contain the answer?
    - faithfulness        : does the answer stick to what the context says?
    - answer_relevancy    : is the answer actually answering the question asked?

Output:
    Prints a score table and saves results to agent/eval_results.json
"""

import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
sys.path.insert(0, str(Path(__file__).parent))

os.environ["TOKENIZERS_PARALLELISM"] = "0"

# ---------------------------------------------------------------------------
# Test dataset — real questions a user would ask + expected answer keywords
# ---------------------------------------------------------------------------
TEST_CASES = [
    {
        "question": "How do I file a consumer complaint for a defective product I bought online?",
        "ground_truth": "File complaint at District Consumer Disputes Redressal Commission under Consumer Protection Act 2019 Section 35. Need purchase receipt, product photos, written complaint.",
    },
    {
        "question": "What is the procedure to file an FIR at a police station?",
        "ground_truth": "Visit police station, give written complaint to SHO, police must register FIR for cognizable offences, get free copy of FIR under Section 154 CrPC.",
    },
    {
        "question": "How do I file an RTI application to get government information?",
        "ground_truth": "Submit written application to Public Information Officer with Rs 10 fee, response within 30 days under RTI Act 2005.",
    },
    {
        "question": "My employer has not paid my salary for 3 months. What can I do?",
        "ground_truth": "File complaint with Labour Commissioner under Payment of Wages Act. Can also approach Labour Court for recovery of wages.",
    },
    {
        "question": "I was bitten by my neighbor's dog. What legal action can I take?",
        "ground_truth": "File civil suit for compensation under tort law. Can also file FIR under IPC Section 289 for negligent conduct with animal. Collect medical records as evidence.",
    },
]


def retrieve_context(query: str, top_k: int = 3) -> list[str]:
    """Use the existing LegalRetrieverTool to get context chunks."""
    from tools.legal_retriever import LegalRetrieverTool
    retriever = LegalRetrieverTool()
    result_json = retriever.forward(query=query, top_k=top_k)
    result = json.loads(result_json)
    return [r["text"] for r in result.get("results", [])]


def generate_answer(question: str, contexts: list[str]) -> str:
    """Generate an answer using the LLM given retrieved contexts."""
    from tools.llm_utils import generate
    context_text = "\n\n---\n\n".join(contexts[:3])
    system = (
        "You are a legal assistant for Indian citizens. "
        "Answer the question using ONLY the provided context. "
        "If the context doesn't contain enough information, say so clearly."
    )
    prompt = f"Context:\n{context_text}\n\nQuestion: {question}\n\nAnswer:"
    return generate(prompt, system)


def run_evaluation():
    print("=" * 60)
    print("RAG Quality Evaluation")
    print("=" * 60)
    print(f"Test cases: {len(TEST_CASES)}")
    print()

    # Build dataset
    questions = []
    answers = []
    contexts = []
    ground_truths = []

    for i, tc in enumerate(TEST_CASES):
        print(f"[{i+1}/{len(TEST_CASES)}] Retrieving: {tc['question'][:60]}...")
        ctx = retrieve_context(tc["question"])
        ans = generate_answer(tc["question"], ctx)
        questions.append(tc["question"])
        answers.append(ans)
        contexts.append(ctx)
        ground_truths.append(tc["ground_truth"])
        print(f"  Retrieved {len(ctx)} chunks, answer length: {len(ans)} chars")

    print()
    print("Running Ragas evaluation...")

    try:
        from ragas import evaluate
        from ragas.metrics import (
            context_precision,
            context_recall,
            faithfulness,
            answer_relevancy,
        )
        from datasets import Dataset

        dataset = Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        })

        # Ragas needs an LLM — use OpenAI-compatible wrapper pointing at Zen
        from langchain_openai import ChatOpenAI
        zen_api_key = os.getenv("ZEN_API_KEY", "")
        zen_llm = ChatOpenAI(
            model="big-pickle",
            openai_api_key=zen_api_key,
            openai_api_base="https://opencode.ai/zen/v1",
            temperature=0,
        )

        result = evaluate(
            dataset=dataset,
            metrics=[context_precision, context_recall, faithfulness, answer_relevancy],
            llm=zen_llm,
            raise_exceptions=False,
        )

        print()
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        scores = result.to_pandas()
        print(scores[["question", "context_precision", "context_recall", "faithfulness", "answer_relevancy"]].to_string())

        print()
        print("AVERAGES:")
        for metric in ["context_precision", "context_recall", "faithfulness", "answer_relevancy"]:
            if metric in scores.columns:
                avg = scores[metric].mean()
                bar = "█" * int(avg * 20) + "░" * (20 - int(avg * 20))
                print(f"  {metric:<22} {bar} {avg:.3f}")

        # Save results
        out_path = Path(__file__).parent / "eval_results.json"
        result_dict = {
            "scores": scores.to_dict(orient="records"),
            "averages": {
                m: float(scores[m].mean())
                for m in ["context_precision", "context_recall", "faithfulness", "answer_relevancy"]
                if m in scores.columns
            },
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2, default=str)
        print(f"\nResults saved to {out_path}")

    except ImportError as e:
        print(f"Ragas import error: {e}")
        print("Run: conda run -n shrishtiai pip install ragas datasets langchain-openai")

    except Exception as e:
        print(f"Evaluation error: {e}")
        import traceback
        traceback.print_exc()

        # Fallback: show raw retrieval quality manually
        print()
        print("=" * 60)
        print("FALLBACK: Manual retrieval inspection")
        print("=" * 60)
        for i, (q, ctx, gt) in enumerate(zip(questions, contexts, ground_truths)):
            print(f"\nQ{i+1}: {q}")
            print(f"Ground truth keywords: {gt[:100]}")
            print(f"Retrieved {len(ctx)} chunks:")
            for j, c in enumerate(ctx):
                print(f"  Chunk {j+1} ({len(c)} chars): {c[:120]}...")


if __name__ == "__main__":
    run_evaluation()
