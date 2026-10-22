# Keyboard-free plant type, words, and confirmation

This reuses sounddevice capture and adds WebRTC VAD for speech detection. Google transcribes online and needs internet plus microphone access. Audio is sent to Google. Recordings stay in memory.

## Start on Mac

After syncing source changes, keep the camera/tray in place and run:

```sh
.venv/bin/python start_camera_garden.py --confirm-setup --enable-pinch --voice-input --camera 0
```

Use your working camera/profile/layout flags. Allow microphone access for Terminal/Python in macOS Privacy & Security if prompted. The microphone is local to garden.py: for Windows capture and Mac display, enable --voice-input on the Mac receiver, not camera_stream.py.

## Visitor flow (one person at a time)

1. Release/rearm, point, and hold pinch/thumbs-up for 2 seconds to click. The circular cursor fills clockwise in teal as valid hold time accumulates. Position tracking and root snapping are unchanged.
2. Watch the screen and **wait for Listening before speaking**. The microphone is not always on. A new planting asks for **flower**, **tree**, or **fern** (4-second recording). Tree maps to the existing conifer type. An existing plant skips type selection.
3. The next Listening prompt asks for **1–5 poem words** (7-second recording). It transcribes online, then shows the draft. No poem changes yet.
4. Review the displayed words/type. When Listening appears again (4-second command recording), say exactly **confirm**, **retry**, or **cancel**. Yes is accepted as confirm; try again/no means retry. Change type returns a new planting to the type question.
5. Confirm uses the existing transactional Water action and JSON checkpoint. Retry clears just the current unsubmitted draft and re-records words. Cancel discards the current draft/selection without modifying any accepted poem.
6. After saving, the microphone stops. The next visitor/entry starts with a new hand click. Further clicks during entry cannot redirect the draft. No keyboard, Mic button, or Water button is required in this flow.

Recordings now end after speech plus about 1.4 seconds of silence. You have up to 8 seconds to begin speaking; the 4/7/4-second limits start when speech is detected. Detection uses the less aggressive WebRTC mode 1 to retain quieter speech. No detected speech triggers a retry without transcription. Wait through Transcribing and the next Listening message rather than speaking during the gap. Poem words are interpreted as text only during the words phase: e.g. confirm can itself be a poem word. Commands are interpreted during separate review.

After three recognition/validation failures, recording pauses. Hold pinch for 2 seconds to retry the SAME target/phase. On entering this paused state, hold progress starts fresh and you can retry without leaving the tray. This keeps bad network/audio from recording indefinitely. Network or microphone failure cannot save an unconfirmed contribution. Stop pauses voice input while keeping a draft; the Mic button can restart voice review as an operator fallback. Read-aloud is blocked during active voice entry to avoid recording playback.

## Select a microphone

List sounddevice devices:

```sh
.venv/bin/python -c "import sounddevice as sd; print(sd.query_devices())"
```

Then add `--mic-device 2` (replace 2 with an INPUT device index) or a distinctive microphone name. Default is the system input. `--speech-language en-US` chooses transcription language; plant/type commands currently use the English phrases above. Output-only devices do not work as microphone inputs.

Receiver-only example:

```sh
.venv/bin/python garden.py --hand-stream --voice-input --hand-host 0.0.0.0 --gallery-mode
```

Enable --voice-input only in single-click mode. Existing manual keyboard/Mic behavior remains available when the flag is omitted.

## Verification boundary

Synthetic integration tests cover new plant/type/words/explicit confirmation, cultivation without reselecting type, checkpoint recovery, retry/cancel, invalid word counts, bounded failure/retry, stale transcript rejection, and the microphone worker's result/busy-state order using mocked capture/transcription. Test the actual Mac microphone, permissions, internet, gallery noise and entire visitor exchange before exhibition. No live microphone/cloud recognition was exercised during this Windows code test run.

## Exhibit display

The side panel shows Type / Words / Confirm, recording or transcription state, and the draft awaiting confirmation. It replaces the keyboard entry controls in voice mode. Cultivation keeps the chosen plant selected after submission, with the original cream root marker, other plants faded, and a persistent SELECTED label. Camera mode focuses attention in the full garden without zooming or changing the calibrated cursor coordinates; choosing empty ground clears that focus. Cursor labels use cream lettering on solid dark green. The original grass stays vivid inside the planting border, with greyed reserved edges.

## Future hardening

Exhibit hardware: M4 Mac mini, 16 GB. Local transcription is deferred; current recognition uses Google. Retain WebRTC VAD, confirmation and target locking. Validate speech endings, pauses, gallery noise and end-of-speech to transcript latency on the Mac.

Pinch reliability: an explicitly open thumb/index gap rearms the optional pinch rule without needing a named model gesture. Brief uncertain classifications (up to 0.2 seconds) pause hold progress; confident release, tracking loss, target change or substantial empty-ground movement clears it. During voice entry, holds are ignored until a paused retry is offered. Retry holds do not change the locked target when the cursor moves. The camera diagnostic gesture trial still reports its historical 600 ms threshold; the frontend progress ring governs the actual 2-second activation.

Troubleshooting: No speech detected means the speech detector never found a phrase; check the chosen mic and Mac input meter. Speech captured, but words were unclear means Google received audio but could not decipher it; move the microphone closer and reduce competing conversation. Google transcription unavailable indicates a service/network problem. These failures still retry at most three times before a fresh pinch hold is needed; no unconfirmed text is saved.

## Pinch confirmation and optimistic hold

At the displayed draft/review step, open your pinch to release, then hold a fresh pinch for two seconds to confirm the locked contribution. Spoken confirm/retry/cancel still work. A completed hold cancels command capture and rejects any late transcript; it never changes the selected location. Holds during plant-type or word capture remain ignored.

Hold initiation still requires score 0.70. As progress builds, the click-score requirement decreases linearly to 0.45, while tolerated uncertainty grows from 0.20 to 0.45 seconds. Returning valid click evidence bridges half of a short uncertain interval. Uncertainty alone cannot complete a hold. The model None label is uncertainty, not an open-pinch release. Explicit release, tracking loss, target change and substantial movement over empty ground still reset progress. Rule scores remain geometric margins, not calibrated probabilities. Physically test accidental selection and confirmation with exhibit lighting before relying on this tuning.
