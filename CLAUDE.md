# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is not a software project — it's the build record for **Sky Cob**, UWOSLAB's recoverable high-altitude weather balloon payload. There is no build, lint, or test tooling; the "artifacts" are a flight controller config dump, a radio model file, and 3D-printable enclosure parts. Changes here are validated by loading the files into their respective external tools (INAV Configurator, EdgeTX Companion, a slicer), not by running commands in this repo.

## Repository contents

| File | What it is |
|---|---|
| `INAV_9.0.1_cli_SKY_COB_20260701_003845.txt` | INAV 9.0.1 CLI dump for the flight controller (target `SPEEDYBEEF405WING`). Loaded into the INAV Configurator CLI tab to reproduce the flight controller setup. |
| `Sky Cob.yml` | EdgeTX/OpenTX radio model ("Sky Cob", targets EdgeTX 2.11.x) — ELRS/CRSF module setup plus telemetry screens (RSSI, GPS, altitude, battery, attitude, flight mode). |
| `cobshell.stl` | Main payload shell, upright orientation. |
| `cobby20x40.stl` | Receiver mounting plate. |
| `cobbyspeedy-top.stl` | Top mounting plate sized for the SpeedyBee F405 Wing FC. |
| `cobby19mm_cam_stand.stl` | Main chassis for components. |
| `fix model.stl` | Current shell model reoriented for printing on a 250x250 bed. |

Models and files are marked WIP in the README — check for recent updates before treating any of them as final.

## Editing the INAV CLI dump

`INAV_9.0.1_cli_SKY_COB_20260701_003845.txt` is a `diff all` batch: `batch start` → `defaults noreboot` → a sequence of `set`/`feature`/`aux`/`osd_layout`/etc. commands → `save`. When editing it:

- Keep the `batch start` / `save` structure intact — it's meant to be pasted or drag-loaded whole into the INAV Configurator CLI tab.
- `acczero_*`, `accgain_*`, and `gyro_zero_*` are per-unit accelerometer calibration offsets taken from the original board. They should NOT be copied as a template for a different physical FC — recalibrate instead.
- `aux` lines define switch-based flight modes (arm, OSD pages, etc.); channel mapping in the README's "Channel Mapping" table must stay consistent with these if either changes.
- Blackbox fields (`blackbox <FIELD>` / `blackbox -<FIELD>`) control what's logged; the enabled set is intentional (`NAV_POS`, `NAV_PID`, `MAG`, `ACC`, `ATTI`, `RC_DATA`, `RC_COMMAND`, `MOTORS`, `SERVOS`).
- Notable defaults already set: `osd_units = IMPERIAL`, `tz_offset = -240` (EDT), `name = SKY COB`, `pilot_name = UWOSLAB`, multi-constellation GPS (`gps_sbas_mode = WAAS`, Galileo/BeiDou/GLONASS enabled).

## Editing the radio model file

`Sky Cob.yml` is an EdgeTX model file (semver 2.11.5). The external module is CRSF (ExpressLRS); `telemetrySensors` maps CRSF/INAV telemetry (RSSI, GPS, altitude, battery, attitude, flight mode) to display fields, and `screenData`/`topbarData` define the on-radio telemetry screens. Switch assignments here (`flightModeData[n].swtch`, `customFn`) must stay in sync with the README's Channel Mapping table and the FC's `aux` lines.

## STL files

These are binary mesh files with no meaningful diff — treat changes as full replacements. `cobbyspeedy-top.stl` should be test-fit against the actual SpeedyBee F405 Wing board before committing to a full print run, since mounting-hole tolerances vary between printers/materials. `fix model.stl` is the shell reoriented specifically for a 250x250 print bed; it is a derivative of `cobshell.stl`, not an independent part.

## Consistency to maintain across files

Several facts are duplicated across the README, the CLI dump, and the radio model, and must be kept consistent if any one of them changes:
- Channel/switch mapping (arm, OSD pages, beeper) — README table ↔ FC `aux` lines ↔ radio `flightModeData`/`customFn`.
- VTX band/channel — README pre-flight checklist ↔ FC `vtx_band`/`vtx_channel`.
- Timezone/units — README ↔ FC `tz_offset`/`osd_units`.
