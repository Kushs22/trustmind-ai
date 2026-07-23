"""
Text extraction and cleaning helpers for TrustMind AI knowledge-base collection.

Removes navigation, cookies, scripts, and chrome while preserving article meaning.
Does not invent, rewrite, or clinically expand source content.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

from bs4 import BeautifulSoup, NavigableString, Tag

# Tags removed entirely (including content)
STRIP_TAGS = (
    "script",
    "style",
    "noscript",
    "svg",
    "iframe",
    "form",
    "nav",
    "footer",
    "header",
    "aside",
    "button",
    "input",
    "select",
    "textarea",
    "template",
)

# Attribute/class/id fragments that usually indicate non-article chrome
NOISE_PATTERNS = (
    "cookie",
    "consent",
    "newsletter",
    "breadcrumb",
    "share",
    "social",
    "related",
    "promo",
    "banner",
    "advert",
    "sidebar",
    "menu",
    "nav-",
    "navigation",
    "footer",
    "header",
    "skip-link",
    "global-header",
    "global-footer",
    "nhsuk-header",
    "nhsuk-footer",
    "nhsuk-breadcrumb",
    "nhsuk-back-link",
    "nhsuk-skip-link",
    "beta-banner",
)

WHITESPACE_RE = re.compile(r"[ \t]+")
MULTI_BLANK_RE = re.compile(r"\n{3,}")


@dataclass
class ExtractedDocument:
    """Cleaned article content extracted from HTML."""

    title: str
    markdown: str
    extraction_method: str
    word_count: int
    character_count: int


def calculate_content_hash(text: str) -> str:
    """Return SHA-256 hex digest of normalised text."""
    normalised = re.sub(r"\s+", " ", text or "").strip().encode("utf-8")
    return hashlib.sha256(normalised).hexdigest()


def _attr_blob(tag: Tag) -> str:
    parts: list[str] = []
    attrs = getattr(tag, "attrs", None)
    if not isinstance(attrs, dict):
        return ""
    for key in ("id", "class", "role"):
        val = attrs.get(key)
        if isinstance(val, list):
            parts.extend(str(v) for v in val)
        elif val:
            parts.append(str(val))
    return " ".join(parts).lower()


def _looks_like_noise(tag: Tag) -> bool:
    if not isinstance(tag, Tag):
        return False
    blob = _attr_blob(tag)
    return any(token in blob for token in NOISE_PATTERNS)


def _prefer_main_container(soup: BeautifulSoup) -> Tag:
    """Pick the most likely main article container without inventing content."""
    for selector in (
        "main#maincontent",
        "main[role='main']",
        "article",
        "main",
        "#maincontent",
        ".nhsuk-main-wrapper",
        "#content",
    ):
        node = soup.select_one(selector)
        if node and isinstance(node, Tag):
            return node
    body = soup.body
    if body and isinstance(body, Tag):
        return body
    return soup


def _remove_noise(root: Tag) -> None:
    # Collect first, then decompose, so iteration stays stable.
    to_remove: list[Tag] = []
    for tag in root.find_all(True):
        if not isinstance(tag, Tag):
            continue
        name = (tag.name or "").lower()
        if name in STRIP_TAGS or _looks_like_noise(tag):
            to_remove.append(tag)
    for tag in to_remove:
        try:
            tag.decompose()
        except Exception:  # noqa: BLE001
            continue

def _heading_level(tag: Tag) -> int | None:
    name = (tag.name or "").lower()
    if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        return int(name[1])
    return None


def _inline_text(tag: Tag) -> str:
    parts: list[str] = []
    for child in tag.descendants:
        if isinstance(child, NavigableString):
            text = str(child)
            if text:
                parts.append(text)
        elif isinstance(child, Tag) and child.name == "br":
            parts.append("\n")
    text = "".join(parts)
    text = WHITESPACE_RE.sub(" ", text)
    text = text.replace("\n ", "\n").strip()
    return text


def _list_markdown(tag: Tag, ordered: bool) -> list[str]:
    lines: list[str] = []
    index = 1
    for li in tag.find_all("li", recursive=False):
        item = _inline_text(li)
        if not item:
            continue
        prefix = f"{index}." if ordered else "-"
        lines.append(f"{prefix} {item}")
        index += 1
    return lines


def _blocks_to_markdown(root: Tag, page_title: str) -> str:
    """Convert retained block elements into Markdown, preserving order."""
    lines: list[str] = []
    seen_h1 = False

    # Prefer direct meaningful descendants in document order
    candidates: Iterable[Tag] = root.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "li", "blockquote"],
        recursive=True,
    )

    # Skip nested list items handled by parent list
    for tag in candidates:
        if not isinstance(tag, Tag):
            continue
        parent_names = {p.name for p in tag.parents if isinstance(p, Tag)}
        if tag.name == "li" and ("ul" in parent_names or "ol" in parent_names):
            # Only emit via parent ul/ol
            continue
        if tag.name in {"ul", "ol"} and any(p.name in {"ul", "ol"} for p in tag.parents if isinstance(p, Tag)):
            continue

        level = _heading_level(tag)
        if level is not None:
            text = _inline_text(tag)
            if not text:
                continue
            if level == 1:
                seen_h1 = True
            lines.append("#" * level + f" {text}")
            lines.append("")
            continue

        if tag.name == "p":
            text = _inline_text(tag)
            if not text:
                continue
            # Skip very short link-only crumbs
            if len(text.split()) <= 2 and text.lower() in {"home", "menu", "skip to main content"}:
                continue
            lines.append(text)
            lines.append("")
            continue

        if tag.name in {"ul", "ol"}:
            list_lines = _list_markdown(tag, ordered=tag.name == "ol")
            if list_lines:
                lines.extend(list_lines)
                lines.append("")
            continue

        if tag.name == "blockquote":
            text = _inline_text(tag)
            if text:
                for row in text.splitlines() or [text]:
                    lines.append(f"> {row.strip()}")
                lines.append("")

    if not seen_h1 and page_title:
        lines.insert(0, "")
        lines.insert(0, f"# {page_title}")

    markdown = "\n".join(lines).strip()
    markdown = MULTI_BLANK_RE.sub("\n\n", markdown)
    return markdown


def extract_main_content(html: str, fallback_title: str = "") -> ExtractedDocument:
    """
    Extract the main readable article from HTML.

    Uses BeautifulSoup with NHS-oriented main-content selectors. A specialised
    library (e.g. trafilatura) is not required for curated official pages and
    would add a dependency; selector-based extraction keeps provenance clearer.
    """
    soup = BeautifulSoup(html, "lxml")

    title = fallback_title.strip()
    if soup.title and soup.title.string:
        title = soup.title.string.strip() or title
    h1 = soup.find("h1")
    if h1:
        h1_text = _inline_text(h1)
        if h1_text:
            title = h1_text

    root = _prefer_main_container(soup)
    # Work on a copy of the subtree to avoid mutating unrelated parse trees oddly
    root_copy = BeautifulSoup(str(root), "lxml")
    working = root_copy.body if root_copy.body else root_copy
    if not isinstance(working, Tag):
        working = root_copy

    _remove_noise(working)
    markdown = _blocks_to_markdown(working, page_title=title)
    words = markdown.split()
    return ExtractedDocument(
        title=title,
        markdown=markdown,
        extraction_method="beautifulsoup_main_content_selectors",
        word_count=len(words),
        character_count=len(markdown),
    )


def extract_pdf_text(pdf_bytes: bytes, fallback_title: str = "") -> ExtractedDocument:
    """
    Extract plain text from a PDF without rewriting clinical content.

    Uses pypdf page extraction; layout can be imperfect but provenance stays clear.
    """
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(pdf_bytes))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = MULTI_BLANK_RE.sub("\n\n", text).strip()
        if text:
            pages.append(text)

    body = "\n\n".join(pages).strip()
    title = fallback_title.strip() or "PDF document"
    # Prefer first non-empty line as title when short enough
    if body:
        first_line = body.splitlines()[0].strip()
        if 3 <= len(first_line.split()) <= 20:
            title = first_line

    markdown = f"# {title}\n\n{body}".strip() if body else f"# {title}"
    words = markdown.split()
    return ExtractedDocument(
        title=title,
        markdown=markdown,
        extraction_method="pypdf_page_text",
        word_count=len(words),
        character_count=len(markdown),
    )


def clean_content(markdown: str) -> str:
    """Light post-clean of extracted Markdown (no semantic rewriting)."""
    text = (markdown or "").replace("\r\n", "\n").replace("\r", "\n")
    text = MULTI_BLANK_RE.sub("\n\n", text).strip()
    # Drop leftover cookie/banner phrases if they slipped through
    filtered: list[str] = []
    for line in text.splitlines():
        low = line.lower()
        if any(
            phrase in low
            for phrase in (
                "cookie settings",
                "accept all cookies",
                "we use cookies",
                "this website uses cookies",
            )
        ):
            continue
        filtered.append(line)
    return MULTI_BLANK_RE.sub("\n\n", "\n".join(filtered)).strip()
