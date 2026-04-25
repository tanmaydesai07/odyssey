import chromadb
from pathlib import Path

# Try multiple paths
BASE_DIR = Path("C:/Users/uday0/OneDrive/Desktop/code/odyssey")
CHROMA_PATHS = [
    BASE_DIR / "rag_v2" / "processed" / "chroma_db",
]

print("Checking ChromaDB...")

for p in CHROMA_PATHS:
    if p.exists():
        print(f"Found: {p}")
        try:
            client = chromadb.PersistentClient(path=str(p))
            cols = client.list_collections()
            print(f"Collections: {[c.name for c in cols]}")
            for c in cols:
                print(f"  - {c.name}: {c.count()} items")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"Not found: {p}")