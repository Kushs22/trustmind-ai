"""Nonsense input must produce a gentle invite only, and never hide a crisis."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "backend"
for path in (_REPO, _BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.config import settings  # noqa: E402
from app.schemas.analyse import AnalyseRequest  # noqa: E402
from app.services.pipeline_controller import run_configured_pipeline  # noqa: E402

_PASSAGE = {
    "source": "NHS_ANX_001",
    "title": "Anxiety",
    "organisation": "NHS",
    "similarity_score": 0.02,
    "text": "Feeling anxious about exams is common.",
    "chunk_id": "c1",
    "topic": "anxiety",
    "source_url": "https://example.org/anxiety",
    "bm25_score": 0.0,
    "faiss_score": 0.12,
}


def _raw(prediction: str | None, confidence: float) -> dict:
    return {
        "prediction": prediction,
        "confidence": confidence,
        "reasoning": "model reasoning",
        "sources": ["NHS_ANX_001"],
        "retrieved_passages": [dict(_PASSAGE)],
        "pipeline_used": "LLM+RAG",
        "latency_ms": 1.0,
        "retrieval_mode": "hybrid",
    }


def _run(text: str, raw: dict):
    request = AnalyseRequest(text=text, pipeline_mode="rag")
    with (
        patch.object(settings, "openai_api_key", "test-key"),
        patch(
            "app.services.rag_pipeline_service.run_rag_pipeline",
            return_value=raw,
        ),
        patch("app.services.pipeline_controller.log_analyse_run"),
    ):
        return run_configured_pipeline(request)


class NeedsMoreInputTests(unittest.TestCase):
    def test_gibberish_gets_invite_only(self) -> None:
        result = _run("jnbfklsdn", _raw("Anxiety", 0.7))
        self.assertTrue(result.needs_more_input)
        self.assertEqual(result.status, "accepted")
        self.assertIsNone(result.prediction)
        self.assertEqual(result.evidence_used, [])
        self.assertEqual(result.sources_detail, [])
        self.assertEqual(result.sources, [])
        self.assertIsNone(result.support_urgency)
        self.assertIsNone(result.support_urgency_band)
        self.assertEqual(result.trust_summary, "")
        self.assertIn("enough to go on", result.explanation)

    def test_long_gibberish_is_not_an_abstention(self) -> None:
        text = " ".join(["qwrtpsdfgh"] * 20)
        result = _run(text, _raw(None, 0.1))
        self.assertTrue(result.needs_more_input)
        self.assertEqual(result.status, "accepted")
        self.assertNotIn("holding back", result.explanation.lower())

    def test_real_feeling_is_not_flagged(self) -> None:
        result = _run("I feel anxious about work", _raw("Anxiety", 0.8))
        self.assertFalse(result.needs_more_input)
        self.assertIsNotNone(result.support_urgency)

    def test_non_english_crisis_label_is_never_swallowed(self) -> None:
        # No English emotion words, so the English-only low-signal check would
        # otherwise treat this as noise and drop the crisis label.
        result = _run("quiero morir ahora", _raw("SuicideWatch", 0.9))
        self.assertFalse(result.needs_more_input)
        self.assertTrue(result.safety_triggered)

    def test_english_crisis_text_is_never_swallowed(self) -> None:
        result = _run("i want to die", _raw(None, 0.2))
        self.assertFalse(result.needs_more_input)
        self.assertTrue(result.safety_triggered)


class FaissMinScoreTests(unittest.TestCase):
    def _retriever(self):
        from rag.config import RagConfig
        from rag.retriever import HybridRetriever

        cfg = RagConfig(faiss_min_score=0.25)
        retriever = HybridRetriever(config=cfg)
        chunk = SimpleNamespace(
            chunk_id="c1",
            source_id="NHS_ANX_001",
            title="Anxiety",
            organisation="NHS",
            text="Feeling anxious is common.",
            topic="anxiety",
            source_url="https://example.org",
        )
        retriever._chunks_by_id = {"c1": chunk}
        retriever._bm25_payload = {"bm25": None, "chunk_ids": ["c1"]}
        retriever._faiss_index = object()
        retriever._faiss_id_map = ["c1"]
        return retriever

    def test_weak_vector_match_is_dropped(self) -> None:
        retriever = self._retriever()
        with (
            patch("rag.retriever.search_keywords", return_value=[]),
            patch(
                "rag.faiss_store.search_vector",
                return_value=[{"chunk_id": "c1", "score": 0.10, "rank": 1}],
            ),
        ):
            self.assertEqual(retriever.retrieve("jnbfklsdn"), [])

    def test_strong_vector_match_is_kept(self) -> None:
        retriever = self._retriever()
        with (
            patch("rag.retriever.search_keywords", return_value=[]),
            patch(
                "rag.faiss_store.search_vector",
                return_value=[{"chunk_id": "c1", "score": 0.60, "rank": 1}],
            ),
        ):
            passages = retriever.retrieve("I feel anxious")
        self.assertEqual(len(passages), 1)
        self.assertEqual(passages[0].source, "NHS_ANX_001")


if __name__ == "__main__":
    unittest.main()
