"""Platform-independent, versioned UDP hand observations and intent gate."""
import json
import math
import socket
import time

VERSION = 1
GESTURES = {"closed_fist", "open_palm", "unknown", "click"}
STATES = {"ok", "no_hand", "ambiguous", "outside", "uncalibrated"}


def validate(data):
    if not isinstance(data, dict) or data.get("version") != VERSION:
        raise ValueError("Unsupported hand protocol")
    for key in ("session", "calibration"):
        if not isinstance(data.get(key), str) or not 1 <= len(data[key]) <= 128:
            raise ValueError("Missing stream identity")
    if type(data.get("seq")) is not int or data["seq"] < 0:
        raise ValueError("Invalid sequence")
    for key in ("sent_at", "score"):
        value = data.get(key)
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Invalid numeric field")
    if not 0 <= data["score"] <= 1:
        raise ValueError("Invalid score")
    if data.get("state") not in STATES or data.get("gesture") not in GESTURES:
        raise ValueError("Invalid observation state")
    if data["state"] == "ok":
        for key in ("x", "y"):
            value = data.get(key)
            if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("Coordinates must be normalized garden coordinates")
    elif data.get("x") is not None or data.get("y") is not None:
        raise ValueError("Invalid tracking state must clear coordinates")
    return data


class HandReceiver:
    def __init__(self, host="127.0.0.1", port=8765):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.socket.bind((host, port))
        except Exception:
            self.socket.close()
            raise
        self.socket.setblocking(False)
        self.last_received = None
        self.identity = None
        self.seq = -1
        self.message = "Waiting for hand stream"
        self.batch = []

    def poll(self):
        latest = None
        self.batch = []
        # Drain a bounded batch. Packet timestamps also reject queued/stale input.
        for _ in range(256):
            try:
                raw, _ = self.socket.recvfrom(4096)
            except BlockingIOError:
                break
            try:
                data = validate(json.loads(raw))
                if abs(time.time() - data["sent_at"]) > .5:
                    self.message = "Stale hand data / clocks differ; commands stopped"
                    continue
                identity = (data["session"], data["calibration"])
                # A new sender can take over only after the current sender stops.
                if self.identity is not None and identity != self.identity and self.last_received is not None:
                    if time.monotonic() - self.last_received < 1:
                        continue
                if identity == self.identity and data["seq"] <= self.seq:
                    continue
                self.identity, self.seq = identity, data["seq"]
                self.last_received = time.monotonic()
                latest = data
                self.batch.append((self.last_received, data))
                self.message = "Hand stream: " + data["state"]
                if data["state"] == "ok":
                    # Only display known model labels from an optional newer sender.
                    raw_pose = data.get("raw_pose")
                    if raw_pose not in ("Closed_Fist", "Open_Palm", "Victory", "Pointing_Up", "Thumb_Up", "Thumb_Down", "ILoveYou", "Pinch", "None"):
                        raw_pose = data["gesture"]
                    pose = "pose unclear" if data["score"] < .7 else raw_pose
                    self.message = f"Position OK | {pose} {data['score']:.2f}"
                    if data.get("click_source") == "pinch_rule":
                        self.message += " (pinch rule)"
                elif data.get("reason") == "palm_outside":
                    self.message = "Hand outside mapped tray - check palm-center ring in camera"
                elif data.get("reason") == "multiple_hands":
                    self.message = "Two hands visible - use one hand"
                elif data.get("reason") == "processing_slow":
                    self.message = "Camera processing slow - commands paused"
            except (ValueError, TypeError, UnicodeError):
                self.message = "Invalid hand packet ignored"
        return latest

    def close(self):
        self.socket.close()


class IntentGate:
    """Requires release on startup/reconnect; a pose change never releases a latch."""
    def __init__(self, rows=2, cols=3, hold=.6, release=.3, score=.7, margin=.025):
        if rows * cols not in (4, 5, 6) or rows < 1 or cols < 1:
            raise ValueError("Choose a rectangular layout with 4, 5, or 6 sections")
        self.rows, self.cols = rows, cols
        self.hold, self.release, self.score, self.margin = hold, release, score, margin
        self.identity = None
        self.latched = True
        self.candidate = None
        self.since = None
        self.release_since = None
        self.last_time = None

    def interrupt(self):
        self.candidate = self.since = self.release_since = None
        self.latched = True

    def cell(self, x, y):
        # Do not clamp an outside hand into a plot. Suppress shared boundaries.
        if not 0 <= x <= 1 or not 0 <= y <= 1:
            return None
        if any(abs(x - i/self.cols) < self.margin for i in range(1, self.cols)):
            return None
        if any(abs(y - i/self.rows) < self.margin for i in range(1, self.rows)):
            return None
        return min(self.rows-1, int(y*self.rows)), min(self.cols-1, int(x*self.cols))

    def update(self, data, now=None):
        now = time.monotonic() if now is None else now
        identity = (data["session"], data["calibration"])
        if identity != self.identity or (self.last_time is not None and now-self.last_time > .5):
            self.interrupt()
            self.identity = identity
        self.last_time = now
        # Only a confidently visible neutral hand or explicit outside state rearms.
        neutral = data["state"] == "outside" or (data["state"] == "ok" and data["gesture"] == "unknown" and data["score"] >= self.score)
        if neutral:
            self.candidate = self.since = None
            if self.release_since is None:
                self.release_since = now
            if now-self.release_since >= self.release:
                self.latched = False
            return None
        self.release_since = None
        if self.latched or data["state"] != "ok" or data["score"] < self.score:
            self.candidate = self.since = None
            return None
        cell = self.cell(data["x"], data["y"])
        if cell is None or data["gesture"] not in ("closed_fist", "open_palm"):
            self.candidate = self.since = None
            return None
        candidate = (data["gesture"], *cell)
        if candidate != self.candidate:
            self.candidate, self.since = candidate, now
        if now-self.since >= self.hold:
            self.latched = True
            self.candidate = self.since = None
            return candidate
        return None


class ClickGate(IntentGate):
    """One model gesture clicks either a stable nearby root or empty ground."""
    def update(self, data, now=None, target_id=None):
        now = time.monotonic() if now is None else now
        identity = (data["session"], data["calibration"])
        if identity != self.identity or (self.last_time is not None and now-self.last_time > .5):
            self.interrupt()
            self.identity = identity
        self.last_time = now
        neutral = data["state"] == "outside" or (data["state"] == "ok" and data["gesture"] == "unknown" and data["score"] >= self.score)
        if neutral:
            self.candidate = self.since = None
            if self.release_since is None:
                self.release_since = now
            if now-self.release_since >= self.release:
                self.latched = False
            return None
        self.release_since = None
        if self.latched or data["state"] != "ok" or data["gesture"] != "click" or data["score"] < self.score:
            self.candidate = self.since = None
            return None
        point = (data["x"], data["y"])
        changed = self.candidate is None or self.candidate[0] != target_id
        if not changed and target_id is None:
            changed = math.hypot((point[0]-self.candidate[1][0])*1200,
                                 (point[1]-self.candidate[1][1])*800) > 48
        if changed:
            self.candidate, self.since = (target_id, point), now
        if now-self.since >= self.hold:
            self.latched = True
            self.candidate = self.since = None
            return dict(x=point[0], y=point[1], target_id=target_id)
        return None
