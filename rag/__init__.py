"""TrustMind AI Retrieval-Augmented Generation package."""

from __future__ import annotations

from typing import Any

__all__ = [
    "RagConfig",
    "get_rag_config",
    "RagPipeline",
    "HybridRetriever",
    "retrieve",
    "retrieve_bm25_only",
]


def __getattr__(name: str) -> Any:
    # Lazy exports — avoid importing FAISS/OpenAI at package import time.
    if name in {"RagConfig", "get_rag_config"}:
        from rag.config import RagConfig, get_rag_config

        return {"RagConfig": RagConfig, "get_rag_config": get_rag_config}[name]
    if name == "RagPipeline":
        from rag.rag_pipeline import RagPipeline

        return RagPipeline
    if name in {"HybridRetriever", "retrieve", "retrieve_bm25_only"}:
        from rag.retriever import HybridRetriever, retrieve, retrieve_bm25_only

        return {
            "HybridRetriever": HybridRetriever,
            "retrieve": retrieve,
            "retrieve_bm25_only": retrieve_bm25_only,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
