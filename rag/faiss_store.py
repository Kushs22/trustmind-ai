"""FAISS vector index build / load / search helpers for TrustMind RAG."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

from rag.config import RagConfig, get_rag_config
from rag.embeddings_store import embed_texts, l2_normalize, load_embeddings

logger = logging.getLogger(__name__)


def build_faiss_index(
    config: RagConfig | None = None,
    *,
    force: bool = False,
) -> Path:
    """Build and persist a FAISS IndexFlatIP over L2-normalised embeddings."""
    import faiss

    cfg = config or get_rag_config()
    cfg.faiss_dir.mkdir(parents=True, exist_ok=True)
    id_map_path = cfg.faiss_dir / "id_map.json"

    if cfg.faiss_index_path.exists() and id_map_path.exists() and not force:
        logger.info("FAISS index already exists — skipping build")
        return cfg.faiss_index_path

    matrix, meta = load_embeddings(cfg)
    dim = int(matrix.shape[1])
    index = faiss.IndexFlatIP(dim)
    index.add(matrix)
    faiss.write_index(index, str(cfg.faiss_index_path))

    id_map = [row["chunk_id"] for row in meta]
    id_map_path.write_text(json.dumps(id_map, indent=2), encoding="utf-8")
    logger.info("Wrote FAISS index (%s vectors, dim=%s) → %s", index.ntotal, dim, cfg.faiss_index_path)
    return cfg.faiss_index_path


def load_index(config: RagConfig | None = None) -> tuple[Any, list[str]]:
    """Load FAISS index and chunk_id map."""
    import faiss

    cfg = config or get_rag_config()
    id_map_path = cfg.faiss_dir / "id_map.json"
    if not cfg.faiss_index_path.exists() or not id_map_path.exists():
        raise FileNotFoundError(
            f"FAISS index missing. Run scripts/build_faiss.py first ({cfg.faiss_index_path})"
        )
    index = faiss.read_index(str(cfg.faiss_index_path))
    id_map = json.loads(id_map_path.read_text(encoding="utf-8"))
    return index, id_map


def search_vector(
    query: str,
    *,
    top_k: int | None = None,
    config: RagConfig | None = None,
    client: Any | None = None,
    index: Any | None = None,
    id_map: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Dense vector search for a query string.

    Returns list of {chunk_id, score, rank}.
    """
    cfg = config or get_rag_config()
    k = top_k or cfg.faiss_candidate_k

    if index is None or id_map is None:
        index, id_map = load_index(cfg)

    if client is None:
        if not cfg.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY required for query embedding")
        from openai import OpenAI

        client = OpenAI(api_key=cfg.openai_api_key)

    query_vec = embed_texts([query], client=client, model=cfg.embedding_model)
    query_vec = l2_normalize(query_vec)
    scores, indices = index.search(query_vec, min(k, len(id_map)))

    results: list[dict[str, Any]] = []
    for rank, (idx, score) in enumerate(zip(indices[0].tolist(), scores[0].tolist()), start=1):
        if idx < 0:
            continue
        results.append(
            {
                "chunk_id": id_map[idx],
                "score": float(score),
                "rank": rank,
            }
        )
    return results
