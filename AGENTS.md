# Poetree working location

The user designated this Git checkout as the canonical location for current and future Poetree / Prose Garden camera work:

`C:/Users/HP/art_practice/poetree-camera-transfer/poetree-camera`

Edit and verify files here. Earlier code in `C:/Users/HP/art_practice/everything-computer/poetree` and archives in the ChatGPT workspace are historical copies. Do not use them as the editing target or generate transfer archives unless requested. The user distributes changes using Git.

Preserve local modifications, accepted poems, output, virtual environments, and camera profiles. Inspect git status before editing. Do not commit or push unless requested.

Read CAMERA-START.md and CALIBRATION.md for the current runtime flow. CAMERA_PLAN.md documents integration with the existing garden. Run `python -m unittest -v` with the project dependencies installed, from this directory. Report physical camera / native Mac validation separately from synthetic tests.

Current interaction is one model-based click with root snapping: Thumb_Up by default selects either a nearby existing root for cultivation or empty ground for planting. The bundled model does not recognize pinch. Custom geometric gesture rules have been retired at the user's request; do not reintroduce custom models/rules as a claimed pretrained pinch detector. Preserve the working position anchor/calibration.

Latest user exception: they explicitly authorized testing the existing pinch rule alongside the model click. `--enable-pinch` adds an optional thumb/index-distance rule as a second source of the SAME click; this is not a pretrained pinch model and must be labeled experimental/rule-based. Default model-only operation, positioning, snapping, and the shared release latch remain unchanged.

The user now needs keyboard-free exhibit input. `--voice-input` reuses the existing online dictation path for contextual plant type, 1â€“5 poem words, and explicit spoken confirmation/retry/cancel after a hand click. Preserve target locking, bounded retries, stale transcript rejection, and no automatic submission of unconfirmed words. See VOICE-INPUT.md.

Exhibit hardware: M4 Mac mini, 16 GB. Local transcription is deferred at user request. Keep online Google recognition plus WebRTC VAD silence detection, bounded captures, confirmation and target locking. Future hardening may revisit a warm local model after native Mac accuracy/latency testing.

Single-click holds now require 2 seconds with teal cursor-ring progress. Preserve position calibration and root snapping. The optional pinch rule emits explicit open-pinch release; short uncertain classifications pause progress, tracking loss clears it. Paused voice retries accept a fresh hold on the locked target without requiring a tray exit.

Voice capture now allows 8 seconds to begin speaking, then the existing 4/7/4-second per-phase budget. WebRTC mode 1 and 1.4 seconds of trailing silence accommodate quieter speech and natural pauses. Preserve bounded retries; distinguish no-speech, unclear transcription, and network failures.

Fault-tolerant voice entry point: run_exhibit.py, documented in EXHIBIT-RUN.md. Preserve the stable accepted-word checkpoint, bounded retries, single-instance lock, normal-close semantics and corrupt-save refusal. Camera-only restarts preserve the live garden; process recovery discards unconfirmed drafts. Do not promise hang detection or native Mac reliability from simulated tests. Keep the original grass image; use cached smooth scaling.

Latest interaction: a fresh released-then-held pinch may confirm a displayed voice draft, as explicitly requested. Preserve the locked target and cancel/reject in-flight dictation results before submission. Optimistic click holds start at score .70 and ease toward .45; uncertainty grace grows with progress, but unknown alone cannot complete. MediaPipe None is uncertainty; explicit open pinch remains release.

Current user override: remove Undo, Read aloud and Stop visitor buttons and eliminate confirmation. Valid 1–5-word transcripts automatically plant/cultivate and checkpoint the locked target. This supersedes earlier confirmation requirements and pinch-confirmation behavior above. Preserve bounded retries, literal words in the thoughts phase, stale/duplicate rejection, optimistic hold progress and calibrated positioning. See current VOICE-INPUT.md.

Latest startup preference: run_exhibit.py starts a fresh empty garden on each manual launch, archiving the previous checkpoint under output/previous-sessions. Automatic crash recovery within that run still restores current accepted words. --resume explicitly continues the prior garden; --load explicitly imports a saved garden. Do not delete profiles or logs when starting fresh.

Voice thoughts longer than five words now keep the first five whitespace-separated words and automatically submit, with a brief truncation status. Preserve punctuation, empty/invalid-word checks and target locking; do not reject a phrase solely for exceeding five words.

Latest user override (October 25): persist plants/root locations across ALL normal shutdowns/restarts; run_exhibit resumes by default and --fresh is the explicit reset. Accepted JSON uses durable atomic writes and one previous backup; never promise recovery of in-flight speech or failed storage writes. Remove the five-word truncation: keep full valid phrases up to the existing 1500-word total per plant. --word-compression (default .35, range0..1) shrinks long forms around fixed roots; --growth-words defaults2 for new plants, smaller values branch faster, 0 retains legacy growth. Save growth settings per plant and preserve old layouts. --words-seconds defaults15. See TUNING.md. sync_garden.py exports a remote-readable JSON/Markdown snapshot; only explicit --publish commits/pushes the snapshot files. Do not run publish from this agent without a user request; the user will run it on the Mac. Automatic publishing is deferred.

User now explicitly requests automatic startup publishing: run_exhibit.py invokes sync_garden.py --publish --non-interactive in the background once per manual launch. --no-sync opts out; no periodic schedule. Preserve bounded non-interactive Git commands, separate sync lock and logs; network/auth/push failures never block the exhibit or delete local saves. Do not actually publish from this editing agent unless asked to run it.

Mouse voice fallback: run_exhibit.py --mouse-only forwards through the launcher without opening a camera. Mouse selection starts guided voice input; active sessions lock the target and paused sessions accept a click to retry. Voice-mode checkpoints must work without a HandReceiver. Keep overview during mouse voice cultivation so clicks are not swallowed by drag/zoom focus.

Flower-specific balance accepted by user: continue allocating words to stem/leaves (one stem, one leaf, three petal steps per cycle after establishment); cap head-driven stem spacing at 2x. Preserve one six-ray head, roots, every word and submission/history. Store flower_balance per session; legacy data validates with old grammar, then GardenApp transactionally rebalances old flowers in memory for the next normal checkpoint. Trees/ferns and camera mapping stay unchanged. See TUNING.md.

Latest hold timing: default .75 seconds, configurable --hold-seconds (0.2..5) through all launchers. Keep the teal progress ring as fast recognition feedback, optimistic evidence policy and release latch. This supersedes prior two-second timing. Mouse selection stays immediate.

run_exhibit.py now explicitly defaults camera0, microphone1, hold.75, compression.35, speech15s and growth2, per user request. Keep all flags overridable and --mouse-only as the camera-free fallback.
