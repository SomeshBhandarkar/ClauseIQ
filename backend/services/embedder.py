import os
import json
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from services.chunker import Chunk

# ── model (loaded once at startup, not per request) ──────────────────────────
# all-MiniLM-L6-v2: free, fast, 384-dimensional, runs on CPU
# Downloads ~90MB on first run, then cached locally
_model = SentenceTransformer("all-MiniLM-L6-v2")

DIMENSION = 384
STORE_DIR = "vector_store"   # where FAISS indexes are saved to disk


def embed_and_store(contract_id: str, chunks: list[Chunk]) -> None:
    """
    Convert each chunk to a 384-dim vector and save to a per-contract
    FAISS index on disk. Also saves the raw chunk texts alongside so
    retriever.py can return actual text, not just vector IDs.

    One FAISS index per contract — this keeps contracts completely
    isolated (no cross-contract retrieval leakage).

    Args:
        contract_id: unique ID for this contract (used as filename)
        chunks:      list of Chunk objects from chunker.py
    """
    os.makedirs(STORE_DIR, exist_ok=True)

    texts = [chunk.text for chunk in chunks]

    # Embed all chunks in one batch (faster than one-by-one)
    embeddings = _model.encode(texts, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype="float32")

    # Build a flat L2 FAISS index (exact search — fine at prototype scale)
    index = faiss.IndexFlatL2(DIMENSION)
    index.add(embeddings)

    # Save the FAISS index to disk
    faiss.write_index(index, _index_path(contract_id))

    # Save the chunk texts alongside (needed to return text at retrieval time)
    with open(_chunks_path(contract_id), "wb") as f:
        pickle.dump(texts, f)


def _index_path(contract_id: str) -> str:
    return os.path.join(STORE_DIR, f"{contract_id}.index")


def _chunks_path(contract_id: str) -> str:
    return os.path.join(STORE_DIR, f"{contract_id}.chunks")