"""
Rebuild ChromaDB from chunks
"""
import json
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = Path("C:/Users/uday0/OneDrive/Desktop/code/odyssey/rag_v2/processed/chroma_db")
CHUNKS_FILE = Path("C:/Users/uday0/OneDrive/Desktop/code/odyssey/rag_v2/processed/chunks.jsonl")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "legal_rag"

print("Rebuilding ChromaDB...")
print(f"Input: {CHUNKS_FILE}")
print(f"Output: {CHROMA_DIR}")

# Load chunks
chunks = []
with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
    for line in f:
        chunks.append(json.loads(line))

print(f"Loaded {len(chunks)} chunks")

# Initialize client and model
client = chromadb.PersistentClient(path=str(CHROMA_DIR))
model = SentenceTransformer(MODEL_NAME)

# Get or create collection
try:
    collection = client.get_collection(COLLECTION_NAME)
    print(f"Collection exists: {collection.count()} items")
except:
    collection = client.create_collection(COLLECTION_NAME)
    print("Created new collection")

# Clear existing data
client.delete_collection(COLLECTION_NAME)
collection = client.create_collection(COLLECTION_NAME)

# Process in batches
batch_size = 100
total = len(chunks)

for i in range(0, total, batch_size):
    batch = chunks[i:i+batch_size]
    ids = [f"chunk_{i+j}" for j in range(len(batch))]
    documents = [c.get("text", "")[:5000] for c in batch]  # Truncate long texts
    metadatas = [
        {
            "source_path": c.get("source", ""),
            "category": c.get("category", ""),
        }
        for c in batch
    ]
    
    # Generate embeddings
    embeddings = model.encode(documents, convert_to_numpy=True).tolist()
    
    # Add to collection
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )
    
    print(f"Added {i+len(batch)}/{total} chunks")

print(f"\nDone! Collection has {collection.count()} items")