# Sky Cob — Weather Balloon Payload

Sky Cob is UWOSLAB's recoverable, high-altitude weather balloon payload. It's built around a SpeedyBee F405 Wing flight controller running INAV, packaged inside a 3D-printed shell, and monitored over an ELRS RC link. This repo holds everything needed to reproduce the payload build: the flight controller configuration, the radio (transmitter) model, and the 3D-printable enclosure.

> [!CAUTION]
> PLease read this description in full before starting!

## Repository contents

| File | What it is |
|---|---|
| `INAV_9.0.1_cli_SKY_COB_20260701_003845.txt` | INAV 9.0.1 CLI dump for the flight controller (target `SPEEDYBEEF405WING`). Paste/load this into the INAV Configurator CLI tab to reproduce the full flight controller setup. |
| `Sky Cob.yml` | EdgeTX/OpenTX radio model ("Sky Cob") for the transmitter — ELRS module setup plus telemetry screens (RSSI, GPS, altitude, battery, attitude, flight mode). |
| `cobshell.stl` | Main payload shell in upright position. |
| `cobby20x40.stl` | Reciever Mounting plate |
| `cobbyspeedy-top.stl` | Top mounting plate sized for the SpeedyBee F405 Wing FC. |
| `cobby19mm_cam_stand.stl` | Main Chassis for components. |
| `fix model.stl` | Current Shell model in printing orientation for 250x250 bed. |

## Hardware you'll need

- SpeedyBee F405 Wing flight controller (INAV target `SPEEDYBEEF405WING`)
- GPS module (uBlox; config uses SBAS/WAAS + Galileo + BeiDou + GLONASS) Preferred: HGLRC M100 Pro or Foxeer M10
- ExpressLRS receiver, Radiomaster DBR4 preferred.
- High power VTX. Read your VTXs manual for Band, Channel, Power, and Unlocking procedures.
- microSD card, for blackbox logging. Maximum 4GB usable, any extra space will not be utilized.
- 3D printer capable of printing the shell/mount parts above
- An EdgeTX/OpenTX-compatible transmitter with an ELRS module, for `Sky Cob.yml`. Preferred Module for ground station telemetry tracking: Radiomaster Nomad on a Radiomaster Boxer

## Setup

### 1. Print the payload shell and assemble

Print `cobshell.stl`, `cobby20x40.stl`, `cobbyspeedy-top.stl`, `cobby19mm_cam_stand.stl`, and `fix model.stl`. Test-fit the FC mount (`cobbyspeedy-top.stl`) against your actual SpeedyBee F405 Wing board before committing to a full print run, since mounting hole tolerances are easy to get slightly wrong between printers/materials.

> [!WARNING]
> Models and files are still WIP. Please check for any recent updates before starting.

FC in the Bay

GPS on top

RX and VTX on mounting plate through eachother (20x20, VTX out, RX in). Place subassembly on back standoffs (drill holes and use inserts for the 40x40 area.)

Battery and 5G tracker strapped through the 2 large holes towards the bottom

Camera on the very bottom

### 2. Flash and configure the flight controller (INAV 9.0.1)

1. Install the [INAV Configurator](https://github.com/iNavFlight/inav-configurator) Git release 9.0.2.
2. Flash the `SPEEDYBEEF405WING` target to the board. use INAV 9.0.1 when flashing.
> [!IMPORTANT]
> - Install ImpulseRC Driver Fixer if you have not already, this will let you install the DFU BOOTLOADER Drivers.
> - If target is not found automatically, check if a new COM port has been listed in the top right dropdown and select it before switching to the Firmware Flasher tab.
> - If flashing 9.0.1 from default configurator settings is unsuccessful, unplug the FC and hold down the boot button on the USB board while plugging it in. Select the new COM port and enable "No reboot sequence" in the flasher.
3. Connect to the board and open the **CLI** tab.
4. Load `INAV_9.0.1_cli_SKY_COB_20260701_003845.txt` (drag-and-drop or the "Load" button), or paste its contents directly into the CLI.
5. Let the batch run to completion — it ends with `save`, which reboots the FC with the new configuration.
6. Recalibrate the accelerometer (Calibration tab) — the dump includes calibration offsets (`acczero_*`, `accgain_*`, `gyro_zero_*`) taken from the original unit, and these won't be accurate for a different board. Recalibrate using standard board orientation, not the orientation it will be in once mounted.
7. In the **Modes** tab, review the `Arm` switch assignment. it should be set to Aux 5 with mid to high sections being enabled. OSD controls are on AUX6, 7, and 8.


Other defaults worth knowing about:
- `osd_units = IMPERIAL`, `tz_offset = -240` (EDT)
- `name = SKY COB`, `pilot_name = UWOSLAB`
- Blackbox is enabled and logs `NAV_POS`, `NAV_PID`, `MAG`, `ACC`, `ATTI`, `RC_DATA`, `RC_COMMAND`, `MOTORS`, `SERVOS` — insert a microSD card before flight.

### 3. Set up the transmitter

1. Use an EdgeTX/OpenTX radio (the model file targets EdgeTX 2.11.x — use EdgeTX Companion to convert if your radio runs a different version).
2. Copy `Sky Cob.yml` to the radio's `/MODELS` folder (via SD card, or open/write it through EdgeTX Companion), then select the **Sky Cob** model on the radio.
3. Confirm the external module is set to CRSF and internal is off.
4. if no telemetry is listed, check the telemeytry page for sensors. If no sensors are listed, select "discover sensors" and "stop discovery" once all sensors are listed and no more show up after 30 seconds.
5. Your telemetry pages should now list payload telemetry.

### 4. Pre-flight checklist

- [ ] Fully charged 3S/12V battery is inserted and plugged in. 
- [ ] microSD card inserted and formated for blackbox logging.
- [ ] GPS has a lock (multi-constellation: GPS + SBAS/WAAS + Galileo + BeiDou + GLONASS) 5-8 sats minimum before launch. takes 30 seconds to 3 minutes from cold start.
- [ ] VTX band/channel (R)ace Band, Channel 8, 5917Mhz, full transmit power.

### 5. Channel Mapping
> [!NOTE]
> The radio file is setup as prefered by 2theMAX. You may change switch layouts on your radio by going to the mixer tab and setting that channel to the desired switch.

| Function | Channel | Switch | Position |
|---|---|---|---|
| ARMING | 5 | SD | Mid-High (keep high )
| OSD Off | 6 | SC | High
| OSD 2nd Page| 6 | SC | Mid
| OSD 1st Page | 6 | SC | Low
| Beeper | 7 | SB | Mid-High

## Questions

For build-specific questions (frame fit, receiver binding, launch procedures), reach out to 2theMAX the Stair Fax directly.
