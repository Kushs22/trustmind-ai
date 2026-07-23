#!/usr/bin/env python3
"""Smoke-test hybrid retrieval + optional one-shot RAG classification."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.config import get_rag_config  # noqa: E402
from rag.rag_pipeline import RagPipeline  # noqa: E402
from rag.retriever import HybridRetriever  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo TrustMind hybrid RAG retrieval")
    parser.add_argument(
        "--query",
        type=str,
        default="I feel constantly anxious and my heart races before exams",
    )
    parser.add_argument("--classify", action="store_true", help="Also call GPT with RAG prompt")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    cfg = get_rag_config()
    retriever = HybridRetriever(cfg)
    passages = retriever.retrieve(args.query)
    print(json.dumps([p.to_dict() for p in passages], indent=2, ensure_ascii=False)[:4000])

    if args.classify:
        pipeline = RagPipeline(cfg)
        result = pipeline.run(args.query)
        print(
            json.dumps(
                {
                    "prediction": result["prediction"],
                    "confidence": result["confidence"],
                    "reasoning": result["reasoning"],
                    "retrieved_sources": result["retrieved_sources"],
                    "latency_ms": result["latency_ms"],
                    "error": result["error"],
                },
                indent=2,
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
