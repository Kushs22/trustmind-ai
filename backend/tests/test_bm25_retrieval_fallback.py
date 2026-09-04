"""BM25-only retrieval fallback when OpenAI embeddings are unavailable."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "backend"
for path in (_REPO, _BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


class Bm25FallbackRetrievalTests(unittest.TestCase):
    def test_retrieve_bm25_only_returns_passages(self) -> None:
        from rag.config import get_rag_config
        from rag.retriever import retrieve_bm25_only

        cfg = get_rag_config()
        if not cfg.bm25_index_path.exists() or not cfg.chunks_jsonl.exists():
            self.skipTest("KB BM25 index / chunks not present in this checkout")

        passages = retrieve_bm25_only(
            "I've been anxious about exams and can't sleep",
            top_k=3,
            config=cfg,
        )
        self.assertGreaterEqual(len(passages), 1)
        self.assertTrue(passages[0].title or passages[0].source)
        self.assertTrue(passages[0].text)
        # BM25-only: no FAISS contribution
        self.assertEqual(passages[0].faiss_score, 0.0)
        self.assertGreater(passages[0].bm25_score, 0.0)

    def test_hybrid_soft_fails_faiss_to_bm25(self) -> None:
        from rag.config import get_rag_config
        from rag.retriever import HybridRetriever

        cfg = get_rag_config()
        if not cfg.bm25_index_path.exists() or not cfg.chunks_jsonl.exists():
            self.skipTest("KB BM25 index / chunks not present in this checkout")

        # Avoid native FAISS load (can segfault in some envs); simulate embedding failure.
        retriever = HybridRetriever(cfg, client=object())
        retriever._faiss_index = object()
        retriever._faiss_id_map = ["chunk-1"]
        with patch(
            "rag.faiss_store.search_vector",
            side_effect=RuntimeError("insufficient_quota"),
        ):
            passages = retriever.retrieve(
                "feeling low and lonely at university",
                top_k=3,
            )
        self.assertGreaterEqual(len(passages), 1)
        self.assertGreater(passages[0].bm25_score, 0.0)
        self.assertEqual(passages[0].faiss_score, 0.0)

    def test_rag_pipeline_service_uses_bm25_without_openai_key(self) -> None:
        from app.config import settings
        from app.services import rag_pipeline_service as rps

        if not (_REPO / "knowledge_base" / "indexes" / "bm25" / "bm25.pkl").exists():
            self.skipTest("KB BM25 index not present")

        fake_json = (
            '{"prediction":"Anxiety","confidence":0.7,'
            '"reasoning":"Exam stress themes.","retrieved_sources":[]}'
        )

        with patch.object(settings, "openai_api_key", ""), patch.object(
            settings, "enable_confidence_calibration", False
        ), patch(
            "app.services.llm_provider.llm_configured",
            return_value=True,
        ), patch(
            "app.services.llm_provider.complete_json",
            return_value=(fake_json, "", "groq"),
        ):
            result = rps.run_rag_pipeline(
                "I feel anxious about coursework and sleep poorly"
            )

        self.assertEqual(result.get("prediction"), "Anxiety")
        self.assertGreaterEqual(len(result.get("retrieved_passages") or []), 1)
        self.assertEqual(result.get("retrieval_mode"), "bm25_only")
        self.assertIn("RAG", (result.get("pipeline_used") or "").upper())

    def test_enrich_depression_noun_adds_kb_terms(self) -> None:
        from rag.query_enrichment import enrich_wellbeing_query

        enriched = enrich_wellbeing_query("I have severe depression")
        lower = enriched.lower()
        self.assertIn("depression", lower)
        self.assertIn("low mood", lower)
        self.assertIn("student", lower)

    def test_prefer_student_guidance_over_literature_pdf(self) -> None:
        from rag.retriever import RetrievedPassage, prefer_student_guidance

        lit = RetrievedPassage(
            source="LIT_ALI_ANX_FINLAND_2025",
            title="Psychiatria Fennica ALI",
            organisation="Psychiatria Fennica",
            similarity_score=0.9,
            text="Finnish student welfare intervention study.",
            chunk_id="lit-1",
        )
        nhs = RetrievedPassage(
            source="NHS_DEP_001",
            title="Depression in adults – Overview",
            organisation="NHS",
            similarity_score=0.4,
            text="NHS overview of depression in adults.",
            chunk_id="nhs-1",
        )
        ranked = prefer_student_guidance(
            [lit, nhs],
            "I have severe depression",
            top_k=1,
        )
        self.assertEqual(ranked[0].source, "NHS_DEP_001")

    def test_research_query_keeps_literature_first(self) -> None:
        from rag.retriever import RetrievedPassage, prefer_student_guidance

        lit = RetrievedPassage(
            source="LIT_ALI_ANX_FINLAND_2025",
            title="Psychiatria Fennica ALI",
            organisation="Psychiatria Fennica",
            similarity_score=0.9,
            text="Finnish student welfare intervention study.",
            chunk_id="lit-1",
        )
        nhs = RetrievedPassage(
            source="NHS_DEP_001",
            title="Depression in adults – Overview",
            organisation="NHS",
            similarity_score=0.4,
            text="NHS overview of depression in adults.",
            chunk_id="nhs-1",
        )
        ranked = prefer_student_guidance(
            [lit, nhs],
            "cite the peer-reviewed research paper",
            top_k=1,
        )
        self.assertEqual(ranked[0].source, "LIT_ALI_ANX_FINLAND_2025")


if __name__ == "__main__":
    unittest.main()
