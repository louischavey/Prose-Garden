# A garden of words

Run from this folder on Windows:

```powershell
.\.venv\Scripts\python.exe garden.py
```

On another Windows or macOS computer with Python 3.12, copy the project including
`assets`, create a virtual environment, install `requirements-garden.txt`, and run
`python garden.py` using that environment. Do not copy the Windows `.venv` to a Mac.
The original `plant_poem.py` terminal program still works separately.

For mouse input without a Metro connection, run `./Start-Poetree.ps1 -MouseOnly`
or `python garden.py --mouse-only`. This skips serial detection and location mapping,
even if serial options were also supplied. Click grass to plant and click existing
plants to water. Add `-ShowSaveButtons` to the launcher to show Save and Finish.

## Plant and water

Click anywhere on the grass, choose Flower, Tree (conifer), or Fern, enter 1–5
words, and press Enter or Water. The first words establish the plant. Click its
words or root dot to append another submission. Each submission makes a shoot
using the existing seeded, conditional L-system. Words occur exactly once in the
plant; the sidebar repeats them as a reading aid in their original order.

Plants are freely positioned inside a pale planting border. New roots must stay
10% from the left, right, and bottom edges, and 22% from the top to leave extra
room for upward growth. Existing saved plants outside this region remain selectable
and waterable. This cushion reduces edge clipping but cannot contain unlimited growth.
Black glyphs have a warm-white outline for contrast against the grass, including
in PNG exports. Playback marks the spoken word without recoloring its glyphs.

Roots also have a small exclusion cushion: 28 units
on a 1200×800 ground plane, about 21 pixels in the initial window. Branches may
overlap. Lower roots draw in front of higher ones, giving a slightly angled garden
view. Selecting a plant brings its words forward and fades its neighbors; root
dots remain reachable above the foliage. No automatic moving of roots or shrinking
plants as they grow. Very large plants may extend beyond the garden viewport.

Focus shows the selected plant on a plain background. Scroll to zoom and drag to
pan; click Focus to return. The sidebar is a scrollable entry-order reading view.
Read aloud uses the existing online Microsoft speech service with word highlighting.
Stop cancels playback and dictation.

Mic records up to eight seconds; click it again to stop recording and transcribe.
Audio goes to Google's online recognition service via SpeechRecognition. The result
is an editable draft, never automatically submitted. Correct it with the arrow keys,
Home/End, Backspace/Delete, Ctrl+A (Cmd+A on Mac), or replace it by typing. Ctrl+V /
Cmd+V pastes text where SDL clipboard support is available. Dictation requires a
working default microphone, OS microphone permission, and internet access. Failure
leaves the existing poem and draft intact. Keyboard planting works offline.

Undo removes the **last watering across the whole garden**, including removing a
new plant if that was its only submission. It does not let visitors rewrite older
words arbitrarily. Escape clears the current draft. Switching plants with an
unsubmitted draft is blocked so it cannot accidentally water the wrong plant.

Save (Ctrl+S / Cmd+S) writes JSON and a PNG of the garden, without controls or
selection fading. Finish saves and stops further watering; the window stays open.
Closing saves too. Unsubmitted drafts must be watered or explicitly cleared before
finishing or closing. Save stores accepted words, not an unfinished draft.
Save failures keep the window open.

```powershell
.\.venv\Scripts\python.exe garden.py --load output/garden-YYYYMMDD-HHMMSS-microseconds.json
```

Reopening allows watering again. By default each launch saves to a new timestamped
basename, preserving the loaded original; `--output output/my-garden` chooses a
stable basename. Saves and loads are restricted to the project folder.

Optional flags: `--connectors` for faint stems; `--seed 42` for repeatable growth
given the same planting/watering sequence; `--no-turns` for growth units independent
of submission boundaries; `--voice en-US-AriaNeural` for playback. Loaded gardens
retain their saved growth settings. The prototype caps a garden at 100 plants and
each plant at the existing 1500-word limit; large layouts can take time to reflow.

Use `python garden.py --gallery-mode` (also accepted: `--gallery_mode`) to hide the
Save and Finish buttons. This is a presentation setting, not a kiosk lock: Ctrl+S /
Cmd+S and save-on-close remain available. Omit the flag for the normal interface.

## Dirt input

The 24-probe serial demo is now implemented. See [DIRT-DEMO.md](DIRT-DEMO.md)
for the Metro sketch, one-time location mapping, and planting/watering through dirt.
Launch with `--serial-port COM5 --map-probes` for the first mapping pass.

## Tap API

`GardenApp.handle_garden_tap(x_normalized, y_normalized)` is the tap entry point,
with both coordinates from 0 through 1, measured across the grass rectangle only.
The mouse adapter converts window coordinates before calling it. It selects a
plant or previews a new location. Call on the UI thread; a future hardware worker
should enqueue coordinates for dispatch on that thread. In serial mode, the
`handle_dirt_tap(row, col)` path selects by root cell rather than word hit-testing.

`GardenApp.water_plant(plant_id, text)` appends text and refreshes the plant, separately
from tap location. `Garden` exposes equivalent model operations without a window.
Voice and keyboard feed the same editable draft and Water action. The garden is a
local, shared-computer experience; it does not synchronize multiple computers.

## Asset and verification

The supplied [Summer grass asset](https://www.summerengine.com/asset-store/grass-tile-sprite-767f957f)
is bundled as `assets/grass-summer.png`, with CC0 provenance in the adjacent license
file. The original raster is cover-scaled with nearest-neighbor sampling and a
light wash in the renderer. It is not repeated as a tile, avoiding assumed seamless
edges. This preserves the user's selected texture while softening it beneath words.

Run `python -m unittest -v`. Tests cover the existing grammar and layouts plus
garden append/undo, root spacing, failed-submission rollback, save/reopen/continued
growth, malformed history, tap selection, and a rendered window/focus preview.
Physical microphone capture, real speaker playback in this new interface, and a
native macOS run require device testing. Online dictation is an optional convenience,
not a guaranteed service.

Implementation references: [sounddevice raw streams](https://python-sounddevice.readthedocs.io/en/latest/api/raw-streams.html)
and [SpeechRecognition](https://github.com/Uberi/speech_recognition). L-system and
concrete-poetry references remain those documented in README.md.
