# Packaging verification — 2026-10-21

Optional simultaneous pinch update: five tests cover adding a pinch click while preserving exact position fields; keeping the model click available; rejecting open/folded/nonfinite or suppressed cases; a single shared click despite switching pinch/thumbs-up; and production sender packets with --enable-pinch while preserving the saved profile. Full suite now has 63 passing tests. Pinch is an experimental landmark-distance rule, not a pretrained model; it remains disabled by default and unverified on exhibit hardware.

CURRENT single-click update: removed the five custom landmark-classifier tests and implementation, and added five tests for root snapping/hysteresis, click hold/release and target changes, empty-ground movement resets, loss interruption, and actual UDP -> cursor planting/cultivation -> protected draft -> multiple roots per section -> save/Finish. Full suite remains 58 passing tests. The current flow uses only the bundled pretrained model; pinch is not a supported label. Position/calibration math is unchanged. Older entries below are historical and do not mean the retired custom source is still available.

Opt-in landmark-gesture source: five additional tests cover Pinch/Open_Palm rules across synthetic rotations/scales, closed-fist rejection despite thumb/index contact, degenerate/nonfinite geometry, source-default validation, and successful intent-gate events when the preset model label is wrong while preserving identical cursor coordinates. Full suite now has 58 passing tests. The geometric rule margin is not a model probability; physical validation with the exhibit camera is outstanding. Default model mode and all position/calibration calculations remain unchanged.

Zero-score diagnostics: reporting now separates model-label matches, confidence, position, and tracking rejection instead of presenting a combined 0% alone. One regression distinguishes three different zero-score causes: recognized pose outside the plot, unrecognized pose inside, and recognized label below confidence threshold. Full suite now has 53 tests. No camera/landmark/calibration or action-threshold changes in this diagnostic update.

Gesture-only comparison update: four additional tests cover coordinate/anchor invariance across pose remappings; timed trial scoring, confusions and interruptions; and running the production test-mode loop with no UDP sends and no saved-profile changes. Full suite now has 52 passing tests. Camera calibration/mapping/anchor and the 0.70-score/600-ms action gate remain unchanged. New gesture candidates require physical comparison on the exhibit camera; no alternate pair has been automatically adopted or certified.

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
