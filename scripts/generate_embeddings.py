#!/usr/bin/env python3
"""Generate OpenAI embeddings for knowledge-base chunks."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.config import get_rag_config  # noqa: E402
from rag.embeddings_store import generate_and_save_embeddings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed TrustMind RAG chunks")
    parser.add_argument("--force", action="store_true", help="Regenerate even if embeddings exist")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    cfg = get_rag_config()
    try:
        matrix, meta = generate_and_save_embeddings(cfg, force=args.force)
    except Exception as exc:  # noqa: BLE001
        logging.error("Embedding generation failed: %s", exc)
        sys.exit(1)
    logging.info("Done. vectors=%s dim=%s", matrix.shape[0], matrix.shape[1] if matrix.ndim == 2 else "?")
    logging.info("Metadata rows=%s", len(meta))


if __name__ == "__main__":
    main()
