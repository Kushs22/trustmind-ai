"""Hybrid BM25 + FAISS retrieval with Reciprocal Rank Fusion."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from rag.bm25_store import load_bm25, search_keywords
from rag.chunking import Chunk, load_chunks
from rag.config import RagConfig, get_rag_config
from rag.query_enrichment import enrich_wellbeing_query

logger = logging.getLogger(__name__)

# Short personal check-ins should surface NHS / charity pages, not literature PDFs.
_RESEARCH_QUERY_CUES = (
    "research paper",
    "peer-reviewed",
    "peer reviewed",
    "literature",
    "journal article",
    "academic paper",
    "cite sources",
    "cite the paper",
)
_GUIDANCE_SOURCE_PREFIXES = (
    "NHS_",
    "MIND_",
    "SM_",
    "STUDENTMINDS",
    "YM_",
    "YOUNGMINDS",
    "UWE_",
    "SAM_",
    "SAMARITANS",
    "PAPYRUS",
)
_GUIDANCE_ORG_NEEDLES = (
    "nhs",
    "mind",
    "student minds",
    "youngminds",
    "young minds",
    "samaritans",
    "uwe",
)


@dataclass
class RetrievedPassage:
    """A ranked passage returned to the prompt builder / caller."""

    source: str
    title: str
    organisation: str
    similarity_score: float
    text: str
    chunk_id: str = ""
    topic: str = ""
    source_url: str = ""
    bm25_score: float = 0.0
    faiss_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "title": self.title,
            "organisation": self.organisation,
            "similarity_score": self.similarity_score,
            "text": self.text,
            "chunk_id": self.chunk_id,
            "topic": self.topic,
            "source_url": self.source_url,
            "bm25_score": self.bm25_score,
            "faiss_score": self.faiss_score,
        }


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    *,
    rrf_k: int = 60,
) -> list[tuple[str, float]]:
    """
    Merge multiple ranked result lists with RRF.

    Each list item must include chunk_id and rank (1-based).
    """
    scores: dict[str, float] = {}
    for results in ranked_lists:
        for item in results:
            chunk_id = str(item["chunk_id"])
            rank = int(item.get("rank", 0))
            if rank <= 0:
                continue
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)


def query_asks_for_research(query: str) -> bool:
    """True when the user is explicitly asking for papers / literature."""
    lower = (query or "").lower()
    return any(cue in lower for cue in _RESEARCH_QUERY_CUES)


def is_literature_source(source_id: str) -> bool:
    return (source_id or "").upper().startswith("LIT_")


def is_guidance_source(source_id: str, organisation: str = "") -> bool:
    """Student-facing official / charity guidance (NHS, Mind, Student Minds…)."""
    sid = (source_id or "").upper()
    if is_literature_source(sid):
        return False
    if any(sid.startswith(prefix) for prefix in _GUIDANCE_SOURCE_PREFIXES):
        return True
    org = (organisation or "").lower()
    return any(needle in org for needle in _GUIDANCE_ORG_NEEDLES)


def prefer_student_guidance(
    passages: list[RetrievedPassage],
    query: str,
    top_k: int,
) -> list[RetrievedPassage]:
    """
    Keep RRF order, but put NHS/charity pages before LIT_* PDFs on personal
    check-ins. Research-seeking queries keep the raw ranking.
    """
    if query_asks_for_research(query) or not passages:
        return passages[:top_k]
    guidance: list[RetrievedPassage] = []
    other: list[RetrievedPassage] = []
    literature: list[RetrievedPassage] = []
    for passage in passages:
        if is_literature_source(passage.source):
            literature.append(passage)
        elif is_guidance_source(passage.source, passage.organisation):
            guidance.append(passage)
        else:
            other.append(passage)
    return (guidance + other + literature)[:top_k]


class HybridRetriever:
    """BM25 + FAISS hybrid retriever with RRF ranking."""

    def __init__(
        self,
        config: RagConfig | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        self.config = config or get_rag_config()
        self.client = client
        self._chunks_by_id: dict[str, Chunk] | None = None
        self._faiss_index = None
        self._faiss_id_map: list[str] | None = None
        self._bm25_payload: dict[str, Any] | None = None

    def _ensure_loaded(self, *, need_faiss: bool = True) -> None:
        if self._chunks_by_id is None:
            chunks = load_chunks(self.config.chunks_jsonl)
            self._chunks_by_id = {c.chunk_id: c for c in chunks}
        if self._bm25_payload is None:
            self._bm25_payload = load_bm25(self.config)
        # FAISS is optional — missing index or failed load must not block BM25.
        # Import lazily so BM25-only demos never hard-depend on the native FAISS lib.
        if need_faiss and self._faiss_index is None and self._faiss_id_map is None:
            try:
                from rag.faiss_store import load_index

                self._faiss_index, self._faiss_id_map = load_index(self.config)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "FAISS index unavailable — BM25-only retrieval: %s",
                    exc,
                )
                self._faiss_index = False  # sentinel: do not retry every call
                self._faiss_id_map = []

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        *,
        allow_faiss: bool = True,
    ) -> list[RetrievedPassage]:
        """
        Hybrid retrieve Top-K passages for a user query.

        1) BM25 search  2) FAISS search (optional)  3) RRF merge  4) dedupe  5) Top-K

        FAISS needs a live OpenAI embedding call for the query. When that fails
        (quota, missing key, network), we soft-fail and return BM25-only hits so
        Mode B still surfaces trusted KB passages.
        """
        self._ensure_loaded(need_faiss=allow_faiss)
        assert self._chunks_by_id is not None
        cfg = self.config
        k = top_k or cfg.top_k
        search_query = enrich_wellbeing_query(query)

        bm25_hits = search_keywords(
            search_query,
            top_k=cfg.bm25_candidate_k,
            config=cfg,
            payload=self._bm25_payload,
        )
        faiss_hits: list[dict[str, Any]] = []
        faiss_error = ""
        faiss_ready = (
            allow_faiss
            and self._faiss_index not in (None, False)
            and bool(self._faiss_id_map)
        )
        if faiss_ready:
            try:
                from rag.faiss_store import search_vector

                faiss_hits = search_vector(
                    search_query,
                    top_k=cfg.faiss_candidate_k,
                    config=cfg,
                    client=self.client,
                    index=self._faiss_index,
                    id_map=self._faiss_id_map,
                )
            except Exception as exc:  # noqa: BLE001
                faiss_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "FAISS/embedding search failed — falling back to BM25-only: %s",
                    faiss_error,
                )

        ranked_lists = [bm25_hits]
        if faiss_hits:
            ranked_lists.append(faiss_hits)
        fused = reciprocal_rank_fusion(ranked_lists, rrf_k=cfg.rrf_k)
        bm25_scores = {h["chunk_id"]: float(h["score"]) for h in bm25_hits}
        faiss_scores = {h["chunk_id"]: float(h["score"]) for h in faiss_hits}

        passages: list[RetrievedPassage] = []
        seen: set[str] = set()
        # Scan past top_k so a later NHS hit can outrank an early LIT_* PDF.
        scan_limit = max(k * 4, 16)
        for chunk_id, rrf_score in fused:
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            chunk = self._chunks_by_id.get(chunk_id)
            if chunk is None:
                continue
            passages.append(
                RetrievedPassage(
                    source=chunk.source_id,
                    title=chunk.title,
                    organisation=chunk.organisation,
                    similarity_score=float(rrf_score),
                    text=chunk.text,
                    chunk_id=chunk.chunk_id,
                    topic=chunk.topic,
                    source_url=chunk.source_url,
                    bm25_score=bm25_scores.get(chunk_id, 0.0),
                    faiss_score=faiss_scores.get(chunk_id, 0.0),
                )
            )
            if len(passages) >= scan_limit:
                break

        ranked = prefer_student_guidance(passages, query, k)
        mode = "hybrid" if faiss_hits else "bm25_only"
        logger.info(
            "Hybrid retrieve: mode=%s bm25=%s faiss=%s fused_top=%s query_chars=%s%s",
            mode,
            len(bm25_hits),
            len(faiss_hits),
            len(ranked),
            len(query),
            f" faiss_error={faiss_error}" if faiss_error else "",
        )
        return ranked


def retrieve_bm25_only(
    query: str,
    top_k: int | None = None,
    config: RagConfig | None = None,
) -> list[RetrievedPassage]:
    """Lexical-only retrieval — no OpenAI embeddings required."""
    return HybridRetriever(config=config).retrieve(
        query, top_k=top_k, allow_faiss=False
    )


def retrieve(query: str, top_k: int | None = None, config: RagConfig | None = None) -> list[RetrievedPassage]:
    """Module-level convenience wrapper."""
    return HybridRetriever(config=config).retrieve(query, top_k=top_k)
