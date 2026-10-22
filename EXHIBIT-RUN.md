# Voice exhibit startup and first hardening pass

From the project folder on Mac, after syncing source and updating dependencies:

```sh
.venv/bin/python -m pip install -r requirements-garden.txt
.venv/bin/python run_exhibit.py --camera 0
```

Voice input, experimental pinch, saved calibration and bounded crash retries are enabled automatically. Keep existing camera/profile/layout/mic flags, for example `--mic-device 2 --profile camera-profile.json`. Calibrate separately before starting; confirm the camera, tray and framing have not moved. Google transcription still needs internet. No local speech server is needed.

Each manual launch starts an empty garden. Previous accepted thoughts are archived under `output/previous-sessions/`. Automatic crash retries still recover the current run from `output/exhibit.json`. Add `--resume` to intentionally continue the previous garden. To import your current accepted poems on the FIRST run:

```sh
.venv/bin/python run_exhibit.py --camera 0 --load output/YOUR-EXISTING-GARDEN.json
```

With --resume, an existing exhibit checkpoint takes precedence over --load. Without --resume it is archived first. Your import file is read only. For a separate new exhibit session choose `--output output/exhibit-session-2`; existing poems are not deleted. Check the displayed plants before opening the exhibit to visitors.

| Failure | Current behavior |
| --- | --- |
| Camera process exits with an error | Sender restarts up to three times with 2/4/8-second waits; garden and its current draft remain open. Reconnection requires gesture release/rearm. |
| Camera keeps failing | Retries stop; garden remains open with stream-stopped status for operator recovery. Close normally, fix camera, rerun. |
| Garden/launcher exits with an error | Supervisor cleans up its process group and retries up to three times, reloading accepted JSON. Unconfirmed draft is discarded. |
| Normal garden close | Saves and exits, without reopening. |
| Duplicate supervisor launch | OS-held lock rejects it; lock releases when supervisor exits. A leftover lock file is harmless. Stop separately launched legacy instances yourself. |
| Invalid checkpoint | Startup stops with an error; no empty replacement is written. Preserve the file and recover a known-good save manually. |
| Silence, unclear transcription or network failure | Existing bounded voice retries and locked target remain; no unconfirmed words are submitted. |
| Camera/tray physically moves | Operator must recalibrate. Automatic restart cannot verify alignment. |

Logs are printed to the launching Terminal as file paths under `output/logs/`. Each process attempt has its own log. Close the garden window normally to save/export and stop. Ctrl-C in the supervisor forcibly stops the process group; only previously checkpointed words are recoverable. Never use that for submitting a draft.

The original grass file is unchanged; display scaling now uses smooth interpolation and is cached rather than recomputed every frame. This softens resized pixels; it cannot add detail absent from the original artwork.

## Acceptance and remaining work

Tests simulate crash budgets, recovery, corrupt saves, duplicate locks, and camera-only restart. Native Mac camera reconnect, microphone permissions, disconnect/reconnect, network outage and visitor interaction still need physical tests. This first pass detects process exits, not a frozen process or silent webcam stall; heartbeat/watchdog monitoring, disk-full recovery UI, automatic backup rotation and power-loss durability are future work. Existing checkpoint writes use atomic replacement, but a contribution during a disk-write failure is not guaranteed recovered after a crash. Do not claim unattended reliability yet.
