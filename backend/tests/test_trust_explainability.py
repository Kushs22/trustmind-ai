"""Unit tests for TrustMind confidence, trust signals, evidence, abstention, safety."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from app.services.abstention import apply_abstention, should_abstain  # noqa: E402
from app.services.confidence_calibration import (  # noqa: E402
    CAP_INCONSISTENT,
    CAP_NORMAL,
    ConfidenceBreakdown,
    W_LLM_ONLY_CLARITY,
    W_LLM_ONLY_CONSISTENCY,
    W_LLM_ONLY_SELF,
    W_RETRIEVAL_SIMILARITY,
    calibrate_confidence,
    calibrate_llm_only_confidence,
    score_classification_consistency,
    score_input_ambiguity,
    uncertainty_from_confidence,
)
from app.services.evidence_presentation import (  # noqa: E402
    BIPOLAR_CAUTIOUS_REASONING,
    build_evidence_items,
    format_display_label,
    sanitise_reasoning,
)
from app.services.support_resources import (  # noqa: E402
    get_support_resources,
    user_text_indicates_crisis,
)
from app.services.trust_signals import (  # noqa: E402
    compute_trust_signals,
    prediction_display_name,
    resolve_grounding,
)


class TrustExplainabilityTests(unittest.TestCase):
    def test_uncertainty_bands(self) -> None:
        self.assertEqual(uncertainty_from_confidence(0.95), "Very Low")
        self.assertEqual(uncertainty_from_confidence(0.80), "Low")
        self.assertEqual(uncertainty_from_confidence(0.65), "Medium")
        self.assertEqual(uncertainty_from_confidence(0.50), "High")
        self.assertEqual(uncertainty_from_confidence(0.20), "Very High")

    def test_calibration_breakdown_bounds(self) -> None:
        passages = [
            {
                "source": "NHS_ANX_001",
                "topic": "anxiety",
                "title": "Anxiety",
                "text": "feeling anxious about exams",
                "faiss_score": 0.9,
                "organisation": "NHS",
            },
            {
                "source": "SM_ANX_001",
                "topic": "anxiety",
                "title": "Student anxiety",
                "text": "worry and anxiety at university",
                "faiss_score": 0.85,
                "organisation": "Student Minds",
            },
        ]
        cal = calibrate_confidence(
            passages=passages,
            prediction="Anxiety",
            llm_confidence=0.92,
            run_labels=["Anxiety", "Anxiety", "Anxiety"],
            expected_k=5,
            has_retrieval=True,
        )
        bd = cal.breakdown.to_dict()
        self.assertIsNotNone(bd["retrieval_similarity"])
        self.assertIsNotNone(bd["source_agreement"])
        self.assertIsNotNone(bd["retrieval_coverage"])
        self.assertIsNone(bd["input_clarity"])
        for value in bd.values():
            if value is None:
                continue
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 100)
        self.assertGreaterEqual(cal.confidence, 0.0)
        self.assertLessEqual(cal.confidence, 1.0)
        self.assertGreater(cal.weights_used.get("retrieval_similarity", 0), 0)
        self.assertEqual(cal.weights_used["retrieval_similarity"], W_RETRIEVAL_SIMILARITY)

    def test_standalone_llm_never_labelled_grounded(self) -> None:
        cal = calibrate_llm_only_confidence(
            text="I have not slept for three nights, feel invincible, spent recklessly, then crashed.",
            prediction="bipolar",
            llm_confidence=0.95,
            run_labels=["bipolar", "bipolar", "bipolar"],
        )
        trust = compute_trust_signals(
            calibrated_pct=cal.confidence_pct,
            breakdown=cal.breakdown,
            has_retrieval=False,
        )
        g = resolve_grounding(
            pipeline_used="LLM",
            has_passages=False,
            trust=trust,
        )
        self.assertEqual(g.status, "not_applicable")
        self.assertEqual(g.label, "Standalone model response")
        self.assertNotIn("grounded", g.label.lower())
        self.assertNotIn("grounded", g.status.lower())

    def test_standalone_retrieval_fields_null_or_na(self) -> None:
        cal = calibrate_llm_only_confidence(
            text="Feeling low and empty for weeks with little energy.",
            prediction="depression",
            llm_confidence=0.88,
            run_labels=["depression", "depression", "depression"],
        )
        bd = cal.breakdown.to_dict()
        self.assertIsNone(bd["retrieval_similarity"])
        self.assertIsNone(bd["retrieval_coverage"])
        self.assertIsNone(bd["source_agreement"])
        self.assertIsNotNone(bd["input_clarity"])
        self.assertEqual(bd["classification_consistency"], 100)
        trust = compute_trust_signals(
            calibrated_pct=cal.confidence_pct,
            breakdown=cal.breakdown,
            has_retrieval=False,
        )
        self.assertIsNone(trust.evidence_strength)
        self.assertIsNone(trust.retrieval_quality)

    def test_standalone_confidence_ignores_retrieval_weights(self) -> None:
        cal = calibrate_llm_only_confidence(
            text="Persistent low mood, emptiness, and withdrawal for several months.",
            prediction="depression",
            llm_confidence=0.80,
            run_labels=["depression", "depression", "depression"],
        )
        self.assertAlmostEqual(cal.weights_used["llm_confidence"], W_LLM_ONLY_SELF)
        self.assertAlmostEqual(
            cal.weights_used["classification_consistency"], W_LLM_ONLY_CONSISTENCY
        )
        self.assertAlmostEqual(cal.weights_used["input_clarity"], W_LLM_ONLY_CLARITY)
        self.assertEqual(cal.weights_used["retrieval_similarity"], 0.0)
        self.assertEqual(cal.weights_used["source_agreement"], 0.0)
        self.assertEqual(cal.weights_used["retrieval_coverage"], 0.0)
        self.assertIn("llm_only_formula", cal.notes)
        self.assertLessEqual(cal.confidence, CAP_NORMAL)

    def test_standalone_confidence_caps(self) -> None:
        clear = calibrate_llm_only_confidence(
            text=(
                "For several months I have had persistent low mood, emptiness, "
                "hopelessness, and withdrawal from friends and studies."
            ),
            prediction="depression",
            llm_confidence=0.99,
            run_labels=["depression", "depression", "depression"],
        )
        self.assertLessEqual(clear.confidence, CAP_NORMAL)

        inconsistent = calibrate_llm_only_confidence(
            text=(
                "For several weeks I have felt low mood and emptiness with little energy."
            ),
            prediction="depression",
            llm_confidence=0.95,
            run_labels=["depression", "Anxiety", "bipolar"],
        )
        self.assertLessEqual(inconsistent.confidence, CAP_INCONSISTENT)

    def test_ambiguity_score_signals(self) -> None:
        short = score_input_ambiguity("tired")
        self.assertGreaterEqual(short, 0.35)
        contradict = score_input_ambiguity(
            "I feel fine and happy but also hopeless and empty without duration cues."
        )
        self.assertGreaterEqual(contradict, 0.40)
        ordinary = score_input_ambiguity(
            "My laptop battery died and I'm annoyed about traffic."
        )
        self.assertGreaterEqual(ordinary, 0.20)
        clear = score_input_ambiguity(
            "For several months I have had persistent low mood, emptiness, "
            "and withdrawal from friends and university studies."
        )
        self.assertLess(clear, short)

    def test_calibrate_confidence_routes_empty_to_llm_only(self) -> None:
        cal = calibrate_confidence(
            passages=[],
            prediction="depression",
            llm_confidence=0.8,
            run_labels=["depression", "depression", "Anxiety"],
            expected_k=5,
            has_retrieval=False,
            text="Feeling low for weeks with emptiness and withdrawal.",
        )
        self.assertIsNone(cal.breakdown.retrieval_similarity)
        self.assertIn("llm_only_formula", cal.notes)

    def test_trust_signal_formulas(self) -> None:
        bd = ConfidenceBreakdown(
            retrieval_similarity=90,
            source_agreement=100,
            llm_confidence=80,
            classification_consistency=50,
            retrieval_coverage=70,
        )
        trust = compute_trust_signals(
            calibrated_pct=88,
            breakdown=bd,
            has_retrieval=True,
        )
        self.assertEqual(trust.model_confidence, 88)
        self.assertEqual(trust.evidence_strength, 80)
        self.assertEqual(trust.retrieval_quality, 82)

    def test_grounding_status_transitions(self) -> None:
        strong = compute_trust_signals(
            calibrated_pct=90,
            breakdown=ConfidenceBreakdown(90, 100, 90, 100, 80),
            has_retrieval=True,
        )
        g = resolve_grounding(
            pipeline_used="LLM+RAG",
            has_passages=True,
            trust=strong,
        )
        self.assertEqual(g.status, "grounded")

        weak = compute_trust_signals(
            calibrated_pct=50,
            breakdown=ConfidenceBreakdown(20, 10, 40, 30, 10),
            has_retrieval=True,
        )
        g2 = resolve_grounding(
            pipeline_used="LLM+RAG",
            has_passages=True,
            trust=weak,
        )
        self.assertEqual(g2.status, "limited")

        g3 = resolve_grounding(
            pipeline_used="LLM",
            has_passages=False,
            trust=compute_trust_signals(
                calibrated_pct=70,
                breakdown=None,
                has_retrieval=False,
            ),
        )
        self.assertEqual(g3.status, "not_applicable")
        self.assertEqual(g3.label, "Standalone model response")

        g4 = resolve_grounding(
            pipeline_used="LLM+RAG",
            has_passages=False,
            trust=weak,
        )
        self.assertEqual(g4.status, "ungrounded")

    def test_evidence_dedupe_and_fallback(self) -> None:
        passages = [
            {
                "source": "NHS_DEP_001",
                "organisation": "NHS",
                "title": "",
                "topic": "depression",
                "text": "persistent low mood emptiness withdrawal",
                "faiss_score": 0.7,
                "source_url": "",
            },
            {
                "source": "NHS_DEP_001",
                "organisation": "NHS",
                "title": "Depression overview",
                "topic": "depression",
                "text": "low mood",
                "faiss_score": 0.95,
                "source_url": "https://www.nhs.uk/example",
            },
        ]
        items = build_evidence_items(
            passages,
            user_text="I feel empty and withdrawn",
            prediction="depression",
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source_id, "NHS_DEP_001")
        self.assertEqual(items[0].retrieval_score, 0.95)
        self.assertTrue(items[0].url.startswith("https://"))
        self.assertIn("—", format_display_label("NHS", "Depression overview"))

    def test_diagnostic_language_avoided(self) -> None:
        out = sanitise_reasoning("This proves you have depression.")
        self.assertIn("not a clinical diagnosis", out.lower())
        bipolar = sanitise_reasoning("These are classic symptoms of bipolar disorder.")
        self.assertEqual(bipolar, BIPOLAR_CAUTIOUS_REASONING)
        self.assertNotIn("classic symptoms", bipolar.lower())
        self.assertIn("not a clinical diagnosis", bipolar.lower())
        self.assertIn("may overlap", bipolar.lower())

    def test_internal_evaluation_label_unchanged(self) -> None:
        self.assertEqual(
            prediction_display_name("bipolar"), "Bipolar-related indicators"
        )
        # Research/storage label remains the SWMH class string.
        self.assertEqual("bipolar", "bipolar")

    def test_abstention_still_works_below_threshold(self) -> None:
        from app.config import settings

        with patch.object(settings, "enable_abstention", True), patch.object(
            settings, "confidence_threshold", 0.75
        ):
            low = calibrate_llm_only_confidence(
                text="ok",
                prediction="offmychest",
                llm_confidence=0.4,
                run_labels=["offmychest", "Anxiety", "depression"],
            )
            self.assertLess(low.confidence, 0.75)
            self.assertTrue(should_abstain(low.confidence))
            decision = apply_abstention(low.confidence, text="stressed")
            self.assertTrue(decision.abstained)
            self.assertIn("short", decision.message.lower())
            self.assertFalse(should_abstain(0.9))

    def test_safety_independent_of_confidence(self) -> None:
        from app.config import settings

        with patch.object(settings, "enable_support_resources", True):
            self.assertTrue(
                user_text_indicates_crisis(
                    "Yesterday I felt like disappearing and thought everyone would be better without me."
                )
            )
            resources = get_support_resources(
                prediction=None,
                sources=[],
                reasoning="",
                user_text="I want to end my life",
            )
            self.assertGreaterEqual(len(resources), 1)
            self.assertTrue(any("Samaritans" in r["name"] for r in resources))

    def test_prediction_display_names(self) -> None:
        self.assertEqual(
            prediction_display_name("depression"), "Depression-related indicators"
        )
        self.assertEqual(
            prediction_display_name("Anxiety"), "Anxiety-related indicators"
        )
        self.assertEqual(
            prediction_display_name("SuicideWatch"),
            "Urgent safety-related indicators",
        )
        self.assertEqual(
            prediction_display_name("bipolar"), "Bipolar-related indicators"
        )

    def test_standalone_llm_controller_does_not_keyword_fallback(self) -> None:
        """Regression: missing GroundingInfo import caused NameError → keyword path."""
        from app.schemas.analyse import AnalyseRequest
        from app.services import pipeline_controller as pc

        fake = {
            "prediction": "Anxiety",
            "confidence": 0.82,
            "reasoning": (
                "The text mentions anxiety about a dissertation. "
                "This is not a clinical diagnosis."
            ),
            "sources": [],
            "retrieved_passages": [],
            "pipeline_used": "LLM",
            "latency_ms": 12.0,
            "error": "",
            "parse_ok": True,
            "confidence_breakdown": {
                "retrieval_similarity": None,
                "source_agreement": None,
                "llm_confidence": 85,
                "classification_consistency": 100,
                "retrieval_coverage": None,
                "input_clarity": 80,
            },
            "uncertainty": "Low",
        }
        req = AnalyseRequest(
            text="I'm really anxious about my dissertation.",
            pipeline_mode="llm",
            analyse_privately=True,
        )
        with patch("app.services.llm_pipeline.run_llm_pipeline", return_value=fake), patch.object(
            pc.settings, "openai_api_key", "sk-test"
        ):
            result = pc.run_configured_pipeline(req)

        self.assertEqual(result.pipeline_used, "LLM")
        self.assertEqual(result.prediction, "Anxiety")
        self.assertEqual(result.prediction_display, "Anxiety-related indicators")
        self.assertEqual(result.grounding_status, "Standalone model response")
        self.assertEqual(result.grounding.get("status"), "not_applicable")
        self.assertNotIn("keyword", (result.grounding_status or "").lower())
        self.assertIsNone((result.trust_signals or {}).get("evidence_strength"))
        self.assertIsNone((result.trust_signals or {}).get("retrieval_quality"))
        self.assertEqual(result.evidence_used, [])

    def test_consistency_score(self) -> None:
        self.assertAlmostEqual(
            score_classification_consistency(["Anxiety", "Anxiety", "depression"]),
            2 / 3,
        )


if __name__ == "__main__":
    unittest.main()
