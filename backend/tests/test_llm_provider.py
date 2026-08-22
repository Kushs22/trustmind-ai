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
            lp.settings, "openai_api_key", "sk-test"
        ), patch.object(lp.settings, "gemini_api_key", "gem-test"), patch.object(
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


if __name__ == "__main__":
    unittest.main()
