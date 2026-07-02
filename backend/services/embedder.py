import os
import json
import numpy as np
import faiss
from fastembed import TextEmbedding
from services.chunker import Chunk

_model = None


def get_model():
    global _model
    if _model is None:
        _model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _model

DIMENSION = 384
STORE_DIR = "vector_store"


def embed_and_store(contract_id: str, chunks: list[Chunk]) -> None:
    """
    Convert each chunk to a vector and save to FAISS.
    ALSO saves raw chunk texts as JSON so BM25 can index them.

    Why save raw text separately?
    FAISS only stores numbers (vectors). BM25 needs actual words.
    So we save two files per contract:
      {contract_id}.index       → FAISS vectors  (for semantic search)
      {contract_id}.chunks.json → raw text list  (for BM25 keyword search)
    """
    os.makedirs(STORE_DIR, exist_ok=True)

    texts = [chunk.text for chunk in chunks]

    # ── Embed all chunks in one batch ────────────────────────────────────────
    embeddings = list(get_model().embed(texts))
    embeddings = np.array(embeddings, dtype="float32")

    # ── Build and save FAISS index ───────────────────────────────────────────
    index = faiss.IndexFlatL2(DIMENSION)
    index.add(embeddings)
    faiss.write_index(index, _index_path(contract_id))

    # ── Save raw chunk texts for BM25 ────────────────────────────────────────
    # Saved as JSON (human readable) so you can inspect it easily during dev
    with open(_chunks_path(contract_id), "w") as f:
        json.dump(texts, f, indent=2)


def _index_path(contract_id: str) -> str:
    return os.path.join(STORE_DIR, f"{contract_id}.index")


def _chunks_path(contract_id: str) -> str:
    # Changed from .pkl (pickle/binary) to .json (readable text)
    # Makes debugging easier — you can open the file and read the chunks
    return os.path.join(STORE_DIR, f"{contract_id}.chunks.json")