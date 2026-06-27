import re
from dataclasses import dataclass


@dataclass
class Chunk:
    index: int        # position in the chunk list
    text: str         # the actual chunk text sent to embedder
    token_count: int  # approximate token count


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[Chunk]:
    """
    Split contract text into overlapping chunks for RAG.

    Why sentence-aware splitting?
      Legal clauses must stay intact. Cutting "this contract auto-renews
      unless cancelled 60 days prior" in half means RAG may only retrieve
      the first half — the risk gets missed entirely.

    Why overlap?
      A clause that spans a chunk boundary will appear complete in at least
      one chunk, so retrieval never loses it.

    Args:
        text:       cleaned contract text from extractor.py
        chunk_size: target size in tokens  (1 token ≈ 4 chars)
        overlap:    tokens to repeat between adjacent chunks
    """
    sentences = _split_sentences(text)

    chunks: list[Chunk] = []
    current: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        s_tokens = _count_tokens(sentence)

        if current_tokens + s_tokens > chunk_size and current:
            # Finalise this chunk
            chunks.append(Chunk(
                index=len(chunks),
                text=" ".join(current),
                token_count=current_tokens,
            ))
            # Keep overlap tail for next chunk
            overlap_sents, overlap_tokens = _tail_overlap(current, overlap)
            current = overlap_sents
            current_tokens = overlap_tokens

        current.append(sentence)
        current_tokens += s_tokens

    # Last chunk
    if current:
        chunks.append(Chunk(
            index=len(chunks),
            text=" ".join(current),
            token_count=current_tokens,
        ))

    # Drop noise chunks — signature blocks, headers, and lone labels
    # are typically under 100 chars and pollute FAISS results
    chunks = [c for c in chunks if len(c.text) >= 100]

    # Re-index after filtering so indices stay contiguous
    for i, c in enumerate(chunks):
        c.index = i

    return chunks


# ── helpers ──────────────────────────────────────────────────────────────────

def _split_sentences(text: str) -> list[str]:
    """
    Split on sentence boundaries while protecting legal abbreviations
    and section numbers from being treated as sentence ends.
    """
    protected = text

    # Protect common legal abbreviations
    for abbr in [r'Inc\.', r'Corp\.', r'Ltd\.', r'LLC\.', r'Co\.',
                 r'i\.e\.', r'e\.g\.', r'etc\.', r'vs\.', r'No\.',
                 r'Sec\.', r'Art\.', r'para\.',]:
        protected = re.sub(abbr, lambda m: m.group().replace('.', '##DOT##'), protected)

    # Protect decimal numbers and section refs like "3.2" or "Section 1.4"
    protected = re.sub(r'(\d+)\.(\d+)', r'\1##DOT##\2', protected)

    # Split on ". " or "! " or "? " followed by a capital letter
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', protected)

    # Restore protected dots and filter empty/tiny fragments
    return [
        s.replace('##DOT##', '.').strip()
        for s in sentences
        if len(s.strip()) > 10
    ]


def _count_tokens(text: str) -> int:
    """Approximate token count. 1 token ≈ 4 characters."""
    return max(1, len(text) // 4)


def _tail_overlap(sentences: list[str], overlap_tokens: int) -> tuple[list[str], int]:
    """
    Return the trailing sentences that fill roughly overlap_tokens.
    These are prepended to the next chunk for continuity.
    """
    result: list[str] = []
    total = 0
    for s in reversed(sentences):
        t = _count_tokens(s)
        if total + t > overlap_tokens:
            break
        result.insert(0, s)
        total += t
    return result, total