"""Structural and validation tests for the Phase 2 integration skeleton."""

import json
import sys
import unittest
from pathlib import Path

CUSTOM_COMPONENTS_PATH = Path(__file__).parents[1]
INTEGRATION_PATH = CUSTOM_COMPONENTS_PATH / "iacad_prayer"
sys.path.insert(0, str(CUSTOM_COMPONENTS_PATH))

from iacad_prayer.const import (
    CALCULATION_METHODS,
    HIGH_LATITUDE_RULES,
    MADHABS,
)
from iacad_prayer.validation import is_valid_timezone


class IacadPrayerSkeletonTest(unittest.TestCase):
    """Verify files that Home Assistant needs to discover the integration."""

    def test_manifest_declares_a_config_flow(self) -> None:
        manifest = json.loads((INTEGRATION_PATH / "manifest.json").read_text())

        self.assertEqual(manifest["domain"], "iacad_prayer")
        self.assertEqual(manifest["name"], "IACAD Prayer Times")
        self.assertTrue(manifest["config_flow"])
        self.assertEqual(manifest["integration_type"], "service")

    def test_translation_files_have_matching_english_content(self) -> None:
        strings = json.loads((INTEGRATION_PATH / "strings.json").read_text())
        english = json.loads(
            (INTEGRATION_PATH / "translations" / "en.json").read_text()
        )

        self.assertEqual(strings, english)
        self.assertEqual(
            strings["config"]["step"]["user"]["data"].keys(),
            {
                "latitude",
                "longitude",
                "timezone",
                "calculation_method",
                "madhab",
                "high_latitude_rule",
            },
        )

    def test_timezone_validation(self) -> None:
        self.assertTrue(is_valid_timezone("Asia/Dubai"))
        self.assertFalse(is_valid_timezone("Not/ARealTimezone"))

    def test_config_choices_match_the_phase_1_api_contract(self) -> None:
        self.assertIn("iacad_dubai", CALCULATION_METHODS)
        self.assertEqual(MADHABS, ("shafi", "hanafi"))
        self.assertEqual(HIGH_LATITUDE_RULES[0], "middle_of_the_night")
