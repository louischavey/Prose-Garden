# Dirt to Poetree: minimal end-to-end demo

## 1. Upload the Metro sketch

Open `arduino/poetree_24/poetree_24.ino` in Arduino IDE. Select your Metro ESP32-S3
board and port. Install/update **Adafruit MPR121** and its dependencies through
Library Manager. Keep the working USB/board settings from your previous sketch.
If you used explicit SDA/SCL GPIO numbers, copy them into the two constants.

Both MPR121s share Metro 3.3 V, GND, SDA, SCL. A is at **0x5A** (ADD grounded);
B is at **0x5C** (ADD connected to SDA, after its direct ground bridge was opened).
Do not connect either electrode array to the other array. Each electrode gets its
own copper pad. Their physical order does not matter; the mapping step discovers it.

Autoconfiguration remains enabled on both chips. Keep hands away during boot.
Serial Monitor at 115200 should show lines like:

```text
D,7500,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
```

These are `D,milliseconds,A0,...,A11,B0,...,B11`. The values are signed
baseline-minus-filtered deltas. Actual idle readings need not be zero.
`-1024` marks an unavailable channel. Missing boards retry every two seconds while
the other board continues streaming. A recovered board gets two seconds to settle;
keep hands off during recovery. Checked I2C reads, chip reset/overcurrent detection,
and per-channel out-of-range flags prevent failed readings being used as touches.
`INFO,...` and `ERR,...` lines describe problems without stopping the stream.
The window reports how many of the 24 channels are available. A hard short on the
shared SDA/SCL bus or power supply can still stop both boards; fix it physically.
This does not reliably detect every loose electrode lead. Known noisy probes can
be disabled with the sketch's DISABLED_A/B bit masks, e.g. `(1u << 10)` for E10.
Only the two configured addresses are polled, preserving board identity and your map.
**Close Serial Monitor before Python opens that port.**

## 2. Install and find the port

From the poetree folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-garden.txt
.\.venv\Scripts\python.exe -m serial.tools.list_ports
```

Use the Metro port shown by Arduino IDE or the list command, for example COM5.
On macOS use your Python environment and `/dev/cu.usbmodem...` port instead.
You can use `--serial-port auto` to choose the single attached Adafruit USB device
automatically (or the sole USB serial device if none identifies as Adafruit).
If several candidates exist, the program asks you to specify one. COM5 in these
examples is a placeholder; the Metro was detected on COM6 on this computer.
Arduino Serial Monitor/Plotter and another running garden cannot share the same
port with this app. Close them first. The garden header counts valid 24-probe frames
and reports incompatible serial text, instead of silently ignoring an old sketch.

## 3. Map locations once, then plant in the same window

```powershell
.\.venv\Scripts\python.exe garden.py --serial-port COM5 --map-probes --gallery-mode
```

The window highlights cells in a 6-column, 4-row grid, left to right, top to bottom.
Orient the tray so its long side corresponds to screen width. Touch the dirt at
the center of the highlighted cell for about half a second, then lift completely.
The next cell highlights automatically. Do not trace wires or enter electrode IDs.
If the same electrode is detected twice, the UI asks you to retry. **Undo location**
backs up one cell. After all 24, click **Use mapping**. The map is saved to
`output/probe-map.json`. An incomplete mapping does not replace an existing map.
Use **Skip location** for a disconnected or unusable pad, then continue. At least
one location must be mapped; every other location may be skipped. Skipped channels
are ignored during normal use. Remap later to add repaired probes. Existing full
maps continue working when a board drops out and recovers, without moving cells.

Now tap an empty dirt cell, choose Flower/Tree/Fern, type or dictate 1–5 words,
and press Enter/Water. Tap a different cell to start another plant. Tap the original
cell to select its plant and append more words. A dirt tap selects the location;
it does not generate words or submit them automatically. Keyboard and microphone
input keep their existing behavior. A pending draft must be submitted or cleared
with Escape before switching plants.

Cells map to centers: `x=(column+0.5)/6`, `y=(row+0.5)/4`. Dirt mode uses the full
tray, bypassing the mouse planting border. Existing roots determine cell ownership,
so foliage overlap cannot steal a dirt tap. Cell ownership survives normal garden
JSON saving/loading. Mouse clicks also select grid cells in serial mode. Start a
fresh garden for the demo; older free-placement gardens can contain several plants
in one cell, which the app reports instead of choosing arbitrarily.

Edge plants can extend out of view as they grow; Focus shows the whole selected
plant. This prototype does not reposition plants to contain their full canopy.

## 4. Subsequent launches

```powershell
.\.venv\Scripts\python.exe garden.py --serial-port COM5 --gallery-mode
```

The saved probe map loads automatically. If no map exists, mapping starts automatically.
Add `--load output/garden-YOUR-SAVED-TIMESTAMP.json` to continue an existing garden.
Use `--probe-map output/another-tray.json` to keep a separate wiring map.
`--map-probes` explicitly restarts location mapping. Normal Save/Finish and
save-on-close behavior still applies; gallery mode only hides Save and Finish buttons.

## Minimal detection, not a calibration project

There is no per-pad sensitivity calibration. Python uses one touch threshold (12)
and release threshold (6), chooses the highest delta with at least a 2-count lead,
and requires about 80 ms of a stable winner. All pads must be at or below the
release threshold for 150 ms to arm another tap. It waits for release on startup,
after mapping, and after a stream interruption. This is deliberately a simple
single-finger demo. Several fingers or broad wet-soil coupling can be ambiguous.

If needed, change the two values without reflashing, e.g.:

```powershell
.\.venv\Scripts\python.exe garden.py --serial-port COM5 --touch-threshold 20 --release-threshold 10 --gallery-mode
```

Those example values are not measured recommendations. The header shows the peak
delta and whether detection is armed. If it stays on “lift finger to rearm” with no
finger down, an idle channel may exceed the release threshold. If signals are too
weak to reach the touch threshold, adjust based on the actual streamed values.
No threshold can fix indistinguishable neighboring signals.

Serial open/disconnect errors appear in the window. Check the port, close other
programs using it, then restart garden. Opening USB serial can reset some boards;
allow the startup delay. No automatic reconnect or firmware flashing is attempted.

## Validation

`python -m unittest -q` covers frame parsing, duplicate mapping rejection, map
save/reload, tap/release behavior, stale stream handling, and simulated serial
frames through mapping -> planting -> watering -> save/reload -> undo in garden.py.
The mapping and garden window previews are saved in `test-output`.
The Arduino sketch has not been compiled or uploaded here; physical hardware,
soil reliability, and native macOS serial behavior still need your device test.

References: [Adafruit MPR121 API](https://github.com/adafruit/Adafruit_MPR121),
[pySerial API](https://pyserial.readthedocs.io/en/latest/pyserial_api.html).
