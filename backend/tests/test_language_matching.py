"""Multilingual language-matching helpers for chat follow-ups."""

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
    _needs_language_mirror,
    _requests_language_switch,
)


class LanguageMatchingTests(unittest.TestCase):
    def test_detects_non_latin_scripts(self) -> None:
        self.assertTrue(_needs_language_mirror("मैं ठीक नहीं हूँ"))
        self.assertTrue(_needs_language_mirror("Estoy muy estresado"))
        self.assertTrue(_needs_language_mirror("นันรู้สึกเครียด"))

    def test_detects_language_switch_requests(self) -> None:
        self.assertTrue(_requests_language_switch("can you talk in Hindi?"))
        self.assertTrue(_requests_language_switch("please reply in Spanish"))
        self.assertTrue(_requests_language_switch("réponds en français"))

    def test_english_only_claim_detector(self) -> None:
        self.assertTrue(
            _claims_english_only(
                "I can only communicate in English, but I'm still here to listen."
            )
        )
        self.assertFalse(_claims_english_only("Claro, podemos hablar en español."))

    def test_override_block_is_language_agnostic(self) -> None:
        block = _language_override_block("Hola, ¿cómo estás?")
        self.assertIn("LANGUAGE POLICY", block)
        self.assertIn("NEVER say you can only communicate in English", block)
        self.assertNotIn("Hindi only", block)


if __name__ == "__main__":
    unittest.main()
