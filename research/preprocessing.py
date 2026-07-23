"""
SWMH text preprocessing for TrustMind AI experiments.

Applies the pipeline documented in 01_SWMH_EDA.ipynb:
UTF-8 load, HTML decode, URL/username removal, whitespace normalisation,
duplicate removal, and optional head truncation for long posts.

Semantic stemming / stop-word removal is intentionally omitted so
emotionally meaningful terms (e.g. empty, hopeless, panic) are preserved.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import pandas as pd

# Reddit / web noise patterns
URL_RE = re.compile(
    r"https?://\S+|www\.\S+",
    flags=re.IGNORECASE,
)
USER_RE = re.compile(
    r"(?:(?<=\s)|^)(?:/?u/|@)[A-Za-z0-9_-]+",
    flags=re.IGNORECASE,
)
WHITESPACE_RE = re.compile(r"\s+")

REQUIRED_COLUMNS = ("text", "label")
DEFAULT_MAX_WORDS = 512


def clean_text(text: Any) -> str:
    """Clean a single post body for modelling."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""

    cleaned = html.unescape(str(text))
    cleaned = URL_RE.sub(" ", cleaned)
    cleaned = USER_RE.sub(" [USER] ", cleaned)
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def truncate_words(text: str, max_words: int = DEFAULT_MAX_WORDS) -> tuple[str, bool]:
    """Head-preserving word truncation. Returns (text, was_truncated)."""
    words = text.split()
    if len(words) <= max_words:
        return text, False
    return " ".join(words[:max_words]), True


def preprocess_dataframe(
    df: pd.DataFrame,
    *,
    max_words: int = DEFAULT_MAX_WORDS,
    drop_duplicates: bool = True,
    truncate: bool = True,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Preprocess an SWMH split.

    Returns cleaned DataFrame with columns: text, label, word_count, truncated
    and a stats dict for audit logging.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    out = df[list(REQUIRED_COLUMNS)].copy()
    n_before = len(out)

    out["text"] = out["text"].map(clean_text)
    out["label"] = out["label"].astype(str).str.strip()

    empty_mask = out["text"].str.len() == 0
    n_empty = int(empty_mask.sum())
    out = out.loc[~empty_mask].copy()

    n_dupes = 0
    if drop_duplicates:
        n_dupes = int(out.duplicated(subset=["text", "label"]).sum())
        out = out.drop_duplicates(subset=["text", "label"], keep="first").reset_index(drop=True)

    truncated_flags: list[bool] = []
    word_counts: list[int] = []
    texts: list[str] = []

    for text in out["text"]:
        word_counts.append(len(text.split()))
        if truncate:
            truncated_text, was_truncated = truncate_words(text, max_words=max_words)
            texts.append(truncated_text)
            truncated_flags.append(was_truncated)
        else:
            texts.append(text)
            truncated_flags.append(False)

    out["text"] = texts
    out["word_count"] = word_counts
    out["truncated"] = truncated_flags

    # After truncation, re-check exact duplicates
    if drop_duplicates:
        post_trunc_dupes = int(out.duplicated(subset=["text", "label"]).sum())
        if post_trunc_dupes:
            n_dupes += post_trunc_dupes
            out = out.drop_duplicates(subset=["text", "label"], keep="first").reset_index(drop=True)

    stats = {
        "rows_before": n_before,
        "rows_after": len(out),
        "empty_removed": n_empty,
        "duplicates_removed": n_dupes,
        "truncated_posts": int(out["truncated"].sum()),
        "mean_word_count": float(out["word_count"].mean()) if len(out) else 0.0,
        "median_word_count": float(out["word_count"].median()) if len(out) else 0.0,
    }
    return out, stats


def remove_leakage(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """
    Drop train rows whose (text, label) also appear in validation or test,
    to reduce train→eval leakage from cross-split duplicates.
    """
    eval_keys = set(
        zip(
            pd.concat([validation["text"], test["text"]], ignore_index=True),
            pd.concat([validation["label"], test["label"]], ignore_index=True),
        )
    )
    before = len(train)
    mask = [
        (text, label) not in eval_keys
        for text, label in zip(train["text"], train["label"])
    ]
    cleaned_train = train.loc[mask].reset_index(drop=True)
    stats = {
        "train_before": before,
        "train_after": len(cleaned_train),
        "leakage_removed": before - len(cleaned_train),
    }
    return cleaned_train, validation, test, stats


def load_swmh_split(path: Path) -> pd.DataFrame:
    """Load a CSV with UTF-8 encoding (fallback for mixed encodings)."""
    try:
        return pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="utf-8-sig")


def preprocess_swmh_directory(
    data_dir: Path,
    output_dir: Path | None = None,
    *,
    max_words: int = DEFAULT_MAX_WORDS,
    remove_cross_split_leakage: bool = True,
) -> dict[str, Any]:
    """
    Preprocess train/val/test CSVs under data_dir and write cleaned files.

    Output files: train_clean.csv, val_clean.csv, test_clean.csv
    Modelling columns remain text + label; audit columns are also saved.
    """
    data_dir = Path(data_dir)
    output_dir = Path(output_dir) if output_dir else data_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    split_files = {
        "train": data_dir / "train.csv",
        "validation": data_dir / "val.csv",
        "test": data_dir / "test.csv",
    }
    for name, path in split_files.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing {name} split: {path}")

    processed: dict[str, pd.DataFrame] = {}
    all_stats: dict[str, Any] = {}

    for name, path in split_files.items():
        raw = load_swmh_split(path)
        cleaned, stats = preprocess_dataframe(raw, max_words=max_words)
        processed[name] = cleaned
        all_stats[name] = stats

    if remove_cross_split_leakage:
        train, val, test, leak_stats = remove_leakage(
            processed["train"],
            processed["validation"],
            processed["test"],
        )
        processed["train"] = train
        processed["validation"] = val
        processed["test"] = test
        all_stats["leakage"] = leak_stats

    out_map = {
        "train": output_dir / "train_clean.csv",
        "validation": output_dir / "val_clean.csv",
        "test": output_dir / "test_clean.csv",
    }
    for name, out_path in out_map.items():
        processed[name].to_csv(out_path, index=False, encoding="utf-8")

    all_stats["output_dir"] = str(output_dir)
    all_stats["output_files"] = {k: str(v) for k, v in out_map.items()}
    return all_stats


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    stats = preprocess_swmh_directory(root / "datasets" / "swmh")
    for key, value in stats.items():
        print(f"{key}: {value}")
