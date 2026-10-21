# Packaging verification — 2026-10-21

Tracking-diagnostics update: three observation tests cover valid positions with uncertain poses (without allowing commands/rearm), outside-plane projection, and two-hand/slow-frame suppression. Full suite now has 48 tests. Live camera preview shows the palm anchor, tray grid, mapped coordinates, and separate failure reasons; uncertain gesture confidence alone no longer hides a valid garden cursor. Physical camera/Mac validation of this update remains required.

White-tape update: six additional synthetic tests cover four-corner detection/mapping, missing/extra/colored patches, search-box exclusion, dim thresholds, temporal stability, and calibration-loop A -> stable proposal -> explicit Enter -> saved profile. Full suite now has 45 tests. Real tape/soil/lighting and native Mac UI validation remain required. No new dependencies were added.

Executed on Windows with Python 3.12.2:

- `python -m unittest -v`: 39 tests passed, including existing poem/garden/dirt regressions and six camera-stream tests.
- Actual localhost UDP -> GardenApp -> fist selection -> first words -> palm selection -> append -> draft protection -> second plant -> draw -> save/reload -> undo/Finish passed.
- Accepted words loaded from an automatic checkpoint before full Save/PNG export.
- Regression for no_hand then command in one received packet batch passed; a hidden interruption no longer completes a prior dwell.
- `python -m pip check`: no broken requirements.
- Bundled MediaPipe model instantiated and ran on a 640x480 blank image; correctly returned no hands. This does not prove real gesture accuracy.
- Laptop camera index 0 opened and captured a 640x480 frame, released immediately. No camera image was saved or sent anywhere by this check.
- PyPI release metadata confirmed Python 3.12 Mac wheels for mediapipe 0.10.21 (universal2 and x86_64), jaxlib 0.4.30 (arm64/x86_64), and pygame 2.6.1 (arm64/x86_64). This is package availability evidence, not a native Mac runtime test.
- Independent reviewer inspected source fixes and retained a conditional staffed-exhibit verdict; see ADVERSARIAL_REVIEW.md.

Not performed: real fist/palm trials, physical calibration accuracy, overhead dirt/lighting trials, multiple visitor rehearsal, a native Mac run, or a two-computer LAN trial. Run these on the exhibit hardware before relying on camera interaction. Keyboard/mouse selection remains the fallback.

The archive excludes virtual environments, user poems/output, private speech caches, machine-specific camera calibration, and video recordings. A destination virtual environment and installation are required. The model is included so camera use needs no model download after dependency installation.
