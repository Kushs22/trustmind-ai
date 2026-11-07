"""Load retrieval indexes once at process start so the first user is not the cold path."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_STATE: dict[str, Any] = {"ready": False, "error": ""}


def warmup_retrieval_indexes() -> dict[str, Any]:
    """Load BM25 (and FAISS if present). Safe to call more than once."""
    if _STATE.get("ready"):
        return {"ready": True, "error": ""}
    try:
        from rag.retriever import HybridRetriever

        retriever = HybridRetriever()
        retriever._ensure_loaded(need_faiss=True)
        _STATE["ready"] = True
        _STATE["error"] = ""
        logger.info("Retrieval indexes warmed (BM25/FAISS)")
    except Exception as exc:  # noqa: BLE001
        _STATE["ready"] = False
        _STATE["error"] = f"{type(exc).__name__}: {exc}"
        logger.warning("Index warmup failed: %s", _STATE["error"])
    return dict(_STATE)


def warmup_status() -> dict[str, Any]:
    return dict(_STATE)
