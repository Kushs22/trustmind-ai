"""RAG classification pipeline wrapper (Mode B) for TrustMind analyse API."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _ensure_paths() -> None:
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))


def run_rag_pipeline(text: str) -> dict[str, Any]:
    """
    Run hybrid BM25+FAISS retrieval then GPT classification.

    Wraps the research `rag.rag_pipeline.RagPipeline` without modifying it.
    """
    _ensure_paths()
    from openai import OpenAI
    from rag.config import get_rag_config
    from rag.rag_pipeline import RagPipeline

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for the RAG pipeline")

    rag_cfg = get_rag_config()
    # Align research config with backend settings for this request
    rag_cfg.openai_api_key = settings.openai_api_key
    rag_cfg.gpt_model = settings.openai_model
    rag_cfg.temperature = settings.openai_temperature
    rag_cfg.top_k = settings.rag_top_k
    rag_cfg.use_rag = True

    client = OpenAI(api_key=settings.openai_api_key)
    pipeline = RagPipeline(rag_cfg, client=client)
    out = pipeline.run(text, top_k=settings.rag_top_k)

    sources = list(out.get("retrieved_sources") or [])
    if settings.enable_source_display is False:
        sources = []

    return {
        "prediction": out.get("predicted_label") or out.get("prediction") or None,
        "confidence": float(out.get("confidence") or 0.0),
        "reasoning": out.get("reasoning") or "",
        "sources": sources,
        "pipeline_used": "LLM+RAG",
        "latency_ms": float(out.get("latency_ms") or 0.0),
        "error": out.get("error") or "",
        "parse_ok": bool(out.get("parse_ok")),
        "retrieved_passages": out.get("retrieved_passages") or [],
    }
