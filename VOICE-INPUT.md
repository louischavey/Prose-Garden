# Keyboard-free plant type, words, and confirmation

This reuses sounddevice capture and adds WebRTC VAD for speech detection. Google remains the default backend; optional whispercpp transcribes locally without cloud fallback. Both need microphone access. Google sends audio online; local mode sends audio only to localhost. Recordings stay in memory.

## Start on Mac

After syncing source changes, keep the camera/tray in place and run:

```sh
.venv/bin/python start_camera_garden.py --confirm-setup --enable-pinch --voice-input --camera 0
```

Use your working camera/profile/layout flags. Allow microphone access for Terminal/Python in macOS Privacy & Security if prompted. The microphone is local to garden.py: for Windows capture and Mac display, enable --voice-input on the Mac receiver, not camera_stream.py.

## Visitor flow (one person at a time)

1. Release/rearm, point, and pinch/thumbs-up to click a spot or snapped plant as before. Position tracking and root snapping are unchanged.
2. Watch the screen and **wait for Listening before speaking**. The microphone is not always on. A new planting asks for **flower**, **tree**, or **fern** (4-second recording). Tree maps to the existing conifer type. An existing plant skips type selection.
3. The next Listening prompt asks for **1–5 poem words** (7-second recording). It transcribes online, then shows the draft. No poem changes yet.
4. Review the displayed words/type. When Listening appears again (4-second command recording), say exactly **confirm**, **retry**, or **cancel**. Yes is accepted as confirm; try again/no means retry. Change type returns a new planting to the type question.
5. Confirm uses the existing transactional Water action and JSON checkpoint. Retry clears just the current unsubmitted draft and re-records words. Cancel discards the current draft/selection without modifying any accepted poem.
6. After saving, the microphone stops. The next visitor/entry starts with a new hand click. Further clicks during entry cannot redirect the draft. No keyboard, Mic button, or Water button is required in this flow.

Recordings now end after speech plus about 0.8 seconds of silence. The 4/7/4-second windows are maximum capture times, including the wait to begin speaking. No detected speech triggers a retry without transcription. Wait through Transcribing and the next Listening message rather than speaking during the gap. Poem words are interpreted as text only during the words phase: e.g. confirm can itself be a poem word. Commands are interpreted during separate review.

After three recognition/validation failures, recording pauses. Pinch again to retry the SAME target/phase. This keeps bad network/audio from recording indefinitely. Network or microphone failure cannot save an unconfirmed contribution. Stop pauses voice input while keeping a draft; the Mic button can restart voice review as an operator fallback. Read-aloud is blocked during active voice entry to avoid recording playback.

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

## Local speech on the M4 / 16 GB exhibit Mac

Stop Poetree, sync the Git source, and run from the project folder:

```sh
.venv/bin/python -m pip install -r requirements-garden.txt
brew install cmake
sh start_local_speech.sh
```

First run clones whisper.cpp, builds its Metal server and downloads pretrained small.en. It needs internet for setup and Apple developer tools. If tools are missing, run `xcode-select --install`, finish installation, then retry. Leave this Terminal open; subsequent runs reuse the build/model. Wait for the server to report listening on 127.0.0.1:8080.

In another Terminal, from the same folder:

```sh
.venv/bin/python start_camera_garden.py --confirm-setup --enable-pinch --voice-input --speech-backend whispercpp --camera 0
```

Keep your working camera/profile/mic-device flags. The panel says the mic stays on this Mac; recognition status says Transcribing locally. Omitting --speech-backend keeps Google. Local failure never uploads to Google. Read-aloud still uses the existing online service independently. Ctrl-C in the server Terminal stops recognition. The ignored local-speech directory must be set up separately on each Mac.

## Future hardening / acceptance

Target: M4 Mac mini, 16 GB, one warm small.en model. Benchmark base.en only if small.en is too slow. Capture is 16 kHz mono; verify the microphone supports it. WebRTC VAD detects speech, not visitor identity; gallery conversation can extend recording to the cap. Test a close mic, initial consonants, pauses, silence, accents, ambient commands, and camera responsiveness. Measure end-of-speech to displayed transcript across at least 20 planting/cultivation entries. Compare exact words and command success against Google before calling accuracy equivalent. Preserve confirmation, target locking, bounded retries and stale transcript rejection.

Tests cover early stopping, no speech, cancellation, caps, and a real loopback HTTP request containing valid WAV audio. Native Mac build, Metal inference, microphone, model quality and speed remain unverified on this Windows machine.

Server protocol: https://github.com/ggml-org/whisper.cpp/tree/master/examples/server
