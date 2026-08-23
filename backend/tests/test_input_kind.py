"""Tests for coaching vs first-person input kind detection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.input_kind import (  # noqa: E402
    classify_input_kind,
    coaching_invite_result_fields,
    emotion_theme_heuristic,
)
from app.services.abstention import apply_abstention  # noqa: E402
from app.services.confidence_calibration import (  # noqa: E402
    calibrate_llm_only_confidence,
    score_input_ambiguity,
)


COACH_ONLY = (
    "Act as a compassionate life coach and supportive conversational partner. "
    "Ask me thoughtful questions one at a time. Start by talking to me like a "
    "caring person sitting next to me. Help me explore my goals."
)

COACH_WITH_FEELINGS = (
    "I want you to act as a compassionate, emotionally intelligent life coach "
    "and supportive conversational partner. I am going through a period where I "
    "feel lonely, heartbroken, deeply sad, emotionally stuck, and unable to move "
    "forward with my life. Ask me thoughtful questions one at a time rather than "
    "overwhelming me. Help me explore what happened and who I am struggling to "
    "let go of."
)

LONG_FIRST_PERSON = (
    "For the past few months I have felt lonely most evenings after lectures. "
    "I keep replaying a breakup, feeling heartbroken and empty, and I struggle "
    "to sleep. Motivation for coursework disappeared. Some days I am angry, "
    "some days numb. I am not looking for a diagnosis — I just need a careful "
    "read of how heavy this has been and whether support options might help "
    "while I try to rebuild a bit of routine with friends and family."
)


class InputKindTests(unittest.TestCase):
    def test_pure_coaching_without_story(self) -> None:
        kind = classify_input_kind(COACH_ONLY)
        self.assertTrue(kind.is_coaching_request)
        self.assertFalse(kind.has_personal_story)
        self.assertTrue(kind.coaching_without_story)

    def test_coaching_with_feelings_counts_as_story(self) -> None:
        kind = classify_input_kind(COACH_WITH_FEELINGS)
        self.assertTrue(kind.is_coaching_request)
        self.assertTrue(kind.has_personal_story)
        self.assertFalse(kind.coaching_without_story)

    def test_long_first_person_is_rich(self) -> None:
        kind = classify_input_kind(LONG_FIRST_PERSON)
        self.assertFalse(kind.is_coaching_request)
        self.assertTrue(kind.has_personal_story)
        self.assertTrue(kind.rich_first_person)

    def test_emotion_heuristic_heartbreak(self) -> None:
        self.assertEqual(emotion_theme_heuristic(COACH_WITH_FEELINGS), "depression")

    def test_coaching_invite_payload(self) -> None:
        raw = coaching_invite_result_fields()
        self.assertEqual(raw["prediction"], "offmychest")
        self.assertGreaterEqual(raw["confidence"], 0.7)
        self.assertIn("own words", raw["reasoning"].lower())

    def test_long_narrative_ambiguity_dampened(self) -> None:
        short_mixed = score_input_ambiguity(
            "I feel fine and happy but also hopeless and empty without duration cues."
        )
        long = score_input_ambiguity(LONG_FIRST_PERSON)
        self.assertLess(long, short_mixed)

    def test_long_consistent_calibration_stays_usable(self) -> None:
        cal = calibrate_llm_only_confidence(
            text=LONG_FIRST_PERSON,
            prediction="depression",
            llm_confidence=0.72,
            run_labels=["depression", "depression", "offmychest"],
        )
        self.assertGreaterEqual(cal.confidence, 0.45)
        decision = apply_abstention(
            cal.confidence, text=LONG_FIRST_PERSON, prediction="depression"
        )
        self.assertFalse(decision.abstained)

    def test_pipeline_coaching_invite_path(self) -> None:
        from app.config import settings
        from app.schemas.analyse import AnalyseRequest
        from app.services.pipeline_controller import run_configured_pipeline

        with patch.object(settings, "openai_api_key", ""), patch.object(
            settings, "gemini_api_key", ""
        ), patch.object(settings, "groq_api_key", ""), patch.object(
            settings, "use_rag", False
        ), patch.object(settings, "enable_abstention", True):
            result = run_configured_pipeline(
                AnalyseRequest(text=COACH_ONLY, pipeline_mode="llm")
            )
        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.prediction, "offmychest")
        self.assertIn("own words", (result.reasoning or "").lower())
        self.assertFalse(result.safety_triggered)


if __name__ == "__main__":
    unittest.main()
