#!/usr/bin/env python3
"""Chunk approved (or pending cleaned) knowledge-base documents for RAG."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.chunking import chunk_all_documents, save_chunks  # noqa: E402
from rag.config import get_rag_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk TrustMind knowledge-base documents")
    parser.add_argument("--force", action="store_true", help="Overwrite existing chunks.jsonl")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    cfg = get_rag_config()

    if cfg.chunks_jsonl.exists() and not args.force:
        logging.info("Chunks already exist at %s (pass --force to rebuild)", cfg.chunks_jsonl)
        return

    chunks = chunk_all_documents(cfg)
    if not chunks:
        logging.error("No chunks produced — check knowledge_base/review/approved or cleaned/")
        sys.exit(1)

    save_chunks(chunks, cfg.chunks_jsonl)
    # Also write one markdown preview file per source for inspection
    by_source: dict[str, list] = {}
    for chunk in chunks:
        by_source.setdefault(chunk.source_id, []).append(chunk)

    for source_id, source_chunks in by_source.items():
        path = cfg.chunks_dir / f"{source_id}.jsonl"
        save_chunks(source_chunks, path)

    logging.info(
        "Wrote %s chunks (%s sources) → %s",
        len(chunks),
        len(by_source),
        cfg.chunks_jsonl,
    )


if __name__ == "__main__":
    main()
