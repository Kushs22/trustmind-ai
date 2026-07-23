#!/usr/bin/env python3
"""Build the FAISS vector index from persisted embeddings."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.config import get_rag_config  # noqa: E402
from rag.faiss_store import build_faiss_index, load_index, search_vector  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build TrustMind FAISS index")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--demo-query", type=str, default="", help="Optional smoke-test query")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    cfg = get_rag_config()
    path = build_faiss_index(cfg, force=args.force)
    index, id_map = load_index(cfg)
    logging.info("Loaded index ntotal=%s ids=%s path=%s", index.ntotal, len(id_map), path)

    if args.demo_query:
        hits = search_vector(args.demo_query, top_k=3, config=cfg, index=index, id_map=id_map)
        for hit in hits:
            logging.info("hit %s score=%.4f", hit["chunk_id"], hit["score"])


if __name__ == "__main__":
    main()
