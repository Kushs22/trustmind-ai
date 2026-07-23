"""
Central configuration for TrustMind AI RAG experiments and backend Mode B.

Paths are resolved relative to the repository root unless overridden via env.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def _load_env() -> None:
    load_dotenv(ROOT / "research" / ".env")
    load_dotenv(ROOT / "backend" / ".env")
    load_dotenv(ROOT / ".env")


@dataclass
class RagConfig:
    """Configurable RAG hyperparameters and filesystem paths."""

    # Models
    embedding_model: str = "text-embedding-3-small"
    gpt_model: str = "gpt-4.1"
    temperature: float = 0.0
    openai_api_key: str = ""

    # Chunking
    chunk_size_words: int = 500
    chunk_overlap_words: int = 100

    # Retrieval
    top_k: int = 5
    bm25_candidate_k: int = 20
    faiss_candidate_k: int = 20
    rrf_k: int = 60  # Reciprocal Rank Fusion constant

    # Experiment parity with LLM-only baseline
    sample_size: int = 100
    random_seed: int = 42
    sleep_between_calls: float = 0.5

    # Knowledge base document loading
    # Prefer review/approved/; fall back to cleaned/ when empty if allow_pending_cleaned
    allow_pending_cleaned: bool = True

    # Backend Mode B
    use_rag: bool = False

    # Paths (set in __post_init__)
    root: Path = field(default_factory=lambda: ROOT)
    kb_dir: Path = field(default_factory=lambda: ROOT / "knowledge_base")
    approved_dir: Path = field(init=False)
    cleaned_dir: Path = field(init=False)
    rejected_dir: Path = field(init=False)
    chunks_dir: Path = field(init=False)
    embeddings_dir: Path = field(init=False)
    faiss_dir: Path = field(init=False)
    bm25_dir: Path = field(init=False)
    rag_log_dir: Path = field(init=False)
    chunks_jsonl: Path = field(init=False)
    embeddings_npy: Path = field(init=False)
    embeddings_meta_jsonl: Path = field(init=False)
    faiss_index_path: Path = field(init=False)
    bm25_index_path: Path = field(init=False)
    test_csv: Path = field(init=False)
    results_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.approved_dir = self.kb_dir / "review" / "approved"
        self.cleaned_dir = self.kb_dir / "cleaned"
        self.rejected_dir = self.kb_dir / "review" / "rejected"
        self.chunks_dir = self.kb_dir / "chunks"
        self.embeddings_dir = self.kb_dir / "embeddings"
        self.faiss_dir = self.kb_dir / "indexes" / "faiss"
        self.bm25_dir = self.kb_dir / "indexes" / "bm25"
        self.rag_log_dir = self.kb_dir / "logs" / "rag"
        self.chunks_jsonl = self.chunks_dir / "chunks.jsonl"
        self.embeddings_npy = self.embeddings_dir / "embeddings.npy"
        self.embeddings_meta_jsonl = self.embeddings_dir / "embeddings_meta.jsonl"
        self.faiss_index_path = self.faiss_dir / "index.faiss"
        self.bm25_index_path = self.bm25_dir / "bm25.pkl"
        self.test_csv = self.root / "datasets" / "swmh" / "test.csv"
        self.results_dir = self.root / "research" / "results"


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_rag_config() -> RagConfig:
    """Load RAG config from environment (cached)."""
    _load_env()
    return RagConfig(
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        gpt_model=os.getenv("OPENAI_MODEL", os.getenv("GPT_MODEL", "gpt-4.1")),
        temperature=float(os.getenv("OPENAI_TEMPERATURE", os.getenv("TEMPERATURE", "0.0"))),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        chunk_size_words=int(os.getenv("CHUNK_SIZE_WORDS", "500")),
        chunk_overlap_words=int(os.getenv("CHUNK_OVERLAP_WORDS", "100")),
        top_k=int(os.getenv("RAG_TOP_K", "5")),
        bm25_candidate_k=int(os.getenv("BM25_CANDIDATE_K", "20")),
        faiss_candidate_k=int(os.getenv("FAISS_CANDIDATE_K", "20")),
        rrf_k=int(os.getenv("RRF_K", "60")),
        sample_size=int(os.getenv("RAG_SAMPLE_SIZE", "100")),
        random_seed=int(os.getenv("RAG_RANDOM_SEED", "42")),
        sleep_between_calls=float(os.getenv("RAG_SLEEP_BETWEEN_CALLS", "0.5")),
        allow_pending_cleaned=_env_bool("ALLOW_PENDING_CLEANED", True),
        use_rag=_env_bool("USE_RAG", False),
    )
