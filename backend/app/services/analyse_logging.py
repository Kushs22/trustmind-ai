"""Separate analyse-run logging for dissertation auditability."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("trustmind.analyse")

_LOG_DIR = Path(__file__).resolve().parents[3] / "knowledge_base" / "logs" / "analyse"
_JSONL_PATH = _LOG_DIR / "analyse_runs.jsonl"
_FILE_LOG_PATH = _LOG_DIR / "analyse.log"


def _ensure_handlers() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        handler = logging.FileHandler(_FILE_LOG_PATH, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)


def log_analyse_run(record: dict[str, Any]) -> None:
    """
    Persist one analyse event.

    Logs timestamp, pipeline, retrieved docs, prediction, confidence,
    latency, errors, and abstention events — without storing full user text.
    """
    _ensure_handlers()
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **record,
    }
    # Never persist raw free-text check-ins in the audit log
    payload.pop("text", None)
    payload.pop("prompt", None)

    try:
        with _JSONL_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except OSError:
        logger.exception("Failed to write analyse JSONL log")

    logger.info(
        "pipeline=%s prediction=%s confidence=%s abstained=%s latency_ms=%s error=%s sources=%s",
        payload.get("pipeline_used"),
        payload.get("prediction"),
        payload.get("confidence"),
        payload.get("abstained"),
        payload.get("latency_ms"),
        payload.get("error") or "",
        payload.get("sources"),
    )
