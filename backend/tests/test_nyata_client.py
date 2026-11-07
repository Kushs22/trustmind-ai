from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.nyata_client import map_concern_to_category
from app.services.nyata_response import build_local_support_card


class NyataMappingTests(unittest.TestCase):
    def test_anxiety_prediction(self) -> None:
        self.assertEqual(map_concern_to_category("Anxiety", "tight chest"), "anxiety")

    def test_food_overrides_prediction(self) -> None:
        self.assertEqual(
            map_concern_to_category("Anxiety", "I need a food bank tonight"),
            "food",
        )

    def test_housing_from_text(self) -> None:
        self.assertEqual(map_concern_to_category(None, "I might be homeless"), "housing")


class NyataCardTests(unittest.TestCase):
    def test_empty_payload_is_hidden(self) -> None:
        self.assertIsNone(build_local_support_card({"ok": False, "error": "not_configured"}))

    def test_sorts_open_and_near_first(self) -> None:
        card = build_local_support_card(
            {
                "ok": True,
                "category": "anxiety",
                "reply": "Here are nearby services.",
                "quota_remaining": 80,
                "results": [
                    {
                        "type": "charity_service",
                        "name": "Far Closed",
                        "organisation": "A",
                        "verification": "verified",
                        "open_now": False,
                        "distance_km": 4.2,
                        "booking_required": True,
                    },
                    {
                        "type": "charity_service",
                        "name": "Near Open",
                        "organisation": "B",
                        "verification": "verified",
                        "open_now": True,
                        "distance_km": 0.4,
                        "booking_required": False,
                        "directions_url": "https://maps.example/1",
                    },
                ],
            }
        )
        self.assertIsNotNone(card)
        assert card is not None
        self.assertEqual(card["listings"][0]["name"], "Near Open")
        self.assertIn("Open now", card["listings"][0]["badges"])
        self.assertIn("Booking needed", card["listings"][1]["badges"])
        self.assertEqual(card["provider"], "Nyata AI")


class NyataClientSkipTests(unittest.TestCase):
    def test_missing_key_does_not_call_network(self) -> None:
        from app.services.nyata_client import get_bristol_support

        with patch("app.services.nyata_client.settings") as fake:
            fake.nyata_api_key = ""
            fake.enable_nyata = True
            with patch("urllib.request.urlopen") as opener:
                out = get_bristol_support("I feel anxious", category="anxiety")
            opener.assert_not_called()
        self.assertEqual(out["error"], "not_configured")


if __name__ == "__main__":
    unittest.main()
