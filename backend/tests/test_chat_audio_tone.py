"""Tests for chat audio transcript + soft tone cues."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from app.services.audio_tone_service import (  # noqa: E402
    format_audio_prompt_block,
    format_audio_user_content,
    infer_tone_cues,
    process_chat_audio,
)
from app.services.conversation_service import (  # noqa: E402
    generate_follow_up_reply,
    parse_conversation_json,
)


class AudioToneServiceTests(unittest.TestCase):
    def test_format_user_content_includes_note_and_tone(self) -> None:
        body = format_audio_user_content(
            transcript="I feel worn out after exams.",
            tone_summary="May have sounded tired and subdued.",
            affect_cues=["tired-sounding", "subdued"],
        )
        self.assertIn("Audio message", body)
        self.assertIn("I feel worn out after exams.", body)
        self.assertIn("How this sounded:", body)
        self.assertIn("Tone cues:", body)

    def test_prompt_block_is_non_diagnostic(self) -> None:
        block = format_audio_prompt_block(
            transcript="Everything feels heavy.",
            tone_summary="Came across as heavy and subdued.",
            affect_cues=["subdued"],
            uncertainty="medium",
        )
        self.assertIn("not a clinical mood reading", block)
        self.assertIn("Everything feels heavy.", block)
        self.assertIn("without diagnosing", block)

    def test_infer_tone_fallback_without_api_key(self) -> None:
        with patch("app.services.audio_tone_service.settings") as mock_settings:
            mock_settings.openai_api_key = ""
            result = infer_tone_cues(
                transcript="I am stressed about deadlines.",
                duration_seconds=4.0,
            )
        self.assertIn("tone_summary", result)
        self.assertIn(result["uncertainty"], ("low", "medium", "high"))
        self.assertFalse(result["safety_hint"])

    def test_process_chat_audio_wires_transcript_and_tone(self) -> None:
        fake_transcription = {
            "status": "completed",
            "transcript": "I keep waking up worried.",
            "language": "en",
            "duration_seconds": 3.5,
            "warnings": [],
        }
        with patch(
            "app.services.audio_tone_service.transcribe_audio_bytes",
            return_value=fake_transcription,
        ), patch(
            "app.services.audio_tone_service.infer_tone_cues",
            return_value={
                "tone_summary": "May have sounded anxious and restless.",
                "affect_cues": ["anxious-sounding", "restless"],
                "uncertainty": "medium",
                "safety_hint": False,
            },
        ):
            result = process_chat_audio(
                data=b"fake",
                filename="clip.webm",
                content_type="audio/webm",
            )
        self.assertEqual(result["transcript"], "I keep waking up worried.")
        self.assertIn("Audio message", result["content"])
        self.assertIn("How this sounded", result["content"])
        self.assertIn("Speech content (note)", result["prompt_block"])
        self.assertEqual(
            result["tone_summary"],
            "May have sounded anxious and restless.",
        )

    def test_parse_conversation_preserves_audio_fields(self) -> None:
        raw = (
            '[{"role":"user","content":"Audio message\\n\\"hi\\"","input_type":"audio",'
            '"transcript":"hi","tone_summary":"Calm","affect_cues":["calm"]},'
            '{"role":"assistant","content":"Thanks for sharing."}]'
        )
        messages = parse_conversation_json(raw)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["input_type"], "audio")
        self.assertEqual(messages[0]["transcript"], "hi")
        self.assertEqual(messages[0]["tone_summary"], "Calm")
        self.assertEqual(messages[0]["affect_cues"], ["calm"])

    def test_follow_up_uses_audio_prompt_and_crisis(self) -> None:
        with patch("app.services.conversation_service.settings") as mock_settings:
            mock_settings.openai_api_key = ""
            reply, safety = generate_follow_up_reply(
                user_message='Audio message\n"I want to die"',
                prior_messages=[],
                audio_prompt_block=(
                    "Speech content (note): I want to die\n"
                    "Tone cues: strained"
                ),
            )
        self.assertTrue(safety)
        self.assertIn("sorry", reply.lower())


if __name__ == "__main__":
    unittest.main()
