# Changelog

All notable changes to Adhan Prayer Time are documented in this file.

## [0.1.2] - 2026-09-24

- Adds the Home Assistant release acceptance checklist.

## [0.1.1] - 2026-09-24

- Documents the HACS update, full-restart, and config-entry reload workflow.
- Documents the Semantic Versioning bump and GitHub release process.

## [0.1.0] - 2026-09-24

Initial public release.

- Provides timezone-aware Fajr, Sunrise, Dhuhr, Asr, Sunset, Maghrib, and
  Isha timestamp sensors.
- Provides display-friendly clock-time sensors, remaining-time sensors, and
  one-minute active binary sensors for the five Azan prayers.
- Supports configurable coordinates, timezone, calculation method, madhab,
  high-latitude rule, diagnostics, and Azan automations.
- Renames the displayed integration to Adhan Prayer Time while preserving the
  `iacad_prayer` domain and existing entity IDs.
