"""OpenAI embedding generation and persistence for TrustMind RAG chunks."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from rag.chunking import Chunk, load_chunks
from rag.config import RagConfig, get_rag_config

logger = logging.getLogger(__name__)


def _batched(items: Sequence[Any], batch_size: int) -> list[Sequence[Any]]:
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def embed_texts(
    texts: list[str],
    *,
    client: Any,
    model: str,
    batch_size: int = 64,
) -> np.ndarray:
    """Embed a list of texts with OpenAI; returns float32 array [n, d]."""
    vectors: list[list[float]] = []
    for batch in _batched(texts, batch_size):
        response = client.embeddings.create(model=model, input=list(batch))
        # API returns data sorted by index
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors.extend([list(item.embedding) for item in ordered])
    arr = np.asarray(vectors, dtype=np.float32)
    return arr


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    """Row-wise L2 normalisation for cosine similarity via inner product."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return matrix / norms


def embeddings_exist(config: RagConfig | None = None) -> bool:
    cfg = config or get_rag_config()
    return cfg.embeddings_npy.exists() and cfg.embeddings_meta_jsonl.exists()


def generate_and_save_embeddings(
    config: RagConfig | None = None,
    *,
    force: bool = False,
    client: Any | None = None,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """
    Embed all chunks and persist vectors + metadata.

    Skips work when files already exist unless force=True.
    """
    cfg = config or get_rag_config()
    if embeddings_exist(cfg) and not force:
        logger.info("Embeddings already present — skipping generation")
        return load_embeddings(cfg)

    if not cfg.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required to generate embeddings")

    chunks = load_chunks(cfg.chunks_jsonl)
    if not chunks:
        raise RuntimeError("No chunks found — run scripts/chunk_documents.py first")

    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=cfg.openai_api_key)

    texts = [c.text for c in chunks]
    logger.info("Embedding %s chunks with %s", len(texts), cfg.embedding_model)
    matrix = embed_texts(texts, client=client, model=cfg.embedding_model)
    matrix = l2_normalize(matrix)

    meta = [
        {
            "row_index": i,
            "chunk_id": c.chunk_id,
            "source_id": c.source_id,
            "organisation": c.organisation,
            "title": c.title,
            "topic": c.topic,
            "chunk_number": c.chunk_number,
            "source_url": c.source_url,
        }
        for i, c in enumerate(chunks)
    ]

    cfg.embeddings_dir.mkdir(parents=True, exist_ok=True)
    np.save(cfg.embeddings_npy, matrix)
    with cfg.embeddings_meta_jsonl.open("w", encoding="utf-8") as fh:
        for row in meta:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    logger.info(
        "Saved embeddings %s shape=%s and metadata %s",
        cfg.embeddings_npy,
        matrix.shape,
        cfg.embeddings_meta_jsonl,
    )
    return matrix, meta


def load_embeddings(config: RagConfig | None = None) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Load persisted embedding matrix and row metadata."""
    cfg = config or get_rag_config()
    if not embeddings_exist(cfg):
        raise FileNotFoundError(
            f"Embeddings missing at {cfg.embeddings_npy}. "
            "Run scripts/generate_embeddings.py first."
        )
    matrix = np.load(cfg.embeddings_npy)
    meta: list[dict[str, Any]] = []
    with cfg.embeddings_meta_jsonl.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                meta.append(json.loads(line))
    if len(meta) != matrix.shape[0]:
        raise ValueError(
            f"Embedding/meta length mismatch: {matrix.shape[0]} vs {len(meta)}"
        )
    return matrix.astype(np.float32), meta
