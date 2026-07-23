"""End-to-end RAG inference pipeline for TrustMind SWMH classification."""

from __future__ import annotations

import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

from rag.config import RagConfig, get_rag_config
from rag.logging_utils import RagRunLogger
from rag.prompt_builder import CLASS_LABELS, build_rag_prompt
from rag.retriever import HybridRetriever

# Allow importing research/llm_baseline.py without modifying that module
_RESEARCH = Path(__file__).resolve().parents[1] / "research"
if str(_RESEARCH) not in sys.path:
    sys.path.insert(0, str(_RESEARCH))

logger = logging.getLogger(__name__)


def _naturalise_reasoning(text: str) -> str:
    """Strip academic citation markers from user-facing explanations."""
    cleaned = re.sub(r"\[\s*\d+\s*\]", "", text)
    cleaned = re.sub(
        r"\b(Retrieved sources?|Source IDs?)\s*[:\-].*$",
        "",
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" +\n", "\n", cleaned)
    return cleaned.strip()


def _parse_rag_response(response_text: str) -> dict[str, Any]:
    """Parse RAG JSON; reuse baseline helpers for label normalisation."""
    from llm_baseline import VALID_LABELS, extract_json_object, normalize_label

    parsed = extract_json_object(response_text)
    if parsed is None:
        return {
            "predicted_label": "",
            "confidence": 0.0,
            "reasoning": "",
            "retrieved_sources": [],
            "parse_ok": False,
            "error": "invalid_json_or_empty_response",
            "raw_response": (response_text or "")[:2000],
        }

    raw_label = parsed.get("prediction", parsed.get("predicted_label", ""))
    label = normalize_label(raw_label)
    if label not in VALID_LABELS:
        # Accept display-style labels from the prompt builder list
        for candidate in CLASS_LABELS:
            if str(raw_label).strip().lower() == candidate.lower():
                label = candidate
                break
        else:
            label = ""

    confidence = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence)
        if confidence > 1.0 and confidence <= 100.0:
            confidence = confidence / 100.0
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    reasoning = _naturalise_reasoning(str(parsed.get("reasoning") or "").strip())
    sources = parsed.get("retrieved_sources") or []
    if isinstance(sources, str):
        sources = [sources]
    if not isinstance(sources, list):
        sources = []
    sources = [str(s).strip() for s in sources if str(s).strip()]

    return {
        "predicted_label": label,
        "confidence": confidence,
        "reasoning": reasoning,
        "retrieved_sources": sources,
        "parse_ok": bool(label),
        "error": "" if label else "invalid_or_missing_label",
        "raw_response": (response_text or "")[:2000],
    }


class RagPipeline:
    """Retrieve → prompt → GPT → structured prediction."""

    def __init__(
        self,
        config: RagConfig | None = None,
        *,
        client: Any | None = None,
        run_logger: RagRunLogger | None = None,
    ) -> None:
        self.config = config or get_rag_config()
        self.client = client
        self.run_logger = run_logger or RagRunLogger(self.config.rag_log_dir)
        self.retriever = HybridRetriever(self.config, client=client)

    def _ensure_client(self) -> Any:
        if self.client is None:
            if not self.config.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required for RAG inference")
            from openai import OpenAI

            self.client = OpenAI(api_key=self.config.openai_api_key)
            self.retriever.client = self.client
        return self.client

    def run(self, text: str, top_k: int | None = None) -> dict[str, Any]:
        """
        Run one RAG classification.

        Returns prediction, confidence, reasoning, retrieved sources, latency.
        """
        from llm_baseline import call_openai_json

        started = time.perf_counter()
        client = self._ensure_client()
        cfg = self.config
        error = ""

        try:
            passages = self.retriever.retrieve(text, top_k=top_k)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Retrieval failed")
            passages = []
            error = f"retrieval_error: {type(exc).__name__}: {exc}"

        prompt = build_rag_prompt(text, passages)
        response_text = ""
        api_error = ""
        if not error:
            response_text, api_error = call_openai_json(
                client,
                model_name=cfg.gpt_model,
                prompt=prompt,
                temperature=cfg.temperature,
            )
            if api_error and not response_text:
                error = api_error

        if response_text:
            parsed = _parse_rag_response(response_text)
            if api_error and not parsed["error"]:
                parsed["error"] = api_error
        else:
            parsed = {
                "predicted_label": "",
                "confidence": 0.0,
                "reasoning": "",
                "retrieved_sources": [],
                "parse_ok": False,
                "error": error or "empty_response",
                "raw_response": "",
            }

        # Prefer model-reported sources; fall back to retrieved chunk source IDs
        retrieved_meta = [p.to_dict() for p in passages]
        if not parsed["retrieved_sources"] and passages:
            parsed["retrieved_sources"] = [p.source for p in passages]

        latency_ms = (time.perf_counter() - started) * 1000.0
        result = {
            "prediction": parsed["predicted_label"],
            "predicted_label": parsed["predicted_label"],
            "confidence": parsed["confidence"],
            "reasoning": parsed["reasoning"],
            "retrieved_sources": parsed["retrieved_sources"],
            "retrieved_passages": retrieved_meta,
            "parse_ok": parsed["parse_ok"],
            "error": parsed["error"] or error,
            "latency_ms": latency_ms,
            "prompt": prompt,
            "raw_response": parsed.get("raw_response", ""),
        }

        self.run_logger.log_run(
            query=text,
            prompt=prompt,
            response=response_text,
            passages=retrieved_meta,
            result={
                "prediction": result["prediction"],
                "confidence": result["confidence"],
                "error": result["error"],
                "latency_ms": latency_ms,
            },
        )
        return result


def run_rag_inference_batch(
    texts: list[str],
    *,
    config: RagConfig | None = None,
    client: Any | None = None,
    sleep_between_calls: float | None = None,
    progress_every: int = 10,
) -> list[dict[str, Any]]:
    """Classify many texts with RAG (research evaluation helper)."""
    cfg = config or get_rag_config()
    pipeline = RagPipeline(cfg, client=client)
    pause = cfg.sleep_between_calls if sleep_between_calls is None else sleep_between_calls
    rows: list[dict[str, Any]] = []
    total = len(texts)
    for i, text in enumerate(texts, start=1):
        out = pipeline.run(text)
        rows.append(out)
        if progress_every and i % progress_every == 0:
            print(f"RAG processed {i}/{total} posts...")
        if pause > 0:
            time.sleep(pause)
    return rows
