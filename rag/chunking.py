"""Document loading and overlapping word-window chunking for TrustMind RAG."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from rag.config import RagConfig, get_rag_config

logger = logging.getLogger(__name__)

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass
class Chunk:
    """One overlapping text window with provenance metadata."""

    chunk_id: str
    source_id: str
    organisation: str
    title: str
    topic: str
    chunk_number: int
    text: str
    source_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_doc(path: Path) -> tuple[dict[str, str], str]:
    """Parse YAML-ish front matter and body from a cleaned KB markdown file."""
    raw = path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(raw)
    meta: dict[str, str] = {}
    body = raw
    if match:
        fm, body = match.group(1), match.group(2)
        for line in fm.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    meta.setdefault("source_id", path.stem)
    meta.setdefault("title", path.stem)
    meta.setdefault("organisation", "")
    meta.setdefault("topic", "")
    meta.setdefault("source_url", "")
    meta.setdefault("review_status", "pending")
    return meta, body.strip()


def list_source_documents(config: RagConfig | None = None) -> list[Path]:
    """
    Return markdown paths to index.

    Prefer knowledge_base/review/approved/.
    If empty and allow_pending_cleaned, use cleaned/ excluding rejected IDs.
    """
    cfg = config or get_rag_config()
    approved = sorted(cfg.approved_dir.glob("*.md"))
    if approved:
        logger.info("Using %s approved document(s) from %s", len(approved), cfg.approved_dir)
        return approved

    if not cfg.allow_pending_cleaned:
        logger.warning("No approved documents and allow_pending_cleaned=False")
        return []

    rejected_ids = {p.stem for p in cfg.rejected_dir.glob("*.md")}
    cleaned: list[Path] = []
    for path in sorted(cfg.cleaned_dir.glob("*.md")):
        if path.stem in rejected_ids:
            continue
        meta, _ = _parse_doc(path)
        if str(meta.get("review_status", "")).lower() == "rejected":
            continue
        cleaned.append(path)

    logger.warning(
        "Approved folder empty — indexing %s cleaned document(s) "
        "(ALLOW_PENDING_CLEANED=true). Promote to review/approved/ before production RAG.",
        len(cleaned),
    )
    return cleaned


def word_chunks(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping word windows."""
    words = text.split()
    if not words:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    step = chunk_size - overlap
    windows: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        windows.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start += step
    return windows


def chunk_document(
    path: Path,
    *,
    chunk_size: int,
    overlap: int,
) -> list[Chunk]:
    """Chunk one markdown document into overlapping windows."""
    meta, body = _parse_doc(path)
    # Drop markdown heading markers lightly for denser retrieval text
    body_clean = re.sub(r"^#+\s*", "", body, flags=re.MULTILINE)
    windows = word_chunks(body_clean, chunk_size, overlap)
    source_id = str(meta.get("source_id") or path.stem)
    chunks: list[Chunk] = []
    for i, text in enumerate(windows, start=1):
        if not text.strip():
            continue
        chunks.append(
            Chunk(
                chunk_id=f"{source_id}__chunk_{i:04d}",
                source_id=source_id,
                organisation=str(meta.get("organisation", "")),
                title=str(meta.get("title", "")),
                topic=str(meta.get("topic", "")),
                chunk_number=i,
                text=text.strip(),
                source_url=str(meta.get("source_url", "")),
            )
        )
    return chunks


def chunk_all_documents(config: RagConfig | None = None) -> list[Chunk]:
    """Chunk every eligible knowledge-base document."""
    cfg = config or get_rag_config()
    docs = list_source_documents(cfg)
    all_chunks: list[Chunk] = []
    for path in docs:
        try:
            doc_chunks = chunk_document(
                path,
                chunk_size=cfg.chunk_size_words,
                overlap=cfg.chunk_overlap_words,
            )
            all_chunks.extend(doc_chunks)
            logger.info("%s → %s chunk(s)", path.name, len(doc_chunks))
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to chunk %s: %s", path, exc)
    return all_chunks


def save_chunks(chunks: Iterable[Chunk], path: Path) -> Path:
    """Persist chunks as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
    return path


def load_chunks(path: Path) -> list[Chunk]:
    """Load chunks from JSONL."""
    if not path.exists():
        raise FileNotFoundError(f"Chunks file not found: {path}")
    chunks: list[Chunk] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            chunks.append(
                Chunk(
                    chunk_id=data["chunk_id"],
                    source_id=data["source_id"],
                    organisation=data.get("organisation", ""),
                    title=data.get("title", ""),
                    topic=data.get("topic", ""),
                    chunk_number=int(data.get("chunk_number", 0)),
                    text=data["text"],
                    source_url=data.get("source_url", ""),
                )
            )
    return chunks
