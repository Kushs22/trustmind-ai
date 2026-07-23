"""
Validate collected TrustMind knowledge-base documents.

Checks provenance, emptiness, navigation-heavy extraction, duplicates, and
whether emergency guidance keywords appear to have been dropped when present
in the raw HTML. Does not auto-approve documents for RAG.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from clean_source_text import calculate_content_hash  # noqa: E402

KB_DIR = ROOT / "knowledge_base"
SOURCES_CSV = KB_DIR / "sources" / "approved_sources.csv"
MANIFEST_CSV = KB_DIR / "metadata" / "source_manifest.csv"
CLEANED_DIR = KB_DIR / "cleaned"
RAW_DIR = KB_DIR / "raw"
LOG_DIR = KB_DIR / "logs"
REPORT_PATH = LOG_DIR / "validation_report.md"

MINIMUM_WORD_COUNT = 80
MAXIMUM_LINK_DENSITY = 0.45  # warnings if too many markdown links vs words

APPROVED_ORGANISATIONS = {
    "nhs",
    "nhs england",
    "nhs 111 wales",
    "nhs inform scotland",
    "nhs every mind matters",
    "oxford health",
    "leicestershire partnership",
    "east london",
    "cambridgeshire and peterborough",
    "herefordshire and worcestershire",
    "greater manchester mental health",
    "cumbria northumberland tyne and wear",
    "berkshire healthcare",
    "sheffield",
    "homerton",
    "west yorkshire",
    "somerset",
    "bradford",
    "staying safe",
    "mind",
    "student minds",
    "youngminds",
    "young minds",
    "mansion student",
    "jami",
    "birkbeck",
    "university of bath",
    "mental health foundation",
    "harvard",
    "harvard health",
    "medical news today",
    "anxiety uk",
    "md anderson",
    "verywell mind",
    "sheffield mind",
    "mayo clinic",
    "samaritans",
    "samaritans hope",
    "nhs employers",
    "healthier together",
    "papyrus",
    "uwe",
    "uwe bristol",
}

EMERGENCY_HINTS = (
    "999",
    "111",
    "samaritans",
    "emergency",
    "immediate danger",
    "crisis",
    "urgent help",
    "call 999",
    "nhs 111",
)


@dataclass
class CheckResult:
    source_id: str
    status: str  # pass | warning | fail | duplicate | pending_review
    messages: list[str] = field(default_factory=list)


def _read_markdown_parts(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')
    return meta, parts[2].strip()


def _link_density(markdown: str) -> float:
    words = max(len(markdown.split()), 1)
    links = len(re.findall(r"\[([^\]]+)\]\([^)]+\)", markdown))
    bare_urls = len(re.findall(r"https?://", markdown))
    return (links + bare_urls) / words


def validate_document(
    source_id: str,
    *,
    manifest_row: pd.Series | None,
    approved_orgs: set[str] | None = None,
) -> CheckResult:
    """Validate one cleaned document against collection quality rules."""
    orgs = approved_orgs or APPROVED_ORGANISATIONS
    cleaned_path = CLEANED_DIR / f"{source_id}.md"
    messages: list[str] = []

    if manifest_row is not None and str(manifest_row.get("collection_status")) == "duplicate":
        return CheckResult(source_id, "duplicate", ["Marked duplicate in manifest"])
    if manifest_row is not None and str(manifest_row.get("collection_status")) == "failed":
        return CheckResult(
            source_id,
            "fail",
            [f"Collection failed: {manifest_row.get('error_message', '')}"],
        )

    if not cleaned_path.exists():
        return CheckResult(source_id, "fail", [f"Missing cleaned file: {cleaned_path}"])

    meta, body = _read_markdown_parts(cleaned_path)
    if not meta:
        messages.append("Missing YAML front matter")
    if not meta.get("title"):
        messages.append("Page title missing in front matter")
    if not body.strip():
        return CheckResult(source_id, "fail", messages + ["Body is empty"])

    org = (meta.get("organisation") or (manifest_row.get("organisation") if manifest_row is not None else "") or "")
    if org and org.strip().lower() not in orgs and not any(o in org.strip().lower() for o in orgs):
        messages.append(f"Organisation '{org}' is outside the expected approved set")

    if not meta.get("source_url"):
        messages.append("source_url missing")
    if not meta.get("accessed_at"):
        messages.append("accessed_at missing")

    words = body.split()
    if len(words) < MINIMUM_WORD_COUNT:
        return CheckResult(
            source_id,
            "fail",
            messages + [f"Word count too low ({len(words)} < {MINIMUM_WORD_COUNT})"],
        )

    density = _link_density(body)
    if density > MAXIMUM_LINK_DENSITY:
        messages.append(f"High link density ({density:.2f}) — possible navigation residue")

    nav_hits = sum(
        1
        for phrase in ("skip to main content", "cookie settings", "accept all cookies", "main menu")
        if phrase in body.lower()
    )
    if nav_hits:
        messages.append("Possible navigation/cookie text remains in cleaned body")

    # Emergency guidance preservation check vs raw HTML when available
    raw_path = RAW_DIR / f"{source_id}.html"
    if not raw_path.exists():
        pdf_raw = RAW_DIR / f"{source_id}.pdf"
        raw_path = pdf_raw if pdf_raw.exists() else raw_path
    if raw_path.exists() and raw_path.suffix.lower() == ".html":
        raw_lower = raw_path.read_text(encoding="utf-8", errors="ignore").lower()
        body_lower = body.lower()
        raw_has_emergency = any(h in raw_lower for h in EMERGENCY_HINTS)
        body_has_emergency = any(h in body_lower for h in EMERGENCY_HINTS)
        if raw_has_emergency and not body_has_emergency:
            messages.append(
                "Raw HTML appears to contain emergency/crisis guidance that is absent from cleaned text"
            )

    # Hash consistency
    body_hash = calculate_content_hash(body)
    listed_hash = meta.get("content_hash", "")
    if listed_hash and listed_hash != body_hash:
        messages.append("content_hash in front matter does not match body text")

    review_status = meta.get("review_status", "pending")
    if review_status == "pending":
        messages.append("Awaiting human review (review_status=pending)")

    # Decide status
    hard_fail_terms = ("empty", "too low", "missing cleaned")
    if any(any(t in m.lower() for t in hard_fail_terms) for m in messages if "Awaiting" not in m):
        status = "fail"
    elif any("Duplicate" in m or "duplicate" in m for m in messages):
        status = "duplicate"
    elif [m for m in messages if "Awaiting human review" not in m]:
        status = "warning"
    else:
        status = "pending_review" if review_status == "pending" else "pass"

    # If only pending-review message, classify as pending_review / pass-with-pending
    non_pending = [m for m in messages if "Awaiting human review" not in m]
    if not non_pending and review_status == "pending":
        status = "pending_review"
    elif non_pending and status != "fail":
        status = "warning"

    return CheckResult(source_id, status, messages)


def run_validation() -> str:
    """Validate all manifest entries / cleaned files and write a Markdown report."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if MANIFEST_CSV.exists():
        manifest = pd.read_csv(MANIFEST_CSV)
    else:
        manifest = pd.DataFrame()

    source_ids: list[str] = []
    if not manifest.empty and "source_id" in manifest.columns:
        source_ids.extend(manifest["source_id"].astype(str).tolist())
    for path in sorted(CLEANED_DIR.glob("*.md")):
        sid = path.stem
        if sid not in source_ids:
            source_ids.append(sid)

    results: list[CheckResult] = []
    for source_id in source_ids:
        row = None
        if not manifest.empty:
            hit = manifest[manifest["source_id"].astype(str) == source_id]
            if not hit.empty:
                row = hit.iloc[-1]
        results.append(validate_document(source_id, manifest_row=row))

    buckets = {
        "pass": [],
        "pending_review": [],
        "warning": [],
        "fail": [],
        "duplicate": [],
    }
    for result in results:
        buckets.setdefault(result.status, []).append(result)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# TrustMind Knowledge Base — Validation Report",
        "",
        f"Generated at: `{now}`",
        "",
        "## Summary",
        "",
        f"- Passed: **{len(buckets.get('pass', []))}**",
        f"- Awaiting human review: **{len(buckets.get('pending_review', []))}**",
        f"- Warnings: **{len(buckets.get('warning', []))}**",
        f"- Failed: **{len(buckets.get('fail', []))}**",
        f"- Duplicates: **{len(buckets.get('duplicate', []))}**",
        "",
        "Collected documents remain `review_status=pending` until you manually approve them.",
        "Do **not** feed pending/rejected files into the future RAG index.",
        "",
    ]

    def _section(title: str, items: list[CheckResult]) -> None:
        lines.append(f"## {title}")
        lines.append("")
        if not items:
            lines.append("_None_")
            lines.append("")
            return
        for item in items:
            lines.append(f"### {item.source_id} — `{item.status}`")
            if item.messages:
                for msg in item.messages:
                    lines.append(f"- {msg}")
            else:
                lines.append("- No messages")
            lines.append("")

    _section("Passed", buckets.get("pass", []))
    _section("Awaiting human review", buckets.get("pending_review", []))
    _section("Warnings", buckets.get("warning", []))
    _section("Failed", buckets.get("fail", []))
    _section("Duplicates", buckets.get("duplicate", []))

    lines.extend(
        [
            "## Manual approval steps",
            "",
            "1. Open the cleaned Markdown in `knowledge_base/cleaned/`.",
            "2. Read the content and confirm it is accurate, non-truncated, and appropriate.",
            "3. If approved, copy it to `knowledge_base/review/approved/` and set "
            "`review_status: approved` in the YAML front matter and in "
            "`knowledge_base/metadata/source_manifest.csv`.",
            "4. If rejected, move/copy to `knowledge_base/review/rejected/` and set "
            "`review_status: rejected` with a short note.",
            "5. Only approved files should be used in the later RAG stage.",
            "",
        ]
    )

    report = "\n".join(lines)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nReport saved to: {REPORT_PATH}")
    return report


def main() -> None:
    run_validation()


if __name__ == "__main__":
    main()
