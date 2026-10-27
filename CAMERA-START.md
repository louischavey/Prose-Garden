Current persistence and tuning: normal run_exhibit.py restarts now RESUME accepted plants/locations; --fresh explicitly archives and clears. Thoughts are no longer truncated to five words. See TUNING.md for --word-compression, --growth-words, --words-seconds and remote Git snapshots.

Current voice interaction: Type (new plant only), then Thoughts. Valid 1�5-word transcripts save automatically; there is no confirmation step or Undo/Read aloud/Stop visitor button. This supersedes older interaction descriptions below. See VOICE-INPUT.md.

For the fault-tolerant voice exhibit, run `.venv/bin/python run_exhibit.py --camera 0`. See EXHIBIT-RUN.md for importing current poems, crash recovery, logs and limits.

# Run Poetree on Mac or Windows

Keyboard-free input is available with `--voice-input`: after a hand click, speak plant type for a new root, then 1–5 words, then confirm/retry/cancel. Start with `start_camera_garden.py --confirm-setup --enable-pinch --voice-input`. See **VOICE-INPUT.md** for microphone permissions/device selection, recording windows, and the full visitor flow. It uses the existing online Google transcription service and never saves words without confirmation.

This Git checkout is the current project. Pull committed updates on the display Mac from the same repository; retain its local virtual environment, camera profile, and saved poems. Stop Poetree before updating its source. The Windows editing location is `C:/Users/HP/art_practice/poetree-camera-transfer/poetree-camera`. Earlier zip-transfer instructions below also apply to a fresh checkout.

The current default is **one model-based click with root snapping**. Thumb_Up is the click pose; it cultivates a nearby highlighted root or selects a new location on empty ground. Use `--click-pose` for another supported model label. The bundled model has no pinch label, and custom landmark classifiers have been removed. See **GESTURE-TEST.md** for current interaction and measurements. Your position anchor/calibration remain unchanged.

Optional simultaneous comparison: add `--enable-pinch` to your usual launcher command to accept an experimental thumb/index pinch rule OR the model's thumbs-up as the same click. The rule is explicitly labeled and does not change position/calibration or snapping. It needs physical testing; see GESTURE-TEST.md. The previous two-pose landmark classifier is not restored.

Use Python **3.12**, macOS 11+ (Apple Silicon or Intel) or 64-bit Windows. Create the environment on that computer. The archive includes source, tests, grass asset, and the gesture model; it excludes old poems and machine-specific profiles.

## Mac: camera and garden on the same computer

In Terminal, change into the extracted `poetree-camera` folder, then:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-camera.txt
.venv/bin/python start_camera_garden.py --calibrate
```

Allow camera access for Terminal/Python when macOS asks. Close other apps using the webcam. Camera 0 is the default; try `--camera 1` or `--camera 2` for USB cameras. Use a rigid temporary overhead mount and an outline of the tray before adding dirt.

Press **A** in the calibration preview to detect four white tape patches at the tray corners, or click **top-left, top-right, bottom-right, bottom-left** manually. Inspect the numbered sections, then press Enter to accept. B limits tape search to a selected box; M shows the mask; +/- adjusts tape brightness; R resets for manual clicks; Q cancels. See **CALIBRATION.md** for placement and the full walkthrough. Use `--rows 2 --cols 2` for four sections (default is six in 2x3). This build assumes equal rectangular sections. Do not substitute an unrelated grid for the real layout.

Frame some visible space **outside the tray** so a hand remains detectable while leaving it. A completely invisible hand does not rearm (it could be tracking loss). Alternatively show a confidently recognized non-click pose. Allow one visitor at a time. The six-section overlay is a visual reference; click mode supports multiple roots in a section, subject to existing spacing/plant-count limits.

Later, if camera/tray/layout have stayed exactly in place:

```sh
.venv/bin/python start_camera_garden.py --confirm-setup
```

Recalibrate after moving or swapping camera, moving tray, or changing framing. Windows profiles are deliberately not packaged. The display Mac needs its own calibration if it captures the camera.

One visitor at a time: move a visible hand outside the tray to arm, point at a root or empty ground, then hold thumbs-up for 0.75 seconds to click. The snapped root is highlighted and labeled Cultivate this plant; empty ground says Plant here. Then **choose type for a new plant, type 1–5 words and press Enter/Water**. A click selects; it never submits words. Release/rearm before another click. Optional Mic creates an editable online dictation draft; keyboard works offline. Escape clears an abandoned draft. Accepted Water/Undo actions automatically checkpoint JSON in camera mode. Close the garden window normally to also export PNG. Save output is in `output/`.

## Windows: same code

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-camera.txt
.\.venv\Scripts\python.exe start_camera_garden.py --calibrate
```

## Camera on Windows, garden displayed on Mac

Both machines must be on a trusted LAN with automatic date/time synchronized (packets older than 0.5 seconds are rejected). Allow UDP port 8765 through the Mac firewall if prompted. This transport is unencrypted and unauthenticated; localhost is preferred when practical.

Mac receiver only (does not need MediaPipe/OpenCV):

```sh
.venv/bin/python -m pip install -r requirements-garden.txt
.venv/bin/python garden.py --hand-stream --hand-host 0.0.0.0 --gallery-mode
```

Windows sender (replace `MAC_LAN_IP` with the display Mac's LAN address):

```powershell
.\.venv\Scripts\python.exe camera_stream.py --host MAC_LAN_IP --calibrate
```

Use `--confirm-setup` for an unchanged sender setup. If using four sections, pass `--hand-rows 2 --hand-cols 2` to garden.py and `--rows 2 --cols 2` to camera_stream.py. The camera process owns calibration; the receiver never needs a physical camera.

## Test without a webcam

Launch `garden.py --hand-stream` in one terminal and `demo_hand_stream.py` in another using your virtualenv Python. In the simulation window, point with the mouse, release keys briefly, then hold Space/F to click. Switch to the garden window to type and submit words. Only the focused simulator sends actionable poses.

```sh
.venv/bin/python -m unittest -v
```

This checks software flow; camera recognition and calibration need the real camera. If installing receiver-only dependencies, run `test_garden`, `test_plant_poem`, and `test_dirt_input` instead of the camera suite.

## Recovery and limits

- No stream: check host/port/firewall and matching layouts. Sender messages say where it is streaming. Keep clock synchronization enabled for LAN streaming.
- Camera missing/permission denied: choose another index, grant OS camera permission, restart capture, and recalibrate. Do not assume USB index identifies the same physical device across reboots.
- Click pose not recognized: test orientation/lighting first; inspect the model label and score, then choose a supported alternative with --click-pose if necessary. Keep one visible hand. This release needs physical validation and is not certified unattended.
- Selected plant won't change: submit the existing draft or Escape to discard it. Multiple roots in a section need mouse selection. Mouse controls remain available.
- Resume saved work with `--load output/garden-....json` on the launcher (or garden.py in receiver-only mode). Load does not restore camera calibration.
- On exit, close the garden normally to save accepted text; a forced kill cannot save an unfinished draft.

See CAMERA_PLAN.md and ADVERSARIAL_REVIEW.md for scope, test evidence, and exhibit feasibility. Online dictation/speech use the services already described in GARDEN.md; hand video processing stays local. No native Mac or real visitor test has been performed by this Windows packaging run.
