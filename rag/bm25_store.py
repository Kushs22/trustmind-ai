"""BM25 lexical index build / load / search for TrustMind RAG."""

from __future__ import annotations

import logging
import pickle
import re
from pathlib import Path
from typing import Any

from rag.chunking import load_chunks
from rag.config import RagConfig, get_rag_config

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    """Simple alphanumeric lowercased tokenizer for BM25."""
    return [tok.lower() for tok in TOKEN_RE.findall(text or "")]


def build_bm25_index(
    config: RagConfig | None = None,
    *,
    force: bool = False,
) -> Path:
    """Build and pickle a BM25Okapi index over chunk texts."""
    from rank_bm25 import BM25Okapi

    cfg = config or get_rag_config()
    cfg.bm25_dir.mkdir(parents=True, exist_ok=True)

    if cfg.bm25_index_path.exists() and not force:
        logger.info("BM25 index already exists — skipping build")
        return cfg.bm25_index_path

    chunks = load_chunks(cfg.chunks_jsonl)
    if not chunks:
        raise RuntimeError("No chunks found — run scripts/chunk_documents.py first")

    corpus_tokens = [tokenize(c.text) for c in chunks]
    bm25 = BM25Okapi(corpus_tokens)
    payload = {
        "bm25": bm25,
        "chunk_ids": [c.chunk_id for c in chunks],
        "corpus_tokens": corpus_tokens,
    }
    with cfg.bm25_index_path.open("wb") as fh:
        pickle.dump(payload, fh)

    logger.info("Wrote BM25 index (%s docs) → %s", len(chunks), cfg.bm25_index_path)
    return cfg.bm25_index_path


def load_bm25(config: RagConfig | None = None) -> dict[str, Any]:
    """Load pickled BM25 payload."""
    cfg = config or get_rag_config()
    if not cfg.bm25_index_path.exists():
        raise FileNotFoundError(
            f"BM25 index missing. Run scripts/build_bm25.py first ({cfg.bm25_index_path})"
        )
    with cfg.bm25_index_path.open("rb") as fh:
        return pickle.load(fh)


def search_keywords(
    query: str,
    *,
    top_k: int | None = None,
    config: RagConfig | None = None,
    payload: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    BM25 keyword search.

    Returns list of {chunk_id, score, rank}.
    """
    cfg = config or get_rag_config()
    k = top_k or cfg.bm25_candidate_k
    data = payload or load_bm25(cfg)
    bm25 = data["bm25"]
    chunk_ids: list[str] = data["chunk_ids"]

    tokens = tokenize(query)
    if not tokens:
        return []

    scores = bm25.get_scores(tokens)
    # argsort descending
    ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)[:k]
    results: list[dict[str, Any]] = []
    for rank, (idx, score) in enumerate(ranked, start=1):
        if float(score) <= 0:
            continue
        results.append(
            {
                "chunk_id": chunk_ids[idx],
                "score": float(score),
                "rank": rank,
            }
        )
    return results
