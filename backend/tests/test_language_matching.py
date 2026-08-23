"""Language matching / anti English-only regressions for chat follow-ups."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from app.services.conversation_service import (  # noqa: E402
    _claims_english_only,
    _language_override_block,
    _wants_hindi_or_non_english,
)


class LanguageMatchingTests(unittest.TestCase):
    def test_detects_roman_hindi(self) -> None:
        self.assertTrue(_wants_hindi_or_non_english("mera naam Kush hai"))
        self.assertTrue(_wants_hindi_or_non_english("can you talk in Hindi?"))
        self.assertTrue(_wants_hindi_or_non_english("aap kaise ho?"))

    def test_detects_devanagari(self) -> None:
        self.assertTrue(_wants_hindi_or_non_english("मैं ठीक नहीं हूँ"))

    def test_english_only_claim_detector(self) -> None:
        self.assertTrue(
            _claims_english_only(
                "I can only communicate in English, but I'm still here to listen."
            )
        )
        self.assertFalse(_claims_english_only("Haan, main Hindi mein baat kar sakta hoon."))

    def test_override_block_for_hindi(self) -> None:
        block = _language_override_block("talk in Hindi please")
        self.assertIn("CRITICAL LANGUAGE OVERRIDE", block)
        self.assertIn("English", block)


if __name__ == "__main__":
    unittest.main()
