from __future__ import annotations

import unittest

from app.services.language import detect_script_hint, likely_english


class LanguageHintTests(unittest.TestCase):
    def test_english_checkin(self) -> None:
        self.assertTrue(likely_english("I have been feeling anxious at work"))
        self.assertEqual(detect_script_hint("I have been feeling anxious"), "und")

    def test_arabic_not_english(self) -> None:
        self.assertFalse(likely_english("أشعر بالقلق ولا أستطيع النوم"))
        self.assertEqual(detect_script_hint("أشعر بالقلق"), "ar")

    def test_chinese_not_english(self) -> None:
        self.assertFalse(likely_english("我很焦虑，晚上睡不着"))
        self.assertEqual(detect_script_hint("我很焦虑"), "zh")


if __name__ == "__main__":
    unittest.main()
