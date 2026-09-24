# Adhan Prayer Time

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
3. Find **Adhan Prayer Time** in HACS and select **Download**.
4. Restart Home Assistant.
5. Go to **Settings > Devices & services > Add integration**, search for
   **Adhan Prayer Time**, and complete the configuration form.

## Manual installation

1. Copy `custom_components/iacad_prayer` into
   `<Home Assistant config>/custom_components/iacad_prayer`.
2. Restart Home Assistant.
3. Add **Adhan Prayer Time** from **Settings > Devices & services**.

## Configuration

The configuration flow asks for:

- Latitude and longitude
- IANA timezone, for example `Asia/Dubai`
- Calculation method
- Madhab (`shafi` or `hanafi`)
- High-latitude rule

All settings can later be changed through the integration's **Configure**
option. Saving options reloads the entry automatically.

## Name migration

This integration was previously displayed as **IACAD Prayer Times** and
**azanAPI Prayer Times**. On the first setup after updating, an unchanged legacy
integration title is migrated to **Adhan Prayer Time**. The `iacad_prayer` integration domain, existing
entity IDs, and automation triggers are not changed.

If you renamed the integration or device yourself, your chosen name is kept.
To rename the device manually, open it in **Settings > Devices & services** and
select the edit icon.

## Verify in Home Assistant

After setup, open **Settings > Devices & services > Adhan Prayer Time** and
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

## Azan automations

Use an `* Active` binary sensor as a state trigger. It changes from `off` to
`on` exactly once at the final Azan time, including any API adjustment. Do not
trigger audio from the timestamp or `* Time` sensors.

### Prepare and test audio playback

1. Place your audio file at `<Home Assistant config>/media/azan.mp3`.
2. In **Developer tools > Actions**, run `media_player.play_media` against the
   intended speaker with the media source URI below. Confirm that it plays
   before creating an automation.
3. In **Developer tools > States**, find the actual entity ID of the desired
   `Fajr active` entity and your media player. Entity IDs differ if you renamed
   either entity, so replace both placeholders in the examples.

The local media source URI for the example file is:

```text
media-source://media_source/local/azan.mp3
```

### One-prayer template

Paste this into a new automation's YAML editor, then replace both placeholders.

```yaml
alias: Play Azan at Fajr
triggers:
  - trigger: state
    entity_id: binary_sensor.REPLACE_WITH_YOUR_FAJR_ACTIVE_ENTITY
    to: "on"
actions:
  - action: media_player.play_media
    target:
      entity_id: media_player.REPLACE_WITH_YOUR_SPEAKER
    data:
      media_content_id: media-source://media_source/local/azan.mp3
      media_content_type: music
mode: single
max_exceeded: silent
```

`mode: single` prevents an overlapping duplicate run while the same automation
is still playing. Use a separate automation only when a prayer needs a
different speaker, audio file, or volume behavior.

### All five prayers in one automation

Replace each placeholder with the corresponding entity ID from **Developer
tools > States**. This version plays the same audio on the same speaker for all
five Azan prayers.

```yaml
alias: Play Azan at prayer times
triggers:
  - trigger: state
    entity_id: binary_sensor.REPLACE_WITH_YOUR_FAJR_ACTIVE_ENTITY
    to: "on"
  - trigger: state
    entity_id: binary_sensor.REPLACE_WITH_YOUR_DHUHR_ACTIVE_ENTITY
    to: "on"
  - trigger: state
    entity_id: binary_sensor.REPLACE_WITH_YOUR_ASR_ACTIVE_ENTITY
    to: "on"
  - trigger: state
    entity_id: binary_sensor.REPLACE_WITH_YOUR_MAGHRIB_ACTIVE_ENTITY
    to: "on"
  - trigger: state
    entity_id: binary_sensor.REPLACE_WITH_YOUR_ISHA_ACTIVE_ENTITY
    to: "on"
actions:
  - action: media_player.play_media
    target:
      entity_id: media_player.REPLACE_WITH_YOUR_SPEAKER
    data:
      media_content_id: media-source://media_source/local/azan.mp3
      media_content_type: music
mode: single
max_exceeded: silent
```

If your speaker requires a different media type or URL, first use its own
integration documentation and test the action in **Developer tools > Actions**.

## Troubleshooting and privacy

If the API cannot be reached or returns invalid data, coordinator-backed
entities become unavailable and retry on the normal update schedule. Downloaded
diagnostics redact latitude and longitude.

For API details, see the [azanAPI documentation](https://azanapi-docs.aakashsharma.com.np/).
Report integration issues at the configured
[issue tracker](https://github.com/aakash-sharma-github/IACAD-Prayer-Times/issues).

## Releases and versioning

The integration uses Semantic Versioning in `manifest.json`.

- Patch releases fix bugs without changing configuration or entity contracts.
- Minor releases add backward-compatible functionality.
- Major releases may include breaking changes and will document migration steps.

Publish a matching GitHub release and tag for each released manifest version.
HACS shows a commit when the repository has no GitHub release. To publish the
first version shown to users:

1. Commit and push the release-ready changes.
2. Create an annotated tag named `v0.1.0` on that commit and push the tag:

   ```bash
   git tag -a v0.1.0 -m "Adhan Prayer Time v0.1.0"
   git push origin v0.1.0
   ```

3. On GitHub, create a release from `v0.1.0`, use the corresponding
   `CHANGELOG.md` section as its notes, and publish it.
4. In HACS, select **Download** for the integration and choose `v0.1.0`.

For later releases, update `manifest.json`, add the next changelog section,
and create a matching `vX.Y.Z` GitHub tag and release. Repository publishing
is intentionally not performed by this integration.
