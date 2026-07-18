# Weather-Balloon Configurator — Design Doc

> **Status: functional, in use.** The fork lives at [2theMAXtheStairFax/sky-cob-configurator](https://github.com/2theMAXtheStairFax/sky-cob-configurator) (forked from `iNavFlight/inav-configurator`, `upstream` remote wired for future syncs). Verified end-to-end against both Demo Mode (SITL virtual FC) and the real Sky Cob SpeedyBee F405 Wing board over serial.

## Goal

A simplified, Electron-based configurator for weather balloon payloads built on stock INAV firmware (no firmware fork). It exposes only the settings a balloon build needs and provides a one-click way to push the balloon-specific baseline config to a fresh or reset flight controller.

## Non-goals

- No custom firmware build/compile step, no new INAV target, no reflashing a modified binary. The FC keeps running stock INAV; only its stored configuration changes.
- No motor mixer, no autonomous navigation (RTH, waypoints, geozones, safehomes), no multirotor/heli-specific tabs.
- Not a general-purpose INAV Configurator replacement — anything outside the balloon use case is deliberately left out of scope, not just hidden. (This is also why this fork is not a candidate for a PR back into upstream INAV Configurator — see "Upstream contribution" below.)

## What was actually built

Rather than the CLI-diff-generator architecture originally sketched below (kept for history), the simpler and more robust approach turned out to be: strip the UI down tab-by-tab, and reuse the Configurator's own existing CLI-mode plumbing for the one place a "push config" action was actually needed (initial balloon setup).

1. **Tab removal.** Deleted Mission Control, SITL (the manual build/config tab), PID Tuning, Advanced Tuning, Adjustments, LED Strip, Programming, and JavaScript Programming — nav entries, `gui.js` `allowedTabs`, `configurator_main.js` wiring, and the tabs' own HTML/JS/CSS (~14k lines). Also removed the Failsafe tab (a balloon should keep going and stay armed on RC loss, matching `failsafe_procedure = NONE`), the Configuration tab's Power Limits box, and all optical-flow support (sensor dropdown, calibration UI, header status icon).
2. **Servo-only Mixer/Outputs.** Motor-specific sections (Platform Configuration, Mixer Presets, Mixer Wizard, Motor Mixer table, ESC protocol, motor test sliders, reversible-motor fields) are hidden via a `.skycob-hide { display: none !important; }` CSS class rather than deleted, since `Mixer`/`Outputs` share a single MSP load/save chain with the servo-relevant fields we keep. Plain inline `display:none` doesn't survive — `Settings.saveInputs()` calls `parent.show()` on any element with a valid `data-setting`, silently un-hiding it; `!important` does survive that.
3. **Demo Mode.** A lightweight virtual-FC connection (`js/sitl.js` + the `sitl-demo` port option, reusing the bundled SITL binary) for testing the app without real hardware — distinct from the full SITL tab, which stays removed.
4. **No new-FC wizard popup.** Removed `js/defaults_dialog.js` and its wizard step HTML — it walks through multirotor/plane craft-type presets that don't apply here, and it blocked the config view on first connect.
5. **Flat sidebar.** The upstream fork's collapsible accordion nav-groups broke down once most groups were down to 1–2 items (collapsing to a ~1px sliver); replaced with a flat `<li>` list.
6. **Balloon Setup tab** (`tabs/balloon_setup.js`, `js/balloonDefaults.js`) — the actual answer to "push the necessary balloon-only settings to a new FC." A single "Apply Balloon Defaults & Reboot" button runs `defaults noreboot` then applies the curated Sky Cob CLI settings (GPS constellations, blackbox config, AUX/arm switch mapping, OSD units/timezone, VTX band/channel, and the safety settings — `failsafe_procedure=NONE`, `nav_rth_allow_landing=NEVER`, `nav_rth_climb_first=OFF`, `safehome_usage_mode=OFF`). Deliberately excludes acc/gyro calibration (per-board, use the Calibration tab). Implemented by reusing `js/backup_restore.js`'s `BackupRestore` module — already built upstream for backup/restore-around-flashing — to enter CLI mode and send each line with per-line error detection; only saves to EEPROM if every command succeeds.

Verified twice: against Demo Mode (no risk), then against the real connected FC — applied all 98 settings with zero errors, saved, rebooted, re-enumerated normally, and a post-reboot `diff all` confirmed every setting (including the four safety settings) landed correctly.

## Known remaining dead code (left in place deliberately)

`js/transpiler/` (the logic-conditions compiler, now fully orphaned but still has its own test suite) and the `js/fc.js`-wired state models for removed features (geozone, safehome, waypoint, motorMixRule, logicCondition) — those stay because `fc.js` is the shared FC/MSP state object other retained tabs depend on.

One pre-existing, unrelated bug surfaced during verification: `js/appUpdater.js` throws because `window.electronAPI.appGetVersion(...)` isn't a Promise — not caused by anything in this fork's changes, not yet fixed.

## Verification approach

No dedicated test hardware, so tabs that only initialize once connected were verified by driving the running Electron app directly over its Chrome DevTools Protocol port (a small Node script talking to `ws://localhost:9222/devtools/page/...`), checking `element.offsetParent === null` for true rendered visibility (not just an element's own CSS) and capturing console exceptions.

## Distribution

Separate repo from this one on purpose — `sky-cob-configurator` needs its own git history to stay mergeable with `upstream` (iNavFlight/inav-configurator), and is a full Electron app versioned independently of this repo's hardware/build docs. A GitHub Release with a pre-built Windows package is the intended path for non-developers to get a working copy without installing Node.js.

## Upstream contribution

Not planned as a PR into `iNavFlight/inav-configurator` as-is — this fork deletes major functionality (Programming, Mission Control, PID Tuning, LED Strip, etc.) that other users need, so a diff like this would be rejected outright. If contributing back to help other balloon builders is wanted later, the right shape is a separate, additive-only effort against a fresh copy of upstream master: a "Weather Balloon" craft-type preset in the existing Setup Wizard (the one this fork removed) that applies balloon-sensible defaults and optionally hides irrelevant tabs via a toggle, with nothing removed for existing multirotor/plane/rover users.

## Open questions / risks

- **Upstream drift**: forking Configurator UI means periodically re-syncing with upstream INAV Configurator as MSP/CLI protocol or target list changes across INAV releases. Needs an explicit policy (e.g., track one INAV major version at a time).
- **Distribution/signing**: Electron app packaging/signing for Windows/Mac, same burden upstream Configurator already carries — no new problem introduced, just inherited.
- **License**: GPLv3 inheritance from inav-configurator requires this fork's source to also be published under GPLv3.

<details>
<summary>Original CLI-diff-generator sketch (superseded, kept for history)</summary>

The original plan was a "Balloon Profile" JSON document as the single source of truth, with a Save flow that would `diff all`, compute a delta against the profile, and emit a fresh `batch start … save` CLI script enforcing a strip-list on every save — regardless of what was in the UI. In practice this wasn't needed: reusing the existing per-tab MSP save chains (for day-to-day editing) plus a dedicated one-shot "apply the baseline" action (for initial setup, via the Balloon Setup tab) covered the real use cases with far less new code, and no protocol-level diffing was necessary since the curated CLI batch itself is idempotent — applying it twice produces the same result.

</details>
