"""Tests for privacy export and account deletion."""

from __future__ import annotations

import json
import sys
import unittest
import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT))

from app.database import Base  # noqa: E402
from app.models import CheckIn, User  # noqa: E402
from app.services.auth_service import delete_user_data, export_user_data  # noqa: E402
from app.services.history_service import delete_all_check_ins  # noqa: E402


class PrivacyDataControlsTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()
        self.user = User(
            id=str(uuid.uuid4()),
            email="export@example.com",
            hashed_password="hashed",
            is_anonymous=False,
        )
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()

    def _add_check_in(self, preview: str = "feeling tired") -> CheckIn:
        row = CheckIn(
            id=str(uuid.uuid4()),
            user_id=self.user.id,
            concern_level="Moderate",
            ai_confidence="80%",
            uncertainty_level="Low",
            grounding_status="Standalone",
            abstention_status="No abstention",
            explanation="A supportive note.",
            safe_next_steps=json.dumps(["Rest"]),
            safety_note="Not a diagnosis.",
            text_preview=preview,
            is_private=False,
            abstained=False,
            conversation_json=json.dumps(
                [
                    {"role": "user", "content": preview},
                    {"role": "assistant", "content": "Thanks for sharing."},
                ]
            ),
        )
        self.db.add(row)
        self.db.commit()
        return row

    def test_export_includes_profile_and_conversations(self) -> None:
        self._add_check_in()
        payload = export_user_data(self.db, self.user)
        self.assertEqual(payload["format_version"], 1)
        self.assertEqual(payload["profile"]["email"], "export@example.com")
        self.assertFalse(payload["profile"]["is_anonymous"])
        self.assertEqual(len(payload["check_ins"]), 1)
        check_in = payload["check_ins"][0]
        self.assertEqual(check_in["text_preview"], "feeling tired")
        self.assertIsInstance(check_in["conversation"], list)
        self.assertEqual(check_in["conversation"][0]["role"], "user")
        self.assertNotIn("hashed_password", payload["profile"])

    def test_delete_user_cascades_check_ins(self) -> None:
        self._add_check_in()
        user_id = self.user.id
        delete_user_data(self.db, self.user)
        self.assertIsNone(self.db.query(User).filter(User.id == user_id).first())
        self.assertEqual(
            self.db.query(CheckIn).filter(CheckIn.user_id == user_id).count(),
            0,
        )

    def test_delete_all_check_ins_keeps_account(self) -> None:
        self._add_check_in()
        deleted = delete_all_check_ins(self.db, self.user)
        self.assertEqual(deleted, 1)
        self.assertIsNotNone(
            self.db.query(User).filter(User.id == self.user.id).first()
        )


if __name__ == "__main__":
    unittest.main()
