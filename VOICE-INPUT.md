# Voice input: automatic planting and cultivation

Current visitor flow has no confirmation step, Undo button, Read aloud button or Stop button.

## Start on Mac

From the project folder, after syncing source:

```sh
.venv/bin/python -m pip install -r requirements-garden.txt
.venv/bin/python run_exhibit.py --camera 0
```

Keep your working camera/profile/layout/mic flags. See EXHIBIT-RUN.md before importing existing poems into the stable exhibit save. Standard launcher alternative:

```sh
.venv/bin/python start_camera_garden.py --confirm-setup --enable-pinch --voice-input --camera 0
```

## Visitor flow

1. Open pinch to rearm, point at empty ground or a nearby snapped root, then hold pinch for two seconds. The cursor fills teal.
2. A new spot asks for flower, tree, or fern. Existing plants skip type selection.
3. Wait for LISTENING and share your thoughts. Valid transcription automatically plants or cultivates the locked target and checkpoints it. No spoken or gesture confirmation is needed.
4. The selected plant remains highlighted. Rearm and select another spot/plant for the next entry. Holds during type/word capture cannot redirect the contribution.

All transcribed words in the thoughts phase are literal text, including confirm, retry and cancel. Cancel remains recognized during plant-type selection. There is no review/retry command phase after successful transcription.

## Capture and failures

WebRTC VAD mode 1 gives up to eight seconds to begin speaking, then a maximum four seconds for type or 15 seconds for thoughts by default (--words-seconds can tune 1..60 seconds). Recording ends after approximately 1.4 seconds of silence. Google transcribes online; audio stays in memory and is sent to Google, without recording files. Mic and internet permissions are required on the display computer. Local transcription is deferred.

No speech, invalid type, invalid word count, unclear words or network errors retry at most three times, then pause. Hold pinch two seconds to retry the SAME target/phase, without leaving the tray. All valid transcribed words are retained (up to the existing 1500-word total per plant). Only valid current transcripts are submitted; stale/duplicate results cannot create another contribution. An incorrectly recognized but valid phrase now saves immediately by design.

No speech detected: check selected microphone, input volume and distance. Speech captured but words unclear: move the mic closer and reduce competing voices. Google unavailable: check network/service. Logs are under output/logs when using run_exhibit.py.

## Microphone selection

```sh
.venv/bin/python -c "import sounddevice as sd; print(sd.query_devices())"
```

Add --mic-device 2 using the actual INPUT index, or use a distinctive mic name. Default is the system input. Allow Terminal/Python microphone access in macOS Privacy & Security. Speech language defaults to en-US.

## Position and hold behavior

Working position calibration and root snapping are unchanged. A hold starts at score .70 and gradually accepts .45; uncertainty tolerance grows from .20 to .45 seconds. Returning valid click evidence bridges half a short uncertain interval. Unknown alone never completes a hold. Explicit release, tracking loss, target change and substantial empty-ground movement reset it. Rule scores are geometric margins, not calibrated probabilities.

## Hardening and verification

Exhibit hardware is M4 Mac mini, 16 GB. Future hardening may revisit local transcription after live accuracy/latency comparisons. Keep target locking, bounded retries, validated automatic submission, atomic checkpoint recovery and stale-result rejection. Test pauses, noise, accents, network loss and accidental automatic planting on the real Mac. Synthetic tests cover automatic planting/cultivation, checkpoint recovery, failures/retry, late/duplicate rejection, VAD bounds and removed visitor controls. Native Mac hardware remains separately unverified.

Restart persistence, compression and faster growth settings are documented in TUNING.md. The former five-word truncation is removed.

## Mouse fallback with voice

Stop the camera exhibit first, then run:

```sh
python run_exhibit.py --mouse-only --mic-device 1
```

Use the actual microphone index. No camera is opened and no hand stream is required. Click empty ground to choose a planting location or click a root/plant to cultivate. The same guided type/thoughts transcription and automatic submission run, with persistence, checkpoint backups and startup Git sync unchanged. A click during capture cannot change the locked target; after voice pauses, clicking retries that target. The garden stays in overview so subsequent clicks remain usable. Microphone permission and online transcription still apply.
