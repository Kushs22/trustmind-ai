#!/usr/bin/env python3
"""Build the BM25 lexical index from chunk texts."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.bm25_store import build_bm25_index, search_keywords  # noqa: E402
from rag.config import get_rag_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build TrustMind BM25 index")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--demo-query", type=str, default="", help="Optional smoke-test query")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    cfg = get_rag_config()
    path = build_bm25_index(cfg, force=args.force)
    logging.info("BM25 index ready → %s", path)

    if args.demo_query:
        hits = search_keywords(args.demo_query, top_k=3, config=cfg)
        for hit in hits:
            logging.info("hit %s score=%.4f", hit["chunk_id"], hit["score"])


if __name__ == "__main__":
    main()
