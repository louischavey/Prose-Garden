# Voice exhibit startup and first hardening pass

From the project folder on Mac, after syncing source and updating dependencies:

```sh
.venv/bin/python -m pip install -r requirements-garden.txt
.venv/bin/python run_exhibit.py --camera 0
```

Voice input, experimental pinch, saved calibration and bounded crash retries are enabled automatically. Keep existing camera/profile/layout/mic flags, for example `--mic-device 2 --profile camera-profile.json`. Calibrate separately before starting; confirm the camera, tray and framing have not moved. Google transcription still needs internet. No local speech server is needed.

Every manual launch and crash recovery resumes `output/exhibit.json`, including root positions and accepted words. Use --fresh only to explicitly archive the current primary/backup and start a new empty garden. --resume remains a compatibility alias for the default. To import your current accepted poems on the FIRST run:

```sh
.venv/bin/python run_exhibit.py --camera 0 --load output/YOUR-EXISTING-GARDEN.json
```

An existing checkpoint always takes precedence over --load. To explicitly replace the running collection with an imported file, use --fresh --load together. Your import file is read only. For a separate new exhibit session choose `--output output/exhibit-session-2`; existing poems are not deleted. Check the displayed plants before opening the exhibit to visitors.

| Failure | Current behavior |
| --- | --- |
| Camera process exits with an error | Sender restarts up to three times with 2/4/8-second waits; garden and its current draft remain open. Reconnection requires gesture release/rearm. |
| Camera keeps failing | Retries stop; garden remains open with stream-stopped status for operator recovery. Close normally, fix camera, rerun. |
| Garden/launcher exits with an error | Supervisor cleans up its process group and retries up to three times, reloading accepted JSON. Unconfirmed draft is discarded. |
| Normal garden close | Saves and exits, without reopening. |
| Duplicate supervisor launch | OS-held lock rejects it; lock releases when supervisor exits. A leftover lock file is harmless. Stop separately launched legacy instances yourself. |
| Invalid checkpoint | A valid .backup.json is restored automatically, preserving the corrupt primary for inspection. If neither copy validates, startup stops rather than creating an empty replacement. |
| Silence, unclear transcription or network failure | Existing bounded voice retries and locked target remain; no unconfirmed words are submitted. |
| Camera/tray physically moves | Operator must recalibrate. Automatic restart cannot verify alignment. |

Logs are printed to the launching Terminal as file paths under `output/logs/`. Each process attempt has its own log. Close the garden window normally to save/export and stop. Ctrl-C in the supervisor forcibly stops the process group; only previously checkpointed words are recoverable. Never use that for submitting a draft.

The original grass file is unchanged; display scaling now uses smooth interpolation and is cached rather than recomputed every frame. This softens resized pixels; it cannot add detail absent from the original artwork.

## Acceptance and remaining work

Tests simulate crash budgets, recovery, corrupt saves, duplicate locks, and camera-only restart. Native Mac camera reconnect, microphone permissions, disconnect/reconnect, network outage and visitor interaction still need physical tests. This first pass detects process exits, not a frozen process or silent webcam stall; heartbeat/watchdog monitoring, disk-full recovery UI, automatic backup rotation and power-loss durability are future work. Checkpoint writes flush file data, atomically replace JSON and flush the containing directory on macOS; a previous checkpoint is retained. Disk-write failure, storage failure and words still being captured cannot be guaranteed recoverable. Do not claim unattended reliability yet.

Long thoughts and growth/compression parameters: see TUNING.md. Remote snapshot: `.venv/bin/python sync_garden.py --publish` exports JSON plus readable visitor-data/README.md, commits only those snapshot files and pushes the current branch. Export without Git using the same command without --publish. Nothing publishes in the exhibit loop. A failed sync never deletes the local checkpoint.

Startup Git sync is enabled automatically once per manual launch, in the background; logs appear under output/logs/sync-*.log. No periodic publishing is enabled. Failed Git/network/auth operations do not stop the exhibit or alter accepted local saves. --no-sync skips the startup publisher.

## Mouse fallback with voice

Stop the camera exhibit first, then run:

```sh
python run_exhibit.py --mouse-only --mic-device 1
```

Use the actual microphone index. No camera is opened and no hand stream is required. Click empty ground to choose a planting location or click a root/plant to cultivate. The same guided type/thoughts transcription and automatic submission run, with persistence, checkpoint backups and startup Git sync unchanged. A click during capture cannot change the locked target; after voice pauses, clicking retries that target. The garden stays in overview so subsequent clicks remain usable. Microphone permission and online transcription still apply.

### Exhibit defaults

Run `python run_exhibit.py` for camera 0, microphone 1, hold 0.75 seconds, word compression 0.35, thought capture up to 15 seconds and growth every 2 words. Voice, pinch, persistence, recovery and startup Git sync are enabled. `python run_exhibit.py --mouse-only` uses the same voice/render settings without camera capture. All flags can still override these defaults.
