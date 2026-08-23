"""Security helpers: passwords, secrets, rate limits, CORS."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.config import Settings, secret_key_is_weak
from app.core.passwords import validate_password_strength
from app.schemas.auth import RegisterRequest
from app.services.rate_limit import RateLimitExceeded, check_rate_limit


class PasswordStrengthTests(unittest.TestCase):
    def test_rejects_short_and_simple(self) -> None:
        self.assertIsNotNone(validate_password_strength("short"))
        self.assertIsNotNone(validate_password_strength("password"))
        self.assertIsNotNone(validate_password_strength("abcdefgh"))

    def test_accepts_letter_and_digit(self) -> None:
        self.assertIsNone(validate_password_strength("Password1"))
        self.assertIsNone(validate_password_strength("abc!defg"))

    def test_register_schema_enforces(self) -> None:
        with self.assertRaises(ValidationError):
            RegisterRequest(email="a@example.com", password="password")
        ok = RegisterRequest(email="a@example.com", password="Password1")
        self.assertEqual(ok.password, "Password1")


class SecretKeyTests(unittest.TestCase):
    def test_weak_defaults(self) -> None:
        self.assertTrue(secret_key_is_weak("dev-only-change-me-in-production"))
        self.assertTrue(secret_key_is_weak("short"))
        self.assertFalse(
            secret_key_is_weak("a" * 32),
        )

    def test_production_rejects_weak_secret(self) -> None:
        with patch.dict(os.environ, {"RENDER": "true"}, clear=False):
            with self.assertRaises(ValidationError):
                Settings(
                    secret_key="dev-only-change-me-in-production",
                    cors_origins="https://trustmind-ai.vercel.app",
                )

    def test_production_rejects_star_cors(self) -> None:
        strong = "x" * 48
        with patch.dict(os.environ, {"RENDER": "true"}, clear=False):
            with self.assertRaises(ValidationError):
                Settings(secret_key=strong, cors_origins="*")

    def test_frontend_url_merged(self) -> None:
        s = Settings(
            cors_origins="http://localhost:3000",
            frontend_url="https://custom.example",
        )
        self.assertIn("https://custom.example", s.cors_origin_list)
        self.assertIn("http://localhost:3000", s.cors_origin_list)


class RateLimitTests(unittest.TestCase):
    def test_analyse_limit_trips(self) -> None:
        key = "test-client-rate-limit-unique"
        for _ in range(15):
            check_rate_limit(key, action="analyse", limit=15, window_seconds=60)
        with self.assertRaises(RateLimitExceeded):
            check_rate_limit(key, action="analyse", limit=15, window_seconds=60)


if __name__ == "__main__":
    unittest.main()
