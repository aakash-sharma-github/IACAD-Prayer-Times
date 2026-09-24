"""Structural and validation tests for the Phase 2 integration skeleton."""

import json
import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[1]
CUSTOM_COMPONENTS_PATH = REPOSITORY_ROOT / "custom_components"
INTEGRATION_PATH = CUSTOM_COMPONENTS_PATH / "iacad_prayer"
package = type(sys)("iacad_prayer")
package.__path__ = [str(INTEGRATION_PATH)]
sys.modules.setdefault("iacad_prayer", package)

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
        self.assertEqual(manifest["name"], "Adhan Prayer Time")
        self.assertTrue(manifest["config_flow"])
        self.assertEqual(manifest["integration_type"], "service")
        self.assertEqual(manifest["documentation"], "https://www.aakashsharma.com.np")
        self.assertEqual(
            manifest["issue_tracker"],
            "https://github.com/aakash-sharma-github/IACAD-Prayer-Times/issues",
        )

    def test_hacs_metadata_declares_the_existing_repository_layout(self) -> None:
        hacs = json.loads((REPOSITORY_ROOT / "hacs.json").read_text())

        self.assertEqual(hacs, {})

    def test_hacs_brand_icon_is_a_png_asset(self) -> None:
        icon = (REPOSITORY_ROOT / "brand" / "icon.png").read_bytes()

        self.assertTrue(icon.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_readme_documents_installation_and_supported_home_assistant_version(
        self,
    ) -> None:
        readme = (REPOSITORY_ROOT / "README.md").read_text()

        self.assertIn("Home Assistant **2025.8.0 or later**", readme)
        self.assertIn("## Install with HACS", readme)
        self.assertIn("## Manual installation", readme)
        self.assertIn("## Verify in Home Assistant", readme)
        self.assertIn("## Azan automations", readme)
        self.assertIn("media_player.play_media", readme)
        self.assertIn("mode: single", readme)
        self.assertIn("Aakash Sharma", readme)

    def test_github_workflow_runs_hacs_and_home_assistant_validation(self) -> None:
        workflow = (
            REPOSITORY_ROOT / ".github" / "workflows" / "validate.yml"
        ).read_text()

        self.assertIn("hacs/action@main", workflow)
        self.assertIn("home-assistant/actions/hassfest@master", workflow)

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
