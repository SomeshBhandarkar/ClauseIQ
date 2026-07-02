import os
import json
import numpy as np
import faiss
import cohere
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi

_model = None
_cohere = cohere.Client(os.environ.get("COHERE_API_KEY"))


def get_model():
    global _model
    if _model is None:
        _model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _model

STORE_DIR = "vector_store"


# ── Main entry point ──────────────────────────────────────────────────────────

def retrieve(query: str, contract_id: str, top_k: int = 5) -> list[str]:
    """
    Full hybrid retrieval pipeline — 3 stages:

      Stage 1: FAISS (semantic) + BM25 (keyword) run in parallel
               Each returns top 10 chunks independently

      Stage 2: RRF merges both lists into one ranked list of ~20 chunks
               Consensus between the two lists wins

      Stage 3: Cohere Rerank reads all ~20 chunks + the query together
               Re-scores by actual relevance, keeps top_k

    Returns top_k chunks ready to send to Claude.
    Interface unchanged from old retriever — analyzer.py needs zero changes.
    """
    chunks = _load_chunks(contract_id)

    if not chunks:
        raise ValueError(f"No chunks found for contract '{contract_id}'.")

    # Stage 1 — run both retrievers independently
    faiss_results = _faiss_search(query, contract_id, chunks, top_k=10)
    bm25_results  = _bm25_search(query, chunks, top_k=10)

    # Stage 2 — merge with RRF
    merged = _reciprocal_rank_fusion(faiss_results, bm25_results)
    merged_chunks = [chunk for chunk, score in merged]

    # Stage 3 — rerank with Cohere, keep top_k
    reranked = _cohere_rerank(query, merged_chunks, top_k=top_k)

    return reranked


# ── Stage 1a: FAISS semantic search ──────────────────────────────────────────

def _faiss_search(
    query: str,
    contract_id: str,
    chunks: list[str],
    top_k: int
) -> list[str]:
    """
    Embed query → find nearest vectors in FAISS index.
    Finds chunks with similar MEANING to the query.
    """
    index_path = os.path.join(STORE_DIR, f"{contract_id}.index")

    if not os.path.exists(index_path):
        raise FileNotFoundError(
            f"No FAISS index found for contract '{contract_id}'. "
            "Upload the contract first."
        )

    index     = faiss.read_index(index_path)
    query_vec = list(get_model().embed([query]))
    query_vec = np.array(query_vec, dtype="float32")

    actual_k  = min(top_k, len(chunks))
    _, indices = index.search(query_vec, actual_k)

    return [chunks[i] for i in indices[0] if i < len(chunks)]


# ── Stage 1b: BM25 keyword search ────────────────────────────────────────────

def _bm25_search(query: str, chunks: list[str], top_k: int) -> list[str]:
    """
    Tokenize chunks → build BM25 index → score query against all chunks.
    Finds chunks with exact KEYWORD matches to the query.
    """
    tokenized_chunks = [chunk.lower().split() for chunk in chunks]
    tokenized_query  = query.lower().split()

    bm25   = BM25Okapi(tokenized_chunks)
    scores = bm25.get_scores(tokenized_query)

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )

    return [chunks[i] for i in ranked_indices[:top_k]]


# ── Stage 2: Reciprocal Rank Fusion ──────────────────────────────────────────

def _reciprocal_rank_fusion(
    faiss_results: list[str],
    bm25_results: list[str],
    k: int = 60
) -> list[tuple[str, float]]:
    """
    Merge two ranked lists using RRF.

    Formula: score(chunk) = 1/(k+rank_faiss) + 1/(k+rank_bm25)

    A chunk in both lists at rank 5 beats a chunk at rank 1 in only
    one list. Consensus beats dominance. k=60 prevents any single
    top-ranked item from dominating everything.
    """
    scores: dict[str, float] = {}

    for rank, chunk in enumerate(faiss_results):
        scores[chunk] = scores.get(chunk, 0.0) + 1.0 / (k + rank + 1)

    for rank, chunk in enumerate(bm25_results):
        scores[chunk] = scores.get(chunk, 0.0) + 1.0 / (k + rank + 1)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ── Stage 3: Cohere Rerank ────────────────────────────────────────────────────

def _cohere_rerank(
    query: str,
    chunks: list[str],
    top_k: int = 5
) -> list[str]:
    """
    Send query + all RRF-merged chunks to Cohere Rerank.

    Cohere reads each chunk alongside the query and scores true relevance
    from 0.0 to 1.0. This is the final quality gate before Claude.

    Why this matters:
      RRF merges by position math — it's blind to actual content.
      Cohere actually reads the text. A chunk that says "payment due Net 30"
      will score near 0.0 for a query about auto-renewal, even if RRF
      ranked it high because it appeared in both FAISS and BM25 results.

    Cost: Cohere free tier = 1,000 reranks/month. Each analyze call
    makes 25 rerank requests (one per clause). That's 40 full contract
    analyses free per month — plenty for testing and early users.

    Falls back to RRF order if Cohere API fails — no silent breakage.
    """
    if not chunks:
        return []

    # Cohere requires at least 1 document and the query to be non-empty
    if not query.strip():
        return chunks[:top_k]

    try:
        response = _cohere.rerank(
            model     = "rerank-english-v3.0",
            query     = query,
            documents = chunks,
            top_n     = top_k,
        )

        # response.results is sorted by relevance score descending
        # Each result has: .index (position in input chunks), .relevance_score
        reranked = [chunks[r.index] for r in response.results]

        # Debug — remove after testing
        print(f"\n[COHERE] Query: {query[:60]}")
        for r in response.results:
            print(f"  score={r.relevance_score:.3f} | {chunks[r.index][:70]}...")

        return reranked

    except Exception as e:
        # Graceful fallback — if Cohere is down or rate limited,
        # return RRF order instead of crashing the whole analysis
        print(f"[COHERE] Rerank failed ({e}), falling back to RRF order")
        return chunks[:top_k]


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