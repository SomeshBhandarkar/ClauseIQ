import os
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")

STORE_DIR = "vector_store"


def retrieve(query: str, contract_id: str, top_k: int = 5) -> list[str]:
    """
    Given a plain-English question and a contract_id, return the top_k
    most semantically similar chunks from that contract.

    This is the core of RAG — instead of sending the entire contract to
    Claude (too long, too expensive), we only send the chunks most
    likely to contain the answer. Claude can only hallucinate if the
    answer isn't in the chunks — so we pick chunks carefully.

    Args:
        query:       e.g. "Does this contract have an auto-renewal clause?"
        contract_id: which contract to search against
        top_k:       how many chunks to return (5 is a good default)

    Returns:
        List of chunk text strings, most relevant first.
    """
    index_path  = os.path.join(STORE_DIR, f"{contract_id}.index")
    chunks_path = os.path.join(STORE_DIR, f"{contract_id}.chunks")

    if not os.path.exists(index_path):
        raise FileNotFoundError(
            f"No vector store found for contract '{contract_id}'. "
            "Make sure embed_and_store() was called first."
        )

    # Load the FAISS index and chunk texts for this contract
    index = faiss.read_index(index_path)
    with open(chunks_path, "rb") as f:
        chunks: list[str] = pickle.load(f)

    # Embed the query using the same model used for the chunks
    query_vec = _model.encode([query], show_progress_bar=False)
    query_vec = np.array(query_vec, dtype="float32")

    # Search — returns distances and chunk indices
    actual_k = min(top_k, len(chunks))
    _, indices = index.search(query_vec, actual_k)

    # Map indices back to text
    return [chunks[i] for i in indices[0] if i < len(chunks)]