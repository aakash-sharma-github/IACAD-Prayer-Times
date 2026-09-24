# IACAD Prayer Times

Home Assistant custom integration for daily Islamic prayer times from the
[azanAPI](https://api.aakashsharma.com.np). It creates timezone-aware prayer
time sensors, countdown sensors, and one-minute Azan active binary sensors.

Created by [Aakash Sharma](https://www.aakashsharma.com.np).

## Requirements

- Home Assistant **2025.8.0 or later**.
- Internet access from Home Assistant to `https://api.aakashsharma.com.np`.
- HACS is optional, but recommended for installation and updates.

The integration has no additional Python package requirements; it uses Home
Assistant's shared HTTP client.

## Install with HACS

1. In HACS, select **Integrations**.
2. Open the overflow menu, select **Custom repositories**, and add this
   repository as an **Integration**.
3. Find **IACAD Prayer Times** in HACS and select **Download**.
4. Restart Home Assistant.
5. Go to **Settings > Devices & services > Add integration**, search for
   **IACAD Prayer Times**, and complete the configuration form.

## Manual installation

1. Copy `custom_components/iacad_prayer` into
   `<Home Assistant config>/custom_components/iacad_prayer`.
2. Restart Home Assistant.
3. Add **IACAD Prayer Times** from **Settings > Devices & services**.

## Configuration

The configuration flow asks for:

- Latitude and longitude
- IANA timezone, for example `Asia/Dubai`
- Calculation method
- Madhab (`shafi` or `hanafi`)
- High-latitude rule

All settings can later be changed through the integration's **Configure**
option. Saving options reloads the entry automatically.

## Verify in Home Assistant

After setup, open **Settings > Devices & services > IACAD Prayer Times** and
check that its entities are available. Confirm that timestamp values match the
selected location, timezone, and calculation method.

To test the full integration:

1. Change a setting through **Configure** and confirm the entry reloads and the
   values update.
2. Download diagnostics from the integration menu and verify that coordinates
   are redacted.
3. Use **Developer tools > States** to observe an `* Active` binary sensor at a
   final Azan time. It is on for one minute only.
4. If setup fails, inspect **Settings > System > Logs** for entries under
   `custom_components.iacad_prayer`.

## Entities

Each config entry creates:

- Seven timestamp sensors: Fajr, Sunrise, Dhuhr, Asr, Sunset, Maghrib, and
  Isha.
- Five remaining-time sensors for Fajr, Dhuhr, Asr, Maghrib, and Isha.
- Five binary sensors: Fajr Active, Dhuhr Active, Asr Active, Maghrib Active,
  and Isha Active.

An `* Active` binary sensor is `on` from the final API Azan time (including an
adjustment) until, but not including, one minute later. These entities are
intended for Azan automations; the integration does not play audio itself.

## Troubleshooting and privacy

If the API cannot be reached or returns invalid data, coordinator-backed
entities become unavailable and retry on the normal update schedule. Downloaded
diagnostics redact latitude and longitude.

For API details, see the [azanAPI documentation](https://api.aakashsharma.com.np/docs).
Report integration issues at the configured
[issue tracker](https://github.com/aakash-sharma-github/IACAD-Prayer-Times/issues).

## Releases and versioning

The integration uses Semantic Versioning in `manifest.json`.

- Patch releases fix bugs without changing configuration or entity contracts.
- Minor releases add backward-compatible functionality.
- Major releases may include breaking changes and will document migration steps.

Publish a matching GitHub release and tag for each released manifest version.
HACS can use the default branch before the first release; publishing is not
performed by this repository.
