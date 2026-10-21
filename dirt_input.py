"""Serial transport, fixed-threshold taps, and a one-time 24-cell wiring map."""
import json
import queue
import threading
import time
from plant_poem import inside

ROWS, COLS = 4, 6
UNAVAILABLE = -1024


def resolve_port(requested, ports):
    ports = list(ports)
    names = [p.device for p in ports]
    if requested != "auto":
        if requested.casefold() not in [name.casefold() for name in names]:
            raise ValueError(f"{requested} not found. Available: {', '.join(names) or 'none'}. Use --serial-port auto.")
        return next(name for name in names if name.casefold() == requested.casefold())
    candidates = [p for p in ports if p.vid == 0x239A]  # Adafruit USB vendor.
    if not candidates:
        candidates = [p for p in ports if p.vid is not None]
    if len(candidates) != 1:
        raise ValueError(f"Choose --serial-port explicitly. USB ports: {', '.join(p.device for p in candidates) or 'none detected'}")
    return candidates[0].device


def parse_frame(line):
    parts = line.strip().split(",")
    if len(parts) != 26 or parts[0] != "D":
        return None
    try:
        values = [int(value) for value in parts[1:]]
    except ValueError:
        return None
    if not 0 <= values[0] <= 0xFFFFFFFF or any(not UNAVAILABLE <= v <= 1023 for v in values[1:]):
        return None
    return values[0], values[1:]


def electrode_name(index):
    if index is None:
        return "skipped"
    return f"{'A' if index < 12 else 'B'}{index % 12}"


class TapDetector:
    def __init__(self, threshold=12, release=6):
        if not 0 <= release < threshold <= 1023:
            raise ValueError("Use 0 <= release threshold < touch threshold <= 1023.")
        self.threshold, self.release = threshold, release
        self.reset()

    def reset(self):
        self.armed = False
        self.quiet_since = None
        self.candidate = None
        self.since = None
        self.last_time = None
        self.available = None

    def update(self, delta, now):
        if self.last_time is not None and now-self.last_time > .5:
            self.reset()
        self.last_time = now
        available = tuple(v != UNAVAILABLE for v in delta)
        if not any(available):
            self.reset()
            return None
        if self.available != available:
            self.armed = False
            self.quiet_since = None
            self.candidate = None
            self.available = available
        peak = max(delta)
        if peak <= self.release:
            self.candidate = None
            if self.quiet_since is None:
                self.quiet_since = now
            if now-self.quiet_since >= .15:
                self.armed = True
            return None
        self.quiet_since = None
        if not self.armed:
            return None
        winner = max(range(24), key=lambda i: delta[i])
        second = sorted(delta)[-2]
        # A tie is not enough evidence to assign a physical location.
        if peak < self.threshold or peak-second < 2:
            self.candidate = None
            return None
        if winner != self.candidate:
            self.candidate, self.since = winner, now
        elif now-self.since >= .08:
            self.armed = False
            self.candidate = None
            return winner
        return None


class ProbeMap:
    def __init__(self, path, remap=False):
        self.path = inside(path)
        self.cells = []  # Row-major cells -> stream electrode ID (A0=0, B0=12).
        self.mapping = remap or not self.path.exists()
        if not self.mapping:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            cells = data.get("cells") if isinstance(data, dict) else None
            if (not isinstance(data, dict) or data.get("format") != "poetree-probes"
                    or data.get("version") not in (1, 2) or data.get("rows") != ROWS or data.get("cols") != COLS
                    or not isinstance(cells, list) or len(cells) != 24
                    or not self.valid_cells(cells)):
                raise ValueError("Invalid probe map. Use --map-probes to redo location mapping.")
            self.cells = cells

    def record(self, electrode):
        if not self.mapping or len(self.cells) >= 24:
            return
        if electrode in self.cells:
            raise ValueError(f"{electrode_name(electrode)} was already mapped. Lift and retry, or Undo location.")
        self.cells.append(electrode)

    @staticmethod
    def valid_cells(cells):
        live = [v for v in cells if v is not None]
        return bool(live) and all(type(v) is int and 0 <= v < 24 for v in live) and len(set(live)) == len(live)

    def skip(self):
        if self.mapping and len(self.cells) < 24:
            self.cells.append(None)

    def save(self):
        if len(self.cells) != 24 or not self.valid_cells(self.cells):
            raise ValueError("Map at least one probe and map or skip every remaining location.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = inside(self.path.with_suffix(".pending.json"))
        temp.write_text(json.dumps({"format": "poetree-probes", "version": 2,
                                    "rows": ROWS, "cols": COLS, "cells": self.cells}, indent=2), encoding="utf-8")
        temp.replace(self.path)
        self.mapping = False

    def cell(self, electrode):
        if electrode not in self.cells:
            return None
        return divmod(self.cells.index(electrode), COLS)


class SerialInput:
    def __init__(self, port):
        self.port = port
        self.frames = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.message = f"Opening {port}..."
        self.last_frame = None
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        try:
            import serial
            from serial.tools import list_ports
            self.port = resolve_port(self.port, list_ports.comports())
            with serial.Serial(self.port, 115200, timeout=.2) as connection:
                connection.reset_input_buffer()
                self.message = f"{self.port} open; waiting for readings. Keep hands off."
                buffer = b""
                opened = time.monotonic()
                valid_count = 0
                unknown_count = 0
                while not self.stop.is_set():
                    chunk = connection.read(max(1, min(connection.in_waiting, 4096)))
                    buffer += chunk
                    while b"\n" in buffer:
                        raw, buffer = buffer.split(b"\n", 1)
                        line = raw.decode("ascii", errors="replace").strip()
                        frame = parse_frame(line)
                        if frame:
                            valid_count += 1
                            unknown_count = 0
                            stamp = time.monotonic()
                            self.last_frame = stamp
                            available = sum(v != UNAVAILABLE for v in frame[1])
                            self.message = f"{self.port}: {available}/24 probes available ({valid_count} frames)"
                            try:
                                self.frames.get_nowait()
                            except queue.Empty:
                                pass
                            self.frames.put_nowait((stamp, frame))
                        elif line.startswith(("ERR,", "INFO,")):
                            self.message = line.split(",", 1)[1]
                        elif line:
                            unknown_count += 1
                            if unknown_count >= 3:
                                self.message = "Serial data received, wrong format. Upload poetree_24.ino (D,time,24 deltas)."
                    if len(buffer) > 4096:
                        buffer = b""
                    if self.last_frame is None and unknown_count == 0 and time.monotonic()-opened > 12 and not chunk:
                        self.message = f"{self.port} open but no valid probe frames. Check sketch/USB Serial settings."
        except Exception as exc:
            self.message = f"Serial unavailable: {exc}. Close Serial Monitor; check port; restart garden."

    def close(self):
        self.stop.set()
        self.thread.join(timeout=1)
