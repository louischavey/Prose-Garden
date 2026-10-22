# Calibrate the dirt tray (manual or white tape)

Calibration teaches the program which quadrilateral in the camera is the physical garden, then divides it into your chosen equal rows/columns. It does not require moving your hand to train it, and it does not measure hand height or detect soil contact.

## Prepare
1. Fix the camera above the tray. Show all four outer garden corners plus some visible area outside the tray for rearming. Keep the camera still after calibration.
2. Choose the correct layout: default 2x3 = six sections; use `--rows 2 --cols 2` for four. Physical divisions must match the equal rectangular grid. If they do not, do not accept the overlay.
3. For tape detection, use four separate matte white patches, roughly square and about 2–4 cm across. They must appear as distinct, compact patches in the camera. Put their CENTERS at the four desired garden boundary corners, approximately at soil-surface height. Do not use a continuous white border. Keep other white objects/hands out of the search area. A raised rim or an offset marker defines a different plane/boundary; do not assume the program compensates for that offset.

## Start on Mac
From the extracted project folder, with the environment installed:

```sh
.venv/bin/python start_camera_garden.py --calibrate --camera 0 --rows 2 --cols 3
```

Keep the camera index that already works for you. For four plots replace `--cols 3` with `--cols 2`.

## White-tape calibration (new)
1. Click the camera calibration window to give it keyboard focus. Keep hands out of view. Press **A**.
2. The detector looks for exactly four bright, low-saturation, compact white patches. It requires eight stable camera frames, then freezes their centers as a proposed calibration. Extra/missing patches prevent a proposal; it never saves by itself.
3. If it finds other white objects, press **B**, drag a box around the tray including all four patches with some margin, and press Enter to finish the search box. Detection restarts inside that box. The box only limits tape search; it is not the calibrated garden boundary.
4. Press **M** to inspect the black/white detection mask if needed. The tape should appear white and soil black. **-** lowers the brightness threshold for dim tape; **+** raises it to reject dimmer distractions. These keys restart detection. If tape is strongly colored by lighting, change lighting or use manual clicks; saturation adjustment is not exposed.
5. Check numbered corner dots: 1=top-left, 2=top-right, 3=bottom-right, 4=bottom-left as seen in the unmirrored camera. Four identical tape patches have no encoded orientation, so a rotated/ambiguous setup must be corrected manually if the proposal labels are wrong.
6. Check the green plot grid against the actual dirt-section boundaries. If wrong, press A to try again, or R for manual correction. **Press Enter only when the corners and grid are correct.**
7. The program saves `camera-profile.json`, closes the calibration window, starts recognition, and streams to the garden. Tape detection is a setup aid; the saved mapping stays fixed during interaction. It does not automatically follow a bumped camera or drifting tray.

## Manual calibration (also works in the original package)
Press **R**, then click these four positions in the camera image, in order:

1. Top-left garden corner / tape center.
2. Top-right garden corner / tape center.
3. Bottom-right garden corner / tape center.
4. Bottom-left garden corner / tape center.

The grid appears after click four. R clears all clicks if you make a mistake. Enter saves only a valid four-corner shape. Q/Escape cancels. The original package uses this manual workflow and has no A/B/M tape controls.

## Check before visitors

Tracking diagnostics: the live preview now outlines the mapped tray/sections and draws a large ring at the palm-center anchor (wrist plus finger bases), not at the fingertips. Red ring / outside means the projected palm center is outside the mapping: lower/move the hand inside or correct calibration. A valid position draws the garden cursor even if gesture confidence is low; the pose still needs score >=0.70 to act or rearm as a neutral pose. Two hands and slow processing are reported separately and suppress location/actions. With an oblique camera, fingertips over the tray do not guarantee that the palm-center projection is inside. Prefer a more downward-facing view and test at actual hand height. Rotated/reversed section labels require correcting the corner-click order.
Move one hand above the center of each physical section. On empty ground, check that the yellow cursor lands in the matching numbered area. Near existing roots, click mode intentionally snaps the display cursor to a nearby root; the camera's palm ring still shows the original position. Also check boundaries and actual hand heights. The mapping calibrates the surface; an elevated hand may appear shifted by perspective. Fix camera geometry/margins if it selects the wrong target. Tape detection is not proof of hand accuracy.

To click, keep your hand detectable while moving outside the tray for 0.3 seconds, then hold thumbs-up (or your configured model click pose) at the intended target for 0.6 seconds. A snapped root is selected for cultivation; empty ground becomes a new planting location. Type/dictate words in the garden and press Enter/Water. Startup's "camera stream stopped" disappears only after calibration finishes and packets begin arriving.

For another run with the same unmoved setup:

```sh
.venv/bin/python start_camera_garden.py --confirm-setup --camera 0 --rows 2 --cols 3
```

Recalibrate after moving camera/tray, changing source/framing, or changing soil level materially. White tape can be removed after saving if nothing else moves.

## Evidence and limits
Synthetic image tests cover skewed four-patch geometry, missing/extra patches, colored distractions, a restricted search box, dim tape thresholds, and temporal stability. This implementation has not been tested against your actual tape, soil, camera, or lighting. White objects/reflections can mimic tape, which is why operator confirmation is required. This detects white appearance, not tape material identity.

Implementation follows OpenCV HSV inRange thresholding and morphological cleanup:
https://docs.opencv.org/4.x/da/d97/tutorial_threshold_inRange.html
https://docs.opencv.org/4.x/d9/d61/tutorial_py_morphological_ops.html
