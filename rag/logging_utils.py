"""Structured RAG run logging (retrieved docs, prompt, response, latency)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RagRunLogger:
    """Append JSONL records for each RAG inference call."""

    def __init__(self, log_dir: Path) -> None:
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.log_dir / "rag_runs.jsonl"
        self._file_logger = logging.getLogger("trustmind.rag.runs")
        if not self._file_logger.handlers:
            handler = logging.FileHandler(self.log_dir / "rag_pipeline.log", encoding="utf-8")
            handler.setFormatter(
                logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
            )
            self._file_logger.addHandler(handler)
            self._file_logger.setLevel(logging.INFO)

    def log_run(
        self,
        *,
        query: str,
        prompt: str,
        response: str,
        passages: list[dict[str, Any]],
        result: dict[str, Any],
    ) -> None:
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "query_preview": (query or "")[:500],
            "n_passages": len(passages),
            "passage_scores": [
                {
                    "chunk_id": p.get("chunk_id"),
                    "source": p.get("source"),
                    "similarity_score": p.get("similarity_score"),
                    "bm25_score": p.get("bm25_score"),
                    "faiss_score": p.get("faiss_score"),
                }
                for p in passages
            ],
            "prompt_chars": len(prompt or ""),
            "response_preview": (response or "")[:1000],
            "result": result,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

        self._file_logger.info(
            "RAG run prediction=%s confidence=%s latency_ms=%.1f passages=%s error=%s",
            result.get("prediction"),
            result.get("confidence"),
            float(result.get("latency_ms") or 0.0),
            len(passages),
            result.get("error") or "",
        )
