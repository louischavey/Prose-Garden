# Persistent garden, longer thoughts and faster plant forms

On the exhibit Mac, from ~/prose_garden:

```sh
source .venv/bin/activate
python run_exhibit.py --camera 0 --mic-device 1 --word-compression 0.35 --growth-words 2 --words-seconds 15
```

Use the actual microphone index. The same flags work on start_camera_garden.py and garden.py.

| Parameter | Default | Effect |
| --- | --- | --- |
| --word-compression | 0.35 | 0 disables compression; values up to 1 shrink long plants more. Try 0.2 for larger/more readable plants or 0.6 for tighter forms. Applies immediately to all displayed plants, without moving roots or altering stored words/layouts. |
| --growth-words | 2 for new gardens | Words per grammar growth step within each contribution. 1 makes branching/petals develop fastest, 2 is the starting balance, 4 develops slower; 0 restores one growth step per entire contribution. Applies to NEW plants; each plant saves its own growth setting. Existing saved plants retain their original form and growth setting. |
| --words-seconds | 15 | Maximum speech time after speech starts (1..60). Speech still ends after about 1.4 seconds of silence, with up to 8 seconds to start. |
| --fresh | off | Explicitly archive the existing primary and backup and start empty. Normal restarts resume. |

Compression multiplies both word positions relative to the root and text size by max(0.2, max(1, word_count/5) ** -compression). It reduces footprint without changing the normalized root. It does not guarantee that neighboring plants never overlap. Readability naturally decreases at large word counts; tune on the exhibit display. Growth changes are discrete grammar steps per phrase, not a playback animation speed.

All phrase words now remain intact. The existing 1500-word total per plant and per-word validation remain to bound geometry and memory. Each visitor contribution remains one submission/history entry even when it drives several growth steps, so cultivation, save/reload and operator undo remain coherent. Older save files without growth metadata load with their original behavior and layout. New default growth is faster but does not rewrite existing poems.

## Persistence

The exhibit resumes output/exhibit.json after manual close/restart, process crash or reboot. Each accepted contribution is flushed into an atomic JSON checkpoint; output/exhibit.backup.json keeps the preceding checkpoint. On corruption, startup restores a valid backup and preserves the corrupt file. Accepted words, root coordinates, seeds and exact layouts round-trip. In-flight speech and contributions whose disk writes failed are not guaranteed recoverable; hardware/storage failure cannot be made impossible by this code.

The display computer is the live source of truth. Git snapshots are for viewing/history, not a file to merge into the running exhibit. Do not overwrite the live output file with an older remote snapshot.

## Remote viewing through Git

On the Mac, while the exhibit runs or after stopping it:

```sh
python sync_garden.py
```

This durably exports visitor-data/latest.json and visitor-data/README.md from the accepted checkpoint. It does not commit or push. To publish:

```sh
python sync_garden.py --publish
```

This commits only those two snapshot files, then pushes the current branch to origin. Git authentication and permission on the Mac must already work. A rejected push leaves the checkpoint and local snapshot intact; resolve branch divergence outside the exhibit and rerun. Existing unrelated unpushed commits on that branch will also be included by Git push; no pull, merge, reset or force push is performed. No credentials are stored by the script.

Open visitor-data/README.md on that branch in GitHub to read thoughts grouped by plant and root location; latest.json has complete saved layouts. Repeated exports with no changes do not rewrite the snapshot. Publishing retries a previous failed push even when the checkpoint did not change. Custom save basenames use --source output/YOUR-SAVE.json.

Minimal future automation would run that publish command once a minute, committing only changed content and retrying sync later when offline. Startup publishing is now enabled once per run_exhibit.py launch; no repeating scheduler is enabled.

## Validation boundary

Tests exercise retained long phrases, growth grouping and old-save compatibility, all three plant shapes, compression with fixed roots, interrupted JSON replacement, corrupt-primary backup recovery, persistent startup, snapshot export, and the scoped Git command sequence. Rendered views were inspected. Actual abrupt power loss, native Mac latency, long noisy speech and Git authentication/push are separate exhibit-machine checks.

### Automatic startup sync

run_exhibit.py now exports, commits and pushes the accepted garden once at startup, in a background process. It does not block the garden window. Results and errors are in output/logs/sync-*.log. Git credentials must already work on the Mac: startup sync cannot prompt for login. Each Git command has a 30-second timeout; offline/auth/branch errors leave local checkpoint data intact and retry on the next launch, or manually with sync_garden.py --publish. A separate sync lock prevents overlapping publishers. Use --no-sync to skip publishing for a launch. This publishes the startup snapshot, not contributions made later during the same run.

## Flower balance

Flowers now allocate continued growth to their stem and both leaves, in addition to petals. After establishing the initial stem/leaf, each five growth steps allocate one to the stem, one to leaves and three to petals. There is still one flower head with six petal rays; stem growth advances that existing head rather than spawning new flowers. The head-driven stem spacing multiplier is bounded to 1..2 instead of expanding without a ceiling. Collision avoidance still independently adds local spacing where required. Tree/fern grammar and global compression/position mapping are unchanged.

The session saves a flower_balance boolean. Old sessions lacking it still validate under their original rules. At garden-window startup, old flowers are transactionally rebuilt in memory using their original seeds, words, submission boundaries and growth setting; IDs, roots and history remain unchanged. The balanced layout is persisted by the normal next checkpoint/save, which retains the previous save as backup. Reading/exporting a JSON alone does not reflow it. No live saved poems are rewritten by the source-code update itself.
