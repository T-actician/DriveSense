# DriveSense

Real-time driver fatigue and drowsiness detection for Windows. DriveSense uses a USB webcam to watch the driver's eyes, blinking, yawning and head position, calculates a live fatigue score, and warns the driver with sound, voice and on-screen alerts. Everything runs locally on your PC, with no cloud and no special hardware.

Powered by Tactician°™

## Download

1. Go to the [latest release](https://github.com/T-actician/DriveSense/releases/latest).
2. Under **Assets**, download **`DriveSense-Setup-x.x.x.exe`**.
3. Do **not** download "Source code (zip)" or "Source code (tar.gz)". Those are for developers and will not install or update.

Run the installer, then open **DriveSense** from the Start menu.

Windows SmartScreen may warn that the app is unrecognised because the installer is not code-signed yet. Click **More info**, then **Run anyway**.

## Updates

Installed copies of DriveSense update themselves automatically. The app checks for new versions in the background and asks you to restart when one is ready. You never need to download from GitHub again.

## First use

1. Plug in your webcam and open DriveSense.
2. Press **Space** (or click Start Calibration). Look at the camera and blink normally for 8 seconds, then close your eyes when you hear the beep and open them at the second beep.
3. Monitoring starts automatically.

Press **C** at any time to recalibrate. Press **F11** for fullscreen. Use the gear icon for settings, including voice alerts on or off.

## Alert levels

| Level | Meaning | Alert |
|---|---|---|
| Normal | Driver alert | None |
| Caution | Early signs of fatigue | Soft beep and voice suggestions |
| Warning | Drowsiness detected | Beeps and "Wake up! Keep your eyes on the road!" |
| Critical | Eyes closed or head down | Continuous alarm and "Wake up! Pull over when safe!" |

## Using a different camera

DriveSense uses your default camera. To use another one (for example a USB webcam when your laptop also has a built-in camera), create the file `%APPDATA%\DriveSense\settings.json` containing:

```json
{ "cam": 1 }
```

Use `0` for the first camera, `1` for the second, and so on, then restart DriveSense.

## Requirements

- Windows 10 or 11 (64-bit)
- A webcam with a clear view of the driver's face

## Important

DriveSense is a prototype. It is not a certified safety system and must not be your only safeguard against drowsy driving. If you feel tired, stop and rest.

## Run from source

```
git clone https://github.com/T-actician/DriveSense.git
cd DriveSense
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
npm install
npm start
```

Build the installer with `npm run dist`.