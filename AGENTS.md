# Poetree working location

The user designated this Git checkout as the canonical location for current and future Poetree / Prose Garden camera work:

`C:/Users/HP/art_practice/poetree-camera-transfer/poetree-camera`

Edit and verify files here. Earlier code in `C:/Users/HP/art_practice/everything-computer/poetree` and archives in the ChatGPT workspace are historical copies. Do not use them as the editing target or generate transfer archives unless requested. The user distributes changes using Git.

Preserve local modifications, accepted poems, output, virtual environments, and camera profiles. Inspect git status before editing. Do not commit or push unless requested.

Read CAMERA-START.md and CALIBRATION.md for the current runtime flow. CAMERA_PLAN.md documents integration with the existing garden. Run `python -m unittest -v` with the project dependencies installed, from this directory. Report physical camera / native Mac validation separately from synthetic tests.

Current interaction is one model-based click with root snapping: Thumb_Up by default selects either a nearby existing root for cultivation or empty ground for planting. The bundled model does not recognize pinch. Custom geometric gesture rules have been retired at the user's request; do not reintroduce custom models/rules as a claimed pretrained pinch detector. Preserve the working position anchor/calibration.

Latest user exception: they explicitly authorized testing the existing pinch rule alongside the model click. `--enable-pinch` adds an optional thumb/index-distance rule as a second source of the SAME click; this is not a pretrained pinch model and must be labeled experimental/rule-based. Default model-only operation, positioning, snapping, and the shared release latch remain unchanged.

The user now needs keyboard-free exhibit input. `--voice-input` reuses the existing online dictation path for contextual plant type, 1–5 poem words, and explicit spoken confirmation/retry/cancel after a hand click. Preserve target locking, bounded retries, stale transcript rejection, and no automatic submission of unconfirmed words. See VOICE-INPUT.md.

Exhibit hardware: M4 Mac mini, 16 GB. Local transcription is deferred at user request. Keep online Google recognition plus WebRTC VAD silence detection, bounded captures, confirmation and target locking. Future hardening may revisit a warm local model after native Mac accuracy/latency testing.

Single-click holds now require 2 seconds with teal cursor-ring progress. Preserve position calibration and root snapping. The optional pinch rule emits explicit open-pinch release; short uncertain classifications pause progress, tracking loss clears it. Paused voice retries accept a fresh hold on the locked target without requiring a tray exit.

Voice capture now allows 8 seconds to begin speaking, then the existing 4/7/4-second per-phase budget. WebRTC mode 1 and 1.4 seconds of trailing silence accommodate quieter speech and natural pauses. Preserve bounded retries; distinguish no-speech, unclear transcription, and network failures.
