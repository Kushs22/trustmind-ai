"""Tests for authenticated check-in persistence (dashboard history)."""

from __future__ import annotations

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
from app.services.history_service import dashboard_stats, list_check_ins  # noqa: E402


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
        "debug": None,
        "input_summary": None,
        "processed_attachments": [],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class CheckInPersistenceTests(unittest.TestCase):
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

    def test_strip_short_input_result_leaks(self) -> None:
        from app.services.abstention import (
            LIMITED_CONTEXT_DISCLAIMER,
            short_checkin_reflection,
            strip_short_input_result_leaks,
        )

        polluted = f"{LIMITED_CONTEXT_DISCLAIMER} It sounds like stress is hard."
        cleaned = strip_short_input_result_leaks(polluted)
        self.assertNotIn("shared only a little", cleaned.lower())
        self.assertIn("stress", cleaned.lower())
        warm = short_checkin_reflection("Anxiety", user_text="I feel stressed")
        self.assertIn("stress", warm.lower())
        self.assertNotIn("share more", warm.lower())

    def test_authenticated_analyse_creates_check_in(self) -> None:
        payload = AnalyseRequest(
            typed_text="I feel really happy today after finishing my exams.",
            save_to_history=True,
            analyse_privately=False,
        )

        with patch(
            "app.services.check_in_service.run_analysis",
            return_value=_fake_analysis(),
        ):
            response = analyse_and_optionally_save(self.db, payload, self.user)

        self.assertTrue(response.saved_to_history)
        self.assertIsNotNone(response.id)

        rows = self.db.query(CheckIn).filter(CheckIn.user_id == self.user.id).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].concern_level, "Moderate")
        self.assertEqual(rows[0].ai_confidence, "88%")
        self.assertFalse(rows[0].is_private)
        self.assertIsNotNone(rows[0].text_preview)

        history = list_check_ins(self.db, self.user)
        self.assertEqual(len(history), 1)
        stats = dashboard_stats(self.db, self.user)
        self.assertEqual(stats.saved_analyses, 1)
        self.assertEqual(stats.avg_ai_confidence, 88)

    def test_private_save_omits_text_preview(self) -> None:
        payload = AnalyseRequest(
            typed_text="I feel stressed about deadlines.",
            save_to_history=True,
            analyse_privately=True,
        )

        with patch(
            "app.services.check_in_service.run_analysis",
            return_value=_fake_analysis(),
        ):
            response = analyse_and_optionally_save(self.db, payload, self.user)

        self.assertTrue(response.saved_to_history)
        row = self.db.query(CheckIn).one()
        self.assertTrue(row.is_private)
        self.assertIsNone(row.text_preview)

    def test_save_without_user_raises(self) -> None:
        payload = AnalyseRequest(
            typed_text="I feel stressed.",
            save_to_history=True,
            analyse_privately=False,
        )
        with patch(
            "app.services.check_in_service.run_analysis",
            return_value=_fake_analysis(),
        ):
            with self.assertRaises(PermissionError):
                analyse_and_optionally_save(self.db, payload, None)

    def test_no_save_when_flag_false(self) -> None:
        payload = AnalyseRequest(
            typed_text="I feel happy.",
            save_to_history=False,
            analyse_privately=True,
        )
        with patch(
            "app.services.check_in_service.run_analysis",
            return_value=_fake_analysis(),
        ):
            response = analyse_and_optionally_save(self.db, payload, self.user)

        self.assertFalse(response.saved_to_history)
        self.assertEqual(self.db.query(CheckIn).count(), 0)


class DatabaseUrlTests(unittest.TestCase):
    def test_normalize_postgres_urls(self) -> None:
        from app.config import database_url_safe_summary, normalize_database_url

        self.assertEqual(
            normalize_database_url("postgres://u:p@host/db"),
            "postgresql+psycopg2://u:p@host/db",
        )
        self.assertEqual(
            normalize_database_url("postgresql://u:p@host/db"),
            "postgresql+psycopg2://u:p@host/db",
        )
        self.assertEqual(
            normalize_database_url('  "postgres://u:p@host/db"  '),
            "postgresql+psycopg2://u:p@host/db",
        )
        self.assertEqual(
            normalize_database_url("sqlite:///./trustmind.db"),
            "sqlite:///./trustmind.db",
        )
        summary = database_url_safe_summary(
            "postgresql+psycopg2://u:secret@dpg-xxx-a/trustmind"
        )
        self.assertIn("dpg-xxx-a", summary)
        self.assertNotIn("secret", summary)

    def test_sqlite_detection_does_not_false_positive_on_postgres(self) -> None:
        from app.config import Settings

        pg = Settings(
            database_url="postgres://u:p@dpg-xxx-a/trustmind",
            _env_file=None,
        )
        self.assertFalse(pg.is_sqlite)
        self.assertTrue(pg.is_postgres)
        self.assertTrue(pg.database_url.startswith("postgresql+psycopg2://"))

        sq = Settings(database_url="sqlite:///./trustmind.db", _env_file=None)
        self.assertTrue(sq.is_sqlite)
        self.assertFalse(sq.is_postgres)


if __name__ == "__main__":
    unittest.main()
