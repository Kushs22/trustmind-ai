"""
Collect manually approved wellbeing webpages into the TrustMind knowledge base.

Only processes URLs listed in knowledge_base/sources/approved_sources.csv where
approved_for_collection is true. Does not crawl, follow links, or build RAG indexes.
"""

from __future__ import annotations

import csv
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

# Allow running as `python scripts/collect_sources.py` from repo root
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from clean_source_text import (  # noqa: E402
    calculate_content_hash,
    clean_content,
    extract_main_content,
    extract_pdf_text,
)

# ---------------------------------------------------------------------------
# Configuration (edit these values as needed)
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT_SECONDS = 30
USER_AGENT = (
    "TrustMindAI-ResearchCollector/1.0 "
    "(MSc Artificial Intelligence dissertation; UWE Bristol; academic research; "
    "contact: local-dev-only)"
)
REQUEST_DELAY_SECONDS = 2.5
RETRY_COUNT = 3
RETRY_BACKOFF_SECONDS = 2.0
MINIMUM_WORD_COUNT = 80

KB_DIR = ROOT / "knowledge_base"
SOURCES_CSV = KB_DIR / "sources" / "approved_sources.csv"
RAW_DIR = KB_DIR / "raw"
CLEANED_DIR = KB_DIR / "cleaned"
METADATA_DIR = KB_DIR / "metadata"
LOG_DIR = KB_DIR / "logs"
MANIFEST_CSV = METADATA_DIR / "source_manifest.csv"

MANIFEST_COLUMNS = [
    "source_id",
    "organisation",
    "topic",
    "title",
    "source_url",
    "accessed_at",
    "HTTP_status",
    "raw_file",
    "cleaned_file",
    "word_count",
    "character_count",
    "content_hash",
    "extraction_method",
    "collection_status",
    "review_status",
    "error_message",
]


def _setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("trustmind.kb.collect")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(LOG_DIR / "collection.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def load_approved_sources(path: Path = SOURCES_CSV) -> pd.DataFrame:
    """Load the approved source list and keep only collectible rows."""
    if not path.exists():
        raise FileNotFoundError(f"Approved sources file not found: {path}")
    df = pd.read_csv(path)
    required = {
        "source_id",
        "organisation",
        "topic",
        "title",
        "url",
        "country",
        "source_type",
        "approved_for_collection",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"approved_sources.csv missing columns: {sorted(missing)}")

    def _is_true(value: Any) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes", "y"}

    collectible = df[df["approved_for_collection"].map(_is_true)].copy()
    collectible["source_id"] = collectible["source_id"].astype(str).str.strip()
    collectible["url"] = collectible["url"].astype(str).str.strip()
    return collectible.reset_index(drop=True)


def _looks_like_pdf(url: str, content_type: str = "") -> bool:
    ct = (content_type or "").lower()
    if "application/pdf" in ct:
        return True
    return url.lower().split("?", 1)[0].endswith(".pdf")


def fetch_page(
    url: str,
    *,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
    retries: int = RETRY_COUNT,
    logger: logging.Logger | None = None,
) -> tuple[str, bytes | str | None, int | None, str]:
    """
    Download a webpage or PDF with retries.

    Returns (kind, content, http_status, error_message) where kind is
    "html" | "pdf" | "" and content is str for HTML or bytes for PDF.
    """
    log = logger or logging.getLogger("trustmind.kb.collect")
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
    }
    last_error = ""
    last_status: int | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            last_status = response.status_code
            if response.status_code == 200 and response.content:
                content_type = response.headers.get("Content-Type", "")
                if _looks_like_pdf(url, content_type):
                    return "pdf", response.content, response.status_code, ""
                response.encoding = response.apparent_encoding or response.encoding
                if response.text.strip():
                    return "html", response.text, response.status_code, ""
                last_error = "Empty HTML body"
            else:
                last_error = f"HTTP {response.status_code}"
            log.warning("Attempt %s/%s failed for %s (%s)", attempt, retries, url, last_error)
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            log.warning("Attempt %s/%s error for %s (%s)", attempt, retries, url, last_error)

        if attempt < retries:
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    return "", None, last_status, last_error or "fetch_failed"


def save_raw_html(source_id: str, html: str, raw_dir: Path = RAW_DIR) -> Path:
    """Persist original HTML for audit/reproducibility."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{source_id}.html"
    path.write_text(html, encoding="utf-8")
    return path


def save_raw_pdf(source_id: str, pdf_bytes: bytes, raw_dir: Path = RAW_DIR) -> Path:
    """Persist original PDF for audit/reproducibility."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{source_id}.pdf"
    path.write_bytes(pdf_bytes)
    return path


def _front_matter(meta: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in meta.items():
        # Keep YAML simple/quoted where needed
        text = str(value).replace('"', '\\"')
        if any(ch in text for ch in [":", "#", "{", "}", "[", "]", ","]) or text != text.strip():
            lines.append(f'{key}: "{text}"')
        else:
            lines.append(f"{key}: {text}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def save_markdown(
    *,
    source_row: pd.Series,
    title: str,
    body_markdown: str,
    accessed_at: str,
    content_hash: str,
    cleaned_dir: Path = CLEANED_DIR,
) -> Path:
    """Write cleaned Markdown with YAML front matter."""
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    source_id = str(source_row["source_id"])
    meta = {
        "source_id": source_id,
        "title": title,
        "organisation": source_row["organisation"],
        "topic": source_row["topic"],
        "source_type": source_row["source_type"],
        "country": source_row["country"],
        "source_url": source_row["url"],
        "accessed_at": accessed_at,
        "content_hash": content_hash,
        "review_status": "pending",
    }
    path = cleaned_dir / f"{source_id}.md"
    path.write_text(_front_matter(meta) + body_markdown.strip() + "\n", encoding="utf-8")
    return path


def _load_manifest(path: Path = MANIFEST_CSV) -> pd.DataFrame:
    if path.exists():
        df = pd.read_csv(path)
        for col in MANIFEST_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[MANIFEST_COLUMNS]
    return pd.DataFrame(columns=MANIFEST_COLUMNS)


def update_manifest(row: dict[str, Any], path: Path = MANIFEST_CSV) -> pd.DataFrame:
    """Upsert a single source row into the manifest CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df = _load_manifest(path)
    source_id = str(row["source_id"])
    df = df[df["source_id"].astype(str) != source_id]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df = df[MANIFEST_COLUMNS]
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)
    return df


def _existing_success_by_url_or_hash(
    manifest: pd.DataFrame,
    url: str,
    content_hash: str | None = None,
) -> pd.Series | None:
    if manifest.empty:
        return None
    success = manifest[manifest["collection_status"].astype(str) == "success"].copy()
    if success.empty:
        return None
    by_url = success[success["source_url"].astype(str).str.strip() == url.strip()]
    if not by_url.empty:
        return by_url.iloc[-1]
    if content_hash:
        by_hash = success[success["content_hash"].astype(str) == content_hash]
        if not by_hash.empty:
            return by_hash.iloc[-1]
    return None


def collect_source(
    source_row: pd.Series,
    *,
    logger: logging.Logger,
    force: bool = False,
) -> dict[str, Any]:
    """Collect, clean, and record one approved source."""
    source_id = str(source_row["source_id"]).strip()
    url = str(source_row["url"]).strip()
    accessed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = _load_manifest()

    if not force:
        prior = _existing_success_by_url_or_hash(manifest, url)
        if prior is not None and str(prior.get("source_id")) == source_id:
            logger.info("Skipping %s — already collected successfully for this URL", source_id)
            return prior.to_dict()

    kind, content, status, fetch_error = fetch_page(url, logger=logger)
    if content is None:
        row = {
            "source_id": source_id,
            "organisation": source_row["organisation"],
            "topic": source_row["topic"],
            "title": source_row["title"],
            "source_url": url,
            "accessed_at": accessed_at,
            "HTTP_status": status if status is not None else "",
            "raw_file": "",
            "cleaned_file": "",
            "word_count": 0,
            "character_count": 0,
            "content_hash": "",
            "extraction_method": "",
            "collection_status": "failed",
            "review_status": "pending",
            "error_message": fetch_error,
        }
        update_manifest(row)
        return row

    if kind == "pdf":
        assert isinstance(content, (bytes, bytearray))
        raw_path = save_raw_pdf(source_id, bytes(content))
        extracted = extract_pdf_text(bytes(content), fallback_title=str(source_row["title"]))
    else:
        assert isinstance(content, str)
        raw_path = save_raw_html(source_id, content)
        extracted = extract_main_content(content, fallback_title=str(source_row["title"]))
    body = clean_content(extracted.markdown)
    content_hash = calculate_content_hash(body)

    # Duplicate content from another source_id / URL
    if not force:
        prior = _existing_success_by_url_or_hash(manifest, url, content_hash)
        if prior is not None and str(prior.get("source_id")) != source_id:
            row = {
                "source_id": source_id,
                "organisation": source_row["organisation"],
                "topic": source_row["topic"],
                "title": extracted.title or source_row["title"],
                "source_url": url,
                "accessed_at": accessed_at,
                "HTTP_status": status,
                "raw_file": str(raw_path.relative_to(ROOT)),
                "cleaned_file": "",
                "word_count": extracted.word_count,
                "character_count": extracted.character_count,
                "content_hash": content_hash,
                "extraction_method": extracted.extraction_method,
                "collection_status": "duplicate",
                "review_status": "pending",
                "error_message": f"Duplicate of {prior.get('source_id')}",
            }
            update_manifest(row)
            logger.warning("%s flagged as duplicate of %s", source_id, prior.get("source_id"))
            return row

    if extracted.word_count < MINIMUM_WORD_COUNT or not body.strip():
        row = {
            "source_id": source_id,
            "organisation": source_row["organisation"],
            "topic": source_row["topic"],
            "title": extracted.title or source_row["title"],
            "source_url": url,
            "accessed_at": accessed_at,
            "HTTP_status": status,
            "raw_file": str(raw_path.relative_to(ROOT)),
            "cleaned_file": "",
            "word_count": extracted.word_count,
            "character_count": extracted.character_count,
            "content_hash": content_hash,
            "extraction_method": extracted.extraction_method,
            "collection_status": "failed",
            "review_status": "pending",
            "error_message": (
                f"Extracted text too short ({extracted.word_count} words; "
                f"minimum {MINIMUM_WORD_COUNT})"
            ),
        }
        update_manifest(row)
        logger.error("%s extraction too short", source_id)
        return row

    cleaned_path = save_markdown(
        source_row=source_row,
        title=extracted.title or str(source_row["title"]),
        body_markdown=body,
        accessed_at=accessed_at,
        content_hash=content_hash,
    )
    # Recompute counts after final clean
    final_words = len(body.split())
    row = {
        "source_id": source_id,
        "organisation": source_row["organisation"],
        "topic": source_row["topic"],
        "title": extracted.title or source_row["title"],
        "source_url": url,
        "accessed_at": accessed_at,
        "HTTP_status": status,
        "raw_file": str(raw_path.relative_to(ROOT)),
        "cleaned_file": str(cleaned_path.relative_to(ROOT)),
        "word_count": final_words,
        "character_count": len(body),
        "content_hash": content_hash,
        "extraction_method": extracted.extraction_method,
        "collection_status": "success",
        "review_status": "pending",
        "error_message": "",
    }
    update_manifest(row)
    logger.info(
        "Collected %s (%s words) → %s [review_status=pending]",
        source_id,
        final_words,
        cleaned_path.name,
    )
    return row


def collect_all_approved_sources(*, force: bool = False) -> pd.DataFrame:
    """Collect every approved source URL and return the updated manifest."""
    logger = _setup_logging()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_DIR.mkdir(parents=True, exist_ok=True)

    sources = load_approved_sources()
    logger.info("Loaded %s approved source(s) for collection", len(sources))
    if sources.empty:
        logger.warning("No sources with approved_for_collection=true")
        return _load_manifest()

    results: list[dict[str, Any]] = []
    for idx, (_, row) in enumerate(sources.iterrows()):
        if idx > 0:
            time.sleep(REQUEST_DELAY_SECONDS)
        try:
            result = collect_source(row, logger=logger, force=force)
            results.append(result)
        except Exception as exc:  # noqa: BLE001 — continue collecting remaining sources
            logger.exception("Unhandled error for %s", row.get("source_id"))
            fail = {
                "source_id": row.get("source_id"),
                "organisation": row.get("organisation"),
                "topic": row.get("topic"),
                "title": row.get("title"),
                "source_url": row.get("url"),
                "accessed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "HTTP_status": "",
                "raw_file": "",
                "cleaned_file": "",
                "word_count": 0,
                "character_count": 0,
                "content_hash": "",
                "extraction_method": "",
                "collection_status": "failed",
                "review_status": "pending",
                "error_message": f"unhandled: {type(exc).__name__}: {exc}",
            }
            update_manifest(fail)
            results.append(fail)

    manifest = _load_manifest()
    logger.info(
        "Collection finished. success=%s failed=%s duplicate=%s",
        int((manifest["collection_status"] == "success").sum()),
        int((manifest["collection_status"] == "failed").sum()),
        int((manifest["collection_status"] == "duplicate").sum()),
    )
    return manifest


def main() -> None:
    force = "--force" in sys.argv
    collect_all_approved_sources(force=force)


if __name__ == "__main__":
    main()
