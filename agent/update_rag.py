"""
RAG Freshness Update Pipeline.

Run this whenever laws/procedures change to update the ChromaDB corpus
without rebuilding everything from scratch.

Usage:
    # Add a new document to the corpus:
    conda run -n shrishtiai python agent/update_rag.py --add path/to/new_law.pdf

    # Remove a document by source path:
    conda run -n shrishtiai python agent/update_rag.py --remove "laws/central/old_act.pdf"

    # Check what's in the corpus:
    conda run -n shrishtiai python agent/update_rag.py --status

    # Full rebuild from chunks.jsonl:
    conda run -n shrishtiai python agent/update_rag.py --rebuild
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Resolve paths relative to this file
BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATHS = [
    BASE_DIR / "chroma_db",
    BASE_DIR.parent / "rag_v2" / "processed" / "chroma_db",
]
CHUNKS_PATHS = [
    BASE_DIR / "chunks.jsonl",
    BASE_DIR.parent / "rag_v2" / "processed" / "chunks.jsonl",
]

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "legal_rag"


def _get_chroma_dir():
    for p in CHROMA_PATHS:
        if p.exists():
            return p
    return CHROMA_PATHS[0]


def _get_chunks_file():
    for p in CHUNKS_PATHS:
        if p.exists():
            return p
    return CHUNKS_PATHS[0]


def _get_collection():
    import chromadb
    client = chromadb.PersistentClient(path=str(_get_chroma_dir()))
    try:
        return client, client.get_collection(COLLECTION_NAME)
    except Exception:
        return client, client.create_collection(COLLECTION_NAME)


def cmd_status():
    """Show what's currently in the corpus."""
    client, collection = _get_collection()
    count = collection.count()
    print(f"\nChromaDB Status")
    print(f"  Path:       {_get_chroma_dir()}")
    print(f"  Collection: {COLLECTION_NAME}")
    print(f"  Documents:  {count} chunks")

    if count > 0:
        # Sample a few to show sources
        sample = collection.get(limit=min(count, 200), include=["metadatas"])
        sources = {}
        for meta in sample["metadatas"]:
            src = meta.get("source_path", "unknown")
            sources[src] = sources.get(src, 0) + 1
        print(f"\n  Sources ({len(sources)} unique files):")
        for src, n in sorted(sources.items(), key=lambda x: -x[1])[:20]:
            print(f"    {n:4d} chunks  {src}")


def cmd_add(file_path: str):
    """Add a new PDF or text file to the corpus."""
    path = Path(file_path)
    if not path.exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    print(f"Adding: {path.name}")

    # Extract text
    text = ""
    if path.suffix.lower() == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except ImportError:
            print("pdfplumber not installed. Run: pip install pdfplumber")
            sys.exit(1)
    elif path.suffix.lower() in (".txt", ".md"):
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        print(f"Unsupported file type: {path.suffix}. Use PDF or TXT.")
        sys.exit(1)

    if not text.strip():
        print("ERROR: No text extracted from file.")
        sys.exit(1)

    # Chunk the text (simple 1000-char chunks with 200-char overlap)
    chunk_size = 1000
    overlap = 200
    chunks = []
    i = 0
    while i < len(text):
        chunk = text[i:i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap

    print(f"  Extracted {len(chunks)} chunks from {len(text)} chars")

    # Embed and add
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    client, collection = _get_collection()

    # Use timestamp-based IDs to avoid collisions
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    ids = [f"{path.stem}_{ts}_c{i:04d}" for i in range(len(chunks))]
    embeddings = model.encode(chunks, convert_to_numpy=True).tolist()
    metadatas = [
        {
            "source_path": str(path),
            "category": "laws",
            "added_at": datetime.utcnow().isoformat(),
        }
        for _ in chunks
    ]

    # Batch insert
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        collection.add(
            ids=ids[i:i+batch_size],
            documents=chunks[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size],
            embeddings=embeddings[i:i+batch_size],
        )
        print(f"  Added {min(i+batch_size, len(chunks))}/{len(chunks)} chunks")

    print(f"\nDone. Corpus now has {collection.count()} total chunks.")

    # Append to chunks.jsonl for record-keeping
    chunks_file = _get_chunks_file()
    if chunks_file.exists():
        with open(chunks_file, "a", encoding="utf-8") as f:
            for chunk_id, chunk_text, meta in zip(ids, chunks, metadatas):
                f.write(json.dumps({
                    "id": chunk_id,
                    "text": chunk_text,
                    "source": meta["source_path"],
                    "category": meta["category"],
                }) + "\n")
        print(f"Appended to {chunks_file}")


def cmd_remove(source_path: str):
    """Remove all chunks from a specific source file."""
    client, collection = _get_collection()
    count_before = collection.count()

    # Find all chunks from this source
    results = collection.get(
        where={"source_path": {"$eq": source_path}},
        include=["metadatas"],
    )
    ids_to_delete = results["ids"]

    if not ids_to_delete:
        print(f"No chunks found for source: {source_path}")
        return

    collection.delete(ids=ids_to_delete)
    count_after = collection.count()
    print(f"Removed {len(ids_to_delete)} chunks from '{source_path}'")
    print(f"Corpus: {count_before} → {count_after} chunks")


def cmd_rebuild():
    """Full rebuild from chunks.jsonl."""
    chunks_file = _get_chunks_file()
    if not chunks_file.exists():
        print(f"ERROR: chunks.jsonl not found at {chunks_file}")
        sys.exit(1)

    print(f"Full rebuild from {chunks_file}")

    chunks = []
    with open(chunks_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))

    print(f"Loaded {len(chunks)} chunks")

    import chromadb
    from sentence_transformers import SentenceTransformer

    chroma_dir = _get_chroma_dir()
    client = chromadb.PersistentClient(path=str(chroma_dir))

    # Drop and recreate
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    model = SentenceTransformer(MODEL_NAME)
    batch_size = 100

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        ids = [c.get("id", f"chunk_{i+j}") for j, c in enumerate(batch)]
        documents = [c.get("text", "")[:5000] for c in batch]
        metadatas = [{"source_path": c.get("source", ""), "category": c.get("category", "")} for c in batch]
        embeddings = model.encode(documents, convert_to_numpy=True).tolist()
        collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
        print(f"  {min(i+batch_size, len(chunks))}/{len(chunks)} chunks indexed")

    print(f"\nRebuild complete. {collection.count()} chunks in corpus.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG corpus update tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--status", action="store_true", help="Show corpus status")
    group.add_argument("--add", metavar="FILE", help="Add a PDF/TXT file to corpus")
    group.add_argument("--remove", metavar="SOURCE_PATH", help="Remove chunks by source path")
    group.add_argument("--rebuild", action="store_true", help="Full rebuild from chunks.jsonl")
    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.add:
        cmd_add(args.add)
    elif args.remove:
        cmd_remove(args.remove)
    elif args.rebuild:
        cmd_rebuild()
