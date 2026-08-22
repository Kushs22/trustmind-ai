"""Unit tests for deterministic support-urgency mapping."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from app.services.support_urgency import compute_support_urgency  # noqa: E402


class SupportUrgencyTests(unittest.TestCase):
    def test_crisis_lands_in_urgent_band(self) -> None:
        u = compute_support_urgency(
            safety_triggered=True,
            concern_level="High",
            confidence=0.4,
            status="abstained",
            prediction="SuicideWatch",
            early_signs=["self-harm / suicidal crisis signs"],
            support_resources_present=True,
        )
        self.assertGreaterEqual(u.score, 85)
        self.assertEqual(u.band, "urgent")
        self.assertFalse(u.uncertain)
        self.assertIn("not a diagnosis", u.rationale.lower())

    def test_abstention_without_crisis_stays_soft(self) -> None:
        u = compute_support_urgency(
            safety_triggered=False,
            concern_level="High",  # pipeline may set High on abstain
            confidence=0.3,
            status="abstained",
            prediction=None,
            early_signs=[],
            support_resources_present=False,
        )
        self.assertLessEqual(u.score, 45)
        self.assertIn(u.band, {"low", "moderate"})
        self.assertTrue(u.uncertain)

    def test_high_concern_high_confidence_elevated(self) -> None:
        u = compute_support_urgency(
            safety_triggered=False,
            concern_level="High",
            confidence=0.9,
            status="accepted",
            prediction="depression",
            early_signs=["depression"],
        )
        self.assertGreaterEqual(u.score, 55)
        self.assertLess(u.score, 85)
        self.assertEqual(u.band, "elevated")
        self.assertFalse(u.uncertain)

    def test_low_concern_stays_low(self) -> None:
        u = compute_support_urgency(
            safety_triggered=False,
            concern_level="Low",
            confidence=0.85,
            status="accepted",
            prediction="normal",
            early_signs=[],
        )
        self.assertLessEqual(u.score, 34)
        self.assertEqual(u.band, "low")

    def test_deterministic(self) -> None:
        kwargs = dict(
            safety_triggered=False,
            concern_level="Moderate",
            confidence=0.8,
            status="accepted",
            prediction="anxiety",
            early_signs=["anxiety / worry"],
        )
        a = compute_support_urgency(**kwargs)
        b = compute_support_urgency(**kwargs)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
