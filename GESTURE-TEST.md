# Choose distinguishable gestures without changing positioning

Gesture testing/remapping leaves palm-center averaging, camera framing/resolution, four-corner calibration, homography, section geometry, stream coordinates, and the 0.70-score / 600-ms action gate unchanged. Given identical landmark coordinates, every pose mapping produces identical x/y (regression tested). Physically changing a hand pose can still move the detected landmark positions: keep the palm base in the same place during comparison.

## Run the comparison on Mac
Close the existing camera/garden launcher first so two processes do not contend for the webcam. Do not move the camera/tray or recalibrate. From the project folder run:

```sh
.venv/bin/python camera_stream.py --confirm-setup --gesture-test --camera 0
```

Use the same camera index, profile, rows, and columns as your working positioning run. For example, append `--rows 2 --cols 2` if your existing profile has four sections. This mode reads but never writes your saved calibration. It sends NO UDP samples or garden actions; an existing garden will time out if left open. The camera preview still shows your calibrated grid and palm-center ring.

Click the camera window. Press one number for each pose:

| Key | Pose | How to try it |
| --- | --- | --- |
| 1 | Closed_Fist | All fingers folded into fist |
| 2 | Open_Palm | Open hand, fingers spread |
| 3 | Victory | Index and middle fingers extended in V, others curled |
| 4 | Pointing_Up | Index finger extended, other fingers curled |
| 5 | Thumb_Up | Fist with thumb extended |

Each key starts a 3-second preparation period followed by 5 seconds of holding that pose, with one hand inside a plot and at normal interaction height. Keep the camera and your palm location fixed; adjust finger pose/orientation naturally. A key pressed during a trial restarts it. Q quits.

For each trial the preview/Terminal reports:
- Percentage of sampled frames with one hand inside the garden, the expected top model label, and score >=0.70. Lost hands, outside positions, and mismatched poses count against this score.
- Longest continuous matching run; it must reach 0.60 seconds for the existing action dwell to be feasible. Gaps >0.5 seconds and mismatches break the run.
- The labels seen instead, including unknown/unrecognized poses. Model scores are not calibrated probabilities.

Metrics only (no images/video) are saved under `output/gesture-trials-....json`. Try each candidate three times, releasing/changing pose between trials; then repeat the two best candidates over an edge plot and with another person. Prefer two distinct poses with high match percentage and repeatable >=0.60-second runs, and check that each isn't mistaken for the other. A single five-second hold does not establish visitor usability or false-activation rate. Test ordinary gardening/reaching before adopting the pair.

## Use a winning pair
No defaults change automatically. Example ONLY if V sign and pointing prove reliable:

```sh
.venv/bin/python start_camera_garden.py --confirm-setup --camera 0 --plant-pose Victory --cultivate-pose Pointing_Up
```

Both options are also available on camera_stream.py for separate Windows-camera/Mac-display runs. Defaults remain Closed_Fist and Open_Palm. Choose different poses for the two actions. Raw model labels are displayed separately from the existing wire action names (`closed_fist` = plant selection, `open_palm` = cultivation selection), preserving compatibility with garden.py. No text is submitted by a gesture.

Rearm by keeping your hand visible outside the tray, then hold the chosen pose in a plot. Existing unknown/confident non-command neutral poses can also rearm. Draft protection and one-action latch remain unchanged.

Reference: Google's supported built-in gesture categories and classifier model: https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer
