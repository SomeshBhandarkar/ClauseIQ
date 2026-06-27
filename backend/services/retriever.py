import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

_model = SentenceTransformer("all-MiniLM-L6-v2")

STORE_DIR = "vector_store"


# ── Main entry point ──────────────────────────────────────────────────────────

def retrieve(query: str, contract_id: str, top_k: int = 5) -> list[str]:
    """
    Hybrid retrieval pipeline:
      1. FAISS  — semantic vector search        (finds similar meaning)
      2. BM25   — keyword search                (finds exact terms)
      3. RRF    — merges both ranked lists      (consensus wins)

    Returns top_k chunks after merging.
    These go directly to Claude in analyzer.py — interface unchanged.

    Args:
        query:       the clause question e.g. "Does this contract auto-renew?"
        contract_id: which contract to search
        top_k:       how many chunks to return after merging (default 5)
    """
    # Load chunks from disk (saved by embedder.py)
    chunks = _load_chunks(contract_id)

    if not chunks:
        raise ValueError(f"No chunks found for contract '{contract_id}'.")

    # Run both retrievers — each returns ranked list of (chunk_text, rank)
    faiss_results = _faiss_search(query, contract_id, chunks, top_k=10)
    bm25_results  = _bm25_search(query, chunks, top_k=10)

    # Merge with RRF — returns unified ranked list
    merged = _reciprocal_rank_fusion(faiss_results, bm25_results)

    # Return top_k chunk texts
    return [chunk for chunk, score in merged[:top_k]]


# ── Stage 1: FAISS semantic search ───────────────────────────────────────────

def _faiss_search(
    query: str,
    contract_id: str,
    chunks: list[str],
    top_k: int
) -> list[str]:
    """
    Convert query to vector, find nearest chunk vectors in FAISS.
    Returns ordered list of chunk texts (most similar first).

    Theory: cosine/L2 distance in 384-dimensional space.
    Chunks about similar concepts cluster together.
    """
    index_path = os.path.join(STORE_DIR, f"{contract_id}.index")

    if not os.path.exists(index_path):
        raise FileNotFoundError(
            f"No FAISS index found for contract '{contract_id}'. "
            "Upload the contract first."
        )

    index = faiss.read_index(index_path)

    # Embed the query using the same model used for chunks
    query_vec = _model.encode([query], show_progress_bar=False)
    query_vec = np.array(query_vec, dtype="float32")

    actual_k = min(top_k, len(chunks))
    _, indices = index.search(query_vec, actual_k)

    # Return chunk texts in ranked order (index 0 = most similar)
    return [chunks[i] for i in indices[0] if i < len(chunks)]


# ── Stage 2: BM25 keyword search ─────────────────────────────────────────────

def _bm25_search(query: str, chunks: list[str], top_k: int) -> list[str]:
    """
    Tokenize all chunks, build BM25 index, score query against all chunks.
    Returns ordered list of chunk texts (highest keyword score first).

    Theory: BM25 scores based on term frequency (TF) and inverse document
    frequency (IDF). Terms that appear in the query AND are rare across
    all chunks get the highest score.

    Example: "termination without cause" — if only 1 of 20 chunks
    contains the word "cause", that chunk gets a very high IDF score.
    """
    # Tokenize: lowercase + split on whitespace
    # Simple but effective for legal text
    tokenized_chunks = [chunk.lower().split() for chunk in chunks]
    tokenized_query  = query.lower().split()

    # Build BM25 index over all chunks
    bm25 = BM25Okapi(tokenized_chunks)

    # Score all chunks against the query
    scores = bm25.get_scores(tokenized_query)

    # Sort by score descending, return top_k chunk texts
    ranked_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )

    return [chunks[i] for i in ranked_indices[:top_k]]


# ── Stage 3: Reciprocal Rank Fusion ──────────────────────────────────────────

def _reciprocal_rank_fusion(
    faiss_results: list[str],
    bm25_results: list[str],
    k: int = 60
) -> list[tuple[str, float]]:
    """
    Merge two ranked lists into one using RRF.

    Formula: score(chunk) = 1/(k + rank_in_faiss) + 1/(k + rank_in_bm25)

    Key insight: rank position matters, not the raw scores.
    This solves the "incompatible scales" problem — FAISS scores are
    cosine distances (0-1), BM25 scores are term frequencies (0-∞).
    You can't add those directly. But you CAN add their rank positions.

    Why k=60?
    k prevents the #1 ranked item from being overwhelmingly dominant.
    With k=60: rank 1 scores 1/61 = 0.0164, rank 2 scores 1/62 = 0.0161
    The difference is small — consensus beats a single dominant rank.
    With k=1: rank 1 scores 1/2 = 0.5, rank 2 scores 1/3 = 0.33
    Much more skewed — rank 1 dominates everything.

    A chunk appearing in BOTH lists (even at rank 5) beats a chunk
    appearing at rank 1 in only one list. That's the right behavior.
    """
    scores: dict[str, float] = {}

    # Score from FAISS ranked list
    for rank, chunk in enumerate(faiss_results):
        scores[chunk] = scores.get(chunk, 0.0) + 1.0 / (k + rank + 1)

    # Add score from BM25 ranked list
    for rank, chunk in enumerate(bm25_results):
        scores[chunk] = scores.get(chunk, 0.0) + 1.0 / (k + rank + 1)

    # Sort by combined RRF score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return ranked  # list of (chunk_text, rrf_score)


# ── Helper ────────────────────────────────────────────────────────────────────

def _load_chunks(contract_id: str) -> list[str]:
    """Load raw chunk texts saved by embedder.py."""
    path = os.path.join(STORE_DIR, f"{contract_id}.chunks.json")

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No chunks found for contract '{contract_id}'. "
            "Upload the contract first."
        )

    with open(path) as f:
        return json.load(f)