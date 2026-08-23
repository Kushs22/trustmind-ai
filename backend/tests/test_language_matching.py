"""Multilingual language-matching helpers for chat follow-ups."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from app.services.conversation_service import (  # noqa: E402
    _claims_english_only,
    _fallback_reply,
    _language_override_block,
    _looks_like_english_template,
    _needs_language_mirror,
    _requests_language_switch,
    _should_retry_language,
    generate_follow_up_reply,
)


class LanguageMatchingTests(unittest.TestCase):
    def test_detects_non_latin_scripts(self) -> None:
        self.assertTrue(_needs_language_mirror("मैं ठीक नहीं हूँ"))
        self.assertTrue(_needs_language_mirror("Estoy muy estresado"))
        self.assertTrue(_needs_language_mirror("นันรู้สึกเครียด"))

    def test_detects_hinglish_romanised(self) -> None:
        self.assertTrue(_needs_language_mirror("hinglish mai?"))
        self.assertTrue(_needs_language_mirror("yaar main bahut stressed hun"))
        self.assertTrue(_needs_language_mirror("mujhe tension ho rahi hai"))
        self.assertFalse(_needs_language_mirror("I feel stressed about exams today."))

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

    def test_english_template_detector(self) -> None:
        bad = (
            'Thanks for sharing more — it sounds like "hinglish mai?" is still on '
            "your mind. I'm here to listen without judging."
        )
        self.assertTrue(_looks_like_english_template(bad))
        self.assertTrue(_should_retry_language("hinglish mai?", bad))
        self.assertFalse(
            _looks_like_english_template("Samajh gaya — batao kya chal raha hai?")
        )

    def test_fallback_never_quote_echoes(self) -> None:
        reply = _fallback_reply("hinglish mai?", safety=False)
        self.assertNotIn("still on your mind", reply.lower())
        self.assertNotIn("hinglish mai?", reply.lower())
        self.assertNotIn("thanks for sharing more", reply.lower())
        self.assertIn("language", reply.lower())

    def test_override_block_is_language_agnostic(self) -> None:
        block = _language_override_block("Hola, ¿cómo estás?")
        self.assertIn("LANGUAGE POLICY", block)
        self.assertIn("NEVER say you can only communicate in English", block)
        self.assertIn("Hinglish", block)
        self.assertNotIn("Hindi only", block)

    def test_follow_up_retries_english_template(self) -> None:
        bad = (
            'Thanks for sharing more — it sounds like "hinglish mai?" is still on '
            "your mind. I'm here to listen without judging."
        )
        good = "Haan, batao — Hinglish mein hi baat karte hain. Main sun raha hoon."
        calls = {"n": 0}

        def _fake_complete_json(**_kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return json.dumps({"reply": bad, "safety_triggered": False}), "", "groq"
            return json.dumps({"reply": good, "safety_triggered": False}), "", "groq"

        with patch(
            "app.services.llm_provider.llm_configured", return_value=True
        ), patch(
            "app.services.llm_provider.complete_json", side_effect=_fake_complete_json
        ):
            reply, safety = generate_follow_up_reply(
                user_message="hinglish mai?",
                prior_messages=[],
            )

        self.assertFalse(safety)
        self.assertEqual(reply, good)
        self.assertEqual(calls["n"], 2)
        self.assertNotIn("still on your mind", reply.lower())

    def test_follow_up_falls_back_when_retry_still_bad(self) -> None:
        bad = (
            'Thanks for sharing more — it sounds like "mujhe tension hai" is still on '
            "your mind. I'm here to listen without judging."
        )
        calls = {"n": 0}

        def _fake_complete_json(**_kwargs):
            calls["n"] += 1
            return json.dumps({"reply": bad, "safety_triggered": False}), "", "groq"

        with patch(
            "app.services.llm_provider.llm_configured", return_value=True
        ), patch(
            "app.services.llm_provider.complete_json", side_effect=_fake_complete_json
        ):
            reply, safety = generate_follow_up_reply(
                user_message="mujhe tension ho rahi hai",
                prior_messages=[],
            )

        self.assertFalse(safety)
        self.assertEqual(calls["n"], 2)
        self.assertNotIn("still on your mind", reply.lower())
        self.assertNotIn("mujhe tension", reply.lower())
        self.assertIn("language", reply.lower())


if __name__ == "__main__":
    unittest.main()
