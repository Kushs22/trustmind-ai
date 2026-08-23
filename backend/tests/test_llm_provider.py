"""Tests for OpenAI → Gemini JSON provider fallback."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from app.services import llm_provider as lp  # noqa: E402


class LlmProviderTests(unittest.TestCase):
    def test_falls_back_to_gemini_on_openai_quota(self) -> None:
        with patch.object(lp.settings, "llm_provider", "auto"), patch.object(
            lp.settings, "groq_api_key", ""
        ), patch.object(lp.settings, "openai_api_key", "sk-test"), patch.object(
            lp.settings, "gemini_api_key", "gem-test"
        ), patch.object(
            lp,
            "_call_openai_json",
            return_value=("", "RateLimitError: insufficient_quota"),
        ), patch.object(
            lp,
            "_call_gemini_json",
            return_value=('{"predicted_label":"Anxiety","confidence":0.8,"reasoning":"ok"}', ""),
        ):
            text, err, provider = lp.complete_json(
                system="sys",
                user="hello",
                temperature=0.2,
            )
        self.assertEqual(provider, "gemini")
        self.assertFalse(err)
        self.assertIn("Anxiety", text)

    def test_prefers_groq_in_auto(self) -> None:
        with patch.object(lp.settings, "llm_provider", "auto"), patch.object(
            lp.settings, "groq_api_key", "gsk-test"
        ), patch.object(lp.settings, "gemini_api_key", "gem-test"), patch.object(
            lp.settings, "openai_api_key", "sk-test"
        ), patch.object(
            lp,
            "_call_groq_json",
            return_value=('{"reply":"from groq"}', ""),
        ), patch.object(
            lp,
            "_call_gemini_json",
            side_effect=AssertionError("gemini should not be called"),
        ), patch.object(
            lp,
            "_call_openai_json",
            side_effect=AssertionError("openai should not be called"),
        ):
            text, err, provider = lp.complete_json(system="sys", user="hi")
        self.assertEqual(provider, "groq")
        self.assertIn("groq", text)
        self.assertFalse(err)

    def test_gemini_only_mode(self) -> None:
        with patch.object(lp.settings, "llm_provider", "gemini"), patch.object(
            lp.settings, "openai_api_key", "sk-test"
        ), patch.object(lp.settings, "gemini_api_key", "gem-test"), patch.object(
            lp,
            "_call_openai_json",
            side_effect=AssertionError("openai should not be called"),
        ), patch.object(
            lp,
            "_call_gemini_json",
            return_value=('{"reply":"hi"}', ""),
        ):
            text, err, provider = lp.complete_json(system="sys", user="hi")
        self.assertEqual(provider, "gemini")
        self.assertIn("hi", text)
        self.assertFalse(err)


class KeywordFallbackStatusTests(unittest.TestCase):
    def test_maps_quota_and_model_errors_to_short_labels(self) -> None:
        self.assertEqual(
            lp.keyword_fallback_grounding_status(
                "RuntimeError: gemini 429 {\"error\":{\"code\":429,\"status\":\"RESOURCE_EXHAUSTED\"}}"
            ),
            "keyword_fallback (provider_quota)",
        )
        self.assertEqual(
            lp.keyword_fallback_grounding_status(
                "The model llama-3.3-70b-versatile does not exist"
            ),
            "keyword_fallback (model_unavailable)",
        )
        self.assertEqual(
            lp.keyword_fallback_grounding_status("connection timed out"),
            "keyword_fallback (timeout)",
        )
        self.assertEqual(
            lp.keyword_fallback_grounding_status("weird boom"),
            "keyword_fallback (provider_error)",
        )
        # Never embed the raw payload in the short status.
        long_body = "x" * 5000
        status = lp.keyword_fallback_grounding_status(f"RuntimeError: {long_body}")
        self.assertLess(len(status), 80)
        self.assertNotIn(long_body[:100], status)


if __name__ == "__main__":
    unittest.main()
