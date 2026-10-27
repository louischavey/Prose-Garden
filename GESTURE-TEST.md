# Current gesture input: one pretrained-model click

The launcher defaults to one click gesture, Thumb_Up. The same click selects a nearby plant for cultivation or a new planting position on empty ground. There is no separate plant/cultivate gesture and no one-plant-per-section restriction in this mode.

The bundled MediaPipe model has no pinch class. The previous two-pose landmark classifier remains retired; --gesture-source landmarks is no longer supported. The user has now authorized a limited opt-in pinch rule alongside the model click, as described below. This is not a pretrained pinch model.

## Test pinch and thumbs-up simultaneously

```sh
.venv/bin/python start_camera_garden.py --confirm-setup --enable-pinch --camera 0
```

Use your working camera/profile/layout flags. Both a model Thumb_Up and the experimental pinch rule perform exactly the same click. No recalibration or new model/dependencies are required. Pinch by bringing thumb and index fingertips together in front of the palm, forming a small circle; a folded index/fist is deliberately rejected. Other fingers do not need a separate pose.

The rule compares the existing thumb/index tip distance with palm size and rejects a very short index reach. It uses existing estimated world landmarks when available, otherwise aspect-corrected image landmarks. It does not modify position coordinates, camera framing, calibration, or root snapping. Preview and garden identify Pinch as a rule; the score is a rule margin, not model confidence. `gap` shows the normalized tip separation.

The same 0.75-second hold and release latch serve BOTH inputs: changing thumbs-up to pinch while held cannot create a duplicate click. Exit the tray visibly to rearm before clicking again. Test accidental pinches during ordinary reaching/gripping before visitors; this rule has synthetic tests, not a physical reliability certificate.

For timed measurement only, run `camera_stream.py --confirm-setup --enable-pinch --gesture-test --camera 0`. Key 5 measures model thumbs-up; key 6 measures the pinch rule. This mode sends no actions and preserves the calibration file. Remove --enable-pinch to return to model-only clicks.

## Mac

After syncing Git changes on both capture and display machines, stop the old camera/garden and run:

```sh
.venv/bin/python start_camera_garden.py --confirm-setup --camera 0
```

Use your working camera index and existing rows/cols/profile. No recalibration is needed if nothing physical moved.

1. Move your visible hand outside the mapped garden for 0.3 seconds to arm. A confidently recognized non-click pose also releases the latch; losing tracking alone does not.
2. Move the cursor toward a plant. The yellow ring snaps to its root and says Cultivate this plant. Snapping uses root proximity, never a neighboring branch/word sprite. Hysteresis reduces rapid switching between close roots.
3. Over empty ground the cursor says Plant here; reserved edges cannot accept new roots. New roots use the actual cursor coordinate, not a grid center.
4. Hold thumbs-up for 0.75 seconds at score >=0.70 to click. The current target must stay stable. Then enter/dictate 1-5 words and submit with Enter/Water, as before.
5. Release/rearm before another click. A held gesture never continuously submits words. Unsubmitted drafts block changing targets. Accepted text is checkpointed; Finish blocks new edits.

Thumb_Up is selected because it was the only label reported by the exhibit setup, not because a reliable physical hold has already been demonstrated. Test actual clicks and ordinary reaching before visitors.

## Other supported click poses

Use --click-pose Open_Palm, Closed_Fist, Victory, Pointing_Up, or Thumb_Up on the launcher/sender. These are existing model labels; no training, custom model, or hand-geometry classifier is added. Do not lower confidence thresholds based only on the fact that a label occasionally appears.

## Measurement mode

```sh
.venv/bin/python camera_stream.py --confirm-setup --gesture-test --camera 0
```

This emits no garden packets and does not rewrite calibration. The preview continuously shows the model label/score without pressing any key. Keys 1 Fist, 2 Palm, 3 V sign, 4 Index, 5 Thumbs-up start a 3-second countdown and 5-second trial. Reports in output/ separate label, confidence, inside-position, and usable hold measurements. No hand images are saved. Zero matching actions can come from unknown labels, low confidence, outside mapping, or flickering; the report distinguishes these.

## Separate capture/display

Run garden.py --hand-stream on the display (click mode is now default), optionally --hand-host 0.0.0.0 for a trusted LAN. Run camera_stream.py --confirm-setup --host MAC_IP on capture. Both ends must be updated; use matching rows/cols and synchronized clocks. The --hand-click receiver flag remains accepted explicitly. Older two-pose compatibility is --interaction legacy on the launcher, or --legacy-hand-gestures on a standalone receiver plus --interaction legacy on capture.

Position anchor, camera settings, four-corner transform, and normalized stream x/y are unchanged. Display snapping changes the visible target and selection only. Stored plant roots and shared poem data remain intact.

Model reference: https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer
