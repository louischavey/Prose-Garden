# Poetree camera stream: implementation and five-hour exhibit feasibility

## 1. Scope and verified source context
Target: existing Python/Pygame garden.py in this folder. One visitor at a time puts a hand over one dirt tray divided into four to six sections. Fist requests planting; palm requests cultivation. Reuse the actual poem generator, editable draft, Water/Enter submission, speech, undo, and JSON/PNG saves. This document supersedes the earlier browser-based IMPLEMENTATION_PLAN.md in the chat workspace.

GARDEN.md's Tap API and garden.py define normalized ground coordinates x,y in [0,1], measured across grass only, not the whole display. WORLD=(1200,800) is model/rendering scale. handle_garden_tap has no gesture argument and can select word sprites. handle_dirt_tap selects root ownership but assumes a legacy 4x6 probe grid. Camera mode must bypass that sensor grid and foliage hit-testing. The underlying Garden.plant and Garden.water_plant are unchanged.

## 2. Implemented data path
camera_stream.py captures a camera with OpenCV and runs MediaPipe Gesture Recognizer's Closed_Fist/Open_Palm classes. A consistent palm-center anchor averages wrist and four finger-base landmarks. A four-corner homography maps image position into normalized garden coordinates. No video is streamed; UDP sends location, gesture, score, identity, and status to Python hand_input.HandReceiver. garden.py polls it on the UI thread and uses IntentGate for one intentional selection per held gesture. start_camera_garden.py launches both processes on Windows or macOS using the current Python interpreter. Localhost is default; capture can also run on Windows and send to a Mac on a trusted LAN.

Packet (new protocol; not a pre-existing garden wire format):

```json
{"version":1,"session":"unique-run-id","calibration":"setup-id","seq":42,"sent_at":1792600000.12,"rows":2,"cols":3,"state":"ok","x":0.42,"y":0.63,"gesture":"closed_fist","score":0.93}
```

States: ok, no_hand, ambiguous, outside, uncalibrated. Non-ok samples clear x/y. Gesture is closed_fist, open_palm, or unknown. Score is a model category score. Two visible hands or uncertain recognition disable commands. UDP datagrams are bounded, validated, drained to newest state, checked for sequence order, and rejected if wall-clock age exceeds 0.5 seconds. Both machines must have synchronized automatic date/time for LAN mode. No authentication: bind publicly only on a trusted exhibit LAN. Receive timeout clears pending intent. Reconnection requires neutral/exit before commands can fire. Source changes wait for current stream to stop before taking over.

## 3. Interaction contract and exhibit flow
Initial camera layout: configurable equal rectangular sections, default 2 rows x 3 columns; 2x2 for four. One plant root per section; continuous x,y remains in the packet, but a new root is placed at the section center adjusted into existing safe planting bounds. The number of rows/columns must agree between camera calibration and receiver. The actual physical arrangement is still unverified. Arbitrary polygons, unequal sections, and per-section screen warps are future scope, not implemented.

1. Visitor approaches alone. Attendant or sign asks them to move hand outside the tray (or show a confident non-command pose) for 300 ms to arm.
2. Hold fist or palm over the intended numbered section for 600 ms. A boundary margin suppresses commands near internal divisions. A second hand or loss of tracking cannot complete confirmation.
3. Fist on empty section sets pending location; fist on occupied section gives a cue. Palm on an occupied section selects that exact root's plant ID; palm on empty section gives a cue. Multiple saved roots in a section are ambiguous and require mouse selection. Branches overlapping other plots do not transfer ownership.
4. Visitor chooses plant type for a new plant, types 1–5 words, and presses Enter/Water. Optional existing dictation creates an editable draft and requires submission; it needs microphone permission and internet. The gesture never submits text. Existing draft-switch guards prevent moving words to another plant. Hover only draws a cursor and does not cancel dictation/speech.
5. Visitor can append more words or leave. Next visitor explicitly releases/rearms and selects a plot. Existing code provides no visitor identity, authorship verification, automated session timeout, private draft cleanup, or automatic handoff. Attendant must resolve abandoned drafts (submit or Escape) and explain controls.

A held pose fires once. Fist-to-palm does not rearm. Tracking loss does not release a fired latch. Finish prevents edits. Mouse remains a fallback. Existing bounds, plant spacing, renderer, accepted-text validation, and undo semantics remain authoritative. Camera mode now writes an atomic JSON recovery checkpoint after every accepted Water/Undo; full Save/normal close additionally exports PNG. Unsubmitted drafts are not persisted. Rejected camera selection clears the old target when no protected draft exists. Intermediate observations within a drained packet batch are passed through the intent gate so a hidden tracking/pose interruption cannot complete dwell.

## 4. Calibration and testing before dirt

White-tape setup update: camera_stream.py now offers A to detect four compact bright, low-saturation corner patches; it requires eight stable frames and explicit Enter confirmation. B selects a search box, M shows the threshold mask, +/- adjusts brightness, and R returns to manual selection. Tape centers define the boundary: arrange them at desired corners at soil-plane elevation. Identical white patches do not encode orientation or material identity; inspect the numbered overlay. This is setup-only detection, not continuous tracking or movement correction. See CALIBRATION.md. The independent review predates this feature; its physical-validation caveats still apply.
Use paper/cardboard with the same section arrangement as the actual tray, at intended soil-surface height. Select camera index (0/1/2), click tray-plane corners TL/TR/BR/BL, inspect numbered boundaries, then Enter to save. Profile records camera index, frame dimensions, layout, reference corners, and calibration ID. Saved profile requires explicit --confirm-setup; moving camera/tray, changing camera, or changing framing requires recalibration. Camera index is not a stable hardware identity. No automatic movement detection is implemented.

Distance alone does not define the mapping: lens, angle, crop, and resolution also matter. Homography corrects a plane, not the unknown height of a visitor's hand above soil. Even an overhead camera has parallax away from its optical axis. Camera preview is deliberately unmirrored. Lens-distortion correction, marker auto-calibration, true hand height/contact sensing, and arbitrary layouts are deferred.

Before dirt, test both poses at every section center and near every internal boundary, five two-second trials at the surface and measured 10/20 cm heights. Compare independent intended targets with reported cursor/section, not the fitted corners alone. Repeat from the intended temporary overhead camera geometry; normal laptop-front-camera success cannot certify overhead behavior. Record camera height/tilt, resolution, light, hand height, and misses/wrong sections. Repeat with three people, both hands, and representative lighting.

Those five-trial checks are screening, not the 20-trial acceptance measurement below. For a five-hour staffed prototype, choose one intended height band and lighting configuration, screen all plots first, then run 20 intentional selections per pose at the center and worst-performing edge section. Record exactly which conditions passed; do not extrapolate a full multi-height/person matrix from this subset. Keep visible space outside the tray in the camera frame for rearming, or demonstrate a reliably recognized neutral pose. Four/six occupied sections cap new plants; later visitors cultivate existing ones.

Suggested acceptance: 19/20 correct intentional selections per pose/condition; no duplicates during five-second holds or fist-to-palm transitions; at least 95% correct section assignments outside the boundary margin; no unwanted action in a five-minute ordinary gardening/reaching trial. These are prototype gates, not claims of measured real-world reliability. Physical testing remains required after installation with dirt and real visitors.

## 5. Automated verification and portability
test_hand_input.py exercises actual localhost UDP reception through GardenApp, fist selection, first word submission, palm selection, append, protected draft, second plant, PNG draw, save/reload, undo, and Finish. Also test malformed/stale/reordered packets, holds/rearm, tracking loss, boundary ambiguity, and homography reference points. Run the existing garden/poem/dirt suite as regression coverage. Synthetic tests verify plumbing; they do not validate webcam recognition.

Use Python 3.12 and create a fresh virtual environment on the destination; do not transfer Windows .venv. requirements-camera.txt pins camera dependencies with Mac/Windows wheel availability checked during packaging. Receiver-only Mac needs requirements-garden.txt and can consume the Windows camera stream. Bundle official version-1 gesture model and grass asset with provenance. Exclude recordings, existing poems, caches, virtual environments, and camera profiles. Native Mac camera permissions, capture backend behavior, and actual overhead gestures remain untested on this Windows host.

## 6. Five-hour delivery target and cut lines
This is a staffed prototype target, not a guaranteed unattended exhibit. Suggested remaining on-site allocation after transferring tested software:

- 0:00–0:45: install Python dependencies, launch model/garden on actual Mac, verify display and camera access. If Mac capture fails, run capture on the Windows laptop and UDP to receiver-only Mac; test clocks/network/firewall.
- 0:45–1:30: temporary overhead mount, paper/tray calibration, center and boundary checks at expected hand heights.
- 1:30–2:30: gesture thresholds and release instruction trials with several people; test ordinary open-hand gardening motions for false cultivation.
- 2:30–3:30: rehearse full walk-up, select, type/dictate, submit, leave, next visitor flow; verify abandoned draft recovery and save/reopen. Keyboard is the offline baseline; cut online voice if unreliable.
- 3:30–4:15: add dirt and final lighting; recalibrate and repeat mapping/gesture gates.
- 4:15–5:00: end-to-end soak, queue/attendant instructions, backups and fallback rehearsal. If recognition/mapping fails, use mouse selection with the same garden rather than claiming camera reliability.

Do not spend this window on automatic ArUco setup, custom gesture training, multiple simultaneous visitors, automatic authorship checks, arbitrary plant placement in camera mode, or hands-only text entry. If there is no working webcam/mount/display hardware early in the window, five-hour feasibility becomes low confidence. The software alone cannot certify that exhibit flow.

## 7. Reference implementations
- Google Gesture Recognizer Python guide and examples: https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer/python
- OpenCV homography Demo 2 (planar perspective correction): https://docs.opencv.org/5.0/tutorials/features/homography/homography.html
- Future marker board setup: https://docs.opencv.org/5.0/tutorials/objdetect/aruco_board_detection/aruco_board_detection.html
- Future lens calibration: https://docs.opencv.org/4.13.0/dc/dbb/tutorial_py_calibration.html
