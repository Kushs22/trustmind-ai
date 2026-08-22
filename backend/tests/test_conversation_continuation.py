"""Tests for multi-turn check-in chat continuation."""

from __future__ import annotations

import json
import sys
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from app.database import Base  # noqa: E402
from app.models import CheckIn, User  # noqa: E402
from app.schemas.analyse import AnalyseRequest  # noqa: E402
from app.services.check_in_service import analyse_and_optionally_save  # noqa: E402
from app.services.conversation_service import (  # noqa: E402
    append_follow_up_to_check_in,
    messages_for_row,
    parse_conversation_json,
)
from app.services.history_service import get_check_in  # noqa: E402


def _fake_analysis(**overrides):
    base = {
        "status": "accepted",
        "prediction": "anxiety",
        "prediction_display": "Anxiety",
        "confidence": 0.88,
        "reasoning": "It sounds like stress is weighing on you.",
        "sources": [],
        "message": "",
        "recommendation": "",
        "pipeline_used": "LLM",
        "support_resources": [],
        "disclaimer": "",
        "privacy_notice": "",
        "human_oversight": "",
        "concern_level": "Moderate",
        "ai_confidence": "88%",
        "uncertainty_level": "Low",
        "grounding_status": "Standalone",
        "abstention_status": "No abstention",
        "explanation": "It sounds like stress is weighing on you.",
        "safe_next_steps": ["Talk with someone you trust"],
        "safety_note": "Not a diagnosis.",
        "early_signs": [],
        "potential_indicators": [],
        "confidence_breakdown": None,
        "uncertainty": "Low",
        "trust_signals": None,
        "grounding": None,
        "evidence_used": [],
        "sources_detail": [],
        "safety_triggered": False,
        "support_urgency": 48,
        "support_urgency_band": "moderate",
        "support_urgency_rationale": "Moderate concern.",
        "support_urgency_uncertain": False,
        "debug": None,
        "input_summary": None,
        "processed_attachments": [],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class ConversationContinuationTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()
        self.user = User(
            id=str(uuid.uuid4()),
            email="student@example.com",
            hashed_password="hashed",
            is_anonymous=False,
        )
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()

    def test_save_seeds_conversation_thread(self) -> None:
        payload = AnalyseRequest(
            typed_text="I feel really stressed about exams.",
            save_to_history=True,
            analyse_privately=False,
        )
        with patch(
            "app.services.check_in_service.run_analysis",
            return_value=_fake_analysis(),
        ):
            response = analyse_and_optionally_save(self.db, payload, self.user)

        row = self.db.query(CheckIn).filter(CheckIn.id == response.id).one()
        messages = parse_conversation_json(row.conversation_json)
        self.assertGreaterEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "user")
        self.assertIn("stressed", messages[0]["content"].lower())
        self.assertEqual(messages[1]["role"], "assistant")

        detail = get_check_in(self.db, self.user, row.id)
        assert detail is not None
        self.assertGreaterEqual(len(detail.messages), 2)

    def test_legacy_row_synthesises_messages(self) -> None:
        row = CheckIn(
            id=str(uuid.uuid4()),
            user_id=self.user.id,
            concern_level="Low",
            ai_confidence="65%",
            uncertainty_level="Medium",
            grounding_status="Standalone",
            abstention_status="Prediction accepted",
            explanation="It sounds like you're feeling stressed right now.",
            safe_next_steps="[]",
            safety_note="Not a diagnosis.",
            text_preview="I feel stressed about deadlines.",
            is_private=False,
            abstained=False,
            conversation_json=None,
        )
        self.db.add(row)
        self.db.commit()
        msgs = messages_for_row(row)
        self.assertEqual(msgs[0]["role"], "user")
        self.assertEqual(msgs[1]["role"], "assistant")

    def test_append_follow_up_persists(self) -> None:
        row = CheckIn(
            id=str(uuid.uuid4()),
            user_id=self.user.id,
            concern_level="Moderate",
            ai_confidence="80%",
            uncertainty_level="Low",
            grounding_status="Standalone",
            abstention_status="Prediction accepted",
            explanation="It sounds like stress is weighing on you.",
            safe_next_steps="[]",
            safety_note="",
            text_preview="I've been stressed about exams.",
            is_private=False,
            abstained=False,
            conversation_json=json.dumps(
                [
                    {"role": "user", "content": "I've been stressed about exams."},
                    {
                        "role": "assistant",
                        "content": "It sounds like stress is weighing on you.",
                    },
                ]
            ),
        )
        self.db.add(row)
        self.db.commit()

        with patch(
            "app.services.conversation_service.generate_follow_up_reply",
            return_value=("Thanks for sharing more — that sounds tough.", False),
        ):
            updated, assistant, messages = append_follow_up_to_check_in(
                self.db,
                self.user,
                row.id,
                "Still feeling it today.",
            )

        self.assertEqual(assistant["content"], "Thanks for sharing more — that sounds tough.")
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[-2]["role"], "user")
        self.assertEqual(messages[-1]["role"], "assistant")
        self.assertIn("Still feeling", messages[-2]["content"])
        refreshed = self.db.query(CheckIn).filter(CheckIn.id == row.id).one()
        self.assertEqual(refreshed.explanation, assistant["content"])
        stored = parse_conversation_json(refreshed.conversation_json)
        self.assertEqual(len(stored), 4)

    def test_private_follow_up_blocked(self) -> None:
        row = CheckIn(
            id=str(uuid.uuid4()),
            user_id=self.user.id,
            concern_level="Low",
            ai_confidence="60%",
            uncertainty_level="Medium",
            grounding_status="Standalone",
            abstention_status="Prediction accepted",
            explanation="Private reflection.",
            safe_next_steps="[]",
            safety_note="",
            text_preview=None,
            is_private=True,
            abstained=False,
        )
        self.db.add(row)
        self.db.commit()
        with self.assertRaises(PermissionError):
            append_follow_up_to_check_in(
                self.db, self.user, row.id, "Can we keep talking?"
            )


if __name__ == "__main__":
    unittest.main()
