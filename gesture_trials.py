"""Gesture-only measurements; no calibration, coordinates, or action mutations."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path

POSES = ("Closed_Fist", "Open_Palm", "Victory", "Pointing_Up", "Thumb_Up")


class GestureTrials:
    def __init__(self, report_path, setup=None):
        self.path = Path(report_path)
        self.setup = setup or {}
        self.target = None
        self.results = []
        self.last_result = None

    def start(self, index, now):
        self.target = POSES[index]
        self.starts = now + 3.
        self.ends = self.starts + 5.
        self.samples = self.hits = 0
        self.labels = Counter()
        self.hold_start = self.previous = None
        self.longest = 0.

    def update(self, observation, now):
        if self.target is None or now < self.starts:
            return None
        if now >= self.ends:
            result = dict(pose=self.target, samples=self.samples, matching_samples=self.hits,
                          match_percent=round(100*self.hits/self.samples, 1) if self.samples else 0.,
                          longest_hold_seconds=round(self.longest, 2),
                          met_600ms_hold=self.longest >= .6, observed_labels=dict(self.labels))
            self.results.append(result)
            self.last_result = result
            self.target = None
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(dict(setup=self.setup, trials=self.results), indent=2), encoding="utf-8")
            print("Gesture trial: " + json.dumps(result), flush=True)
            return result
        self.samples += 1
        label = observation.get("raw_pose", "None")
        self.labels[label if observation["state"] == "ok" else observation["state"]] += 1
        hit = observation["state"] == "ok" and label == self.target and observation["score"] >= .7
        if hit:
            self.hits += 1
            if self.hold_start is None or (self.previous is not None and now-self.previous > .5):
                self.hold_start = now
            self.longest = max(self.longest, now-self.hold_start)
        else:
            self.hold_start = None
        self.previous = now
        return None

    def status(self, now):
        if self.target:
            if now < self.starts:
                return f"Get ready: {self.target} in {max(1, int(self.starts-now)+1)}s"
            return f"HOLD {self.target}: {max(0, self.ends-now):.1f}s remaining (keep palm inside plot)"
        if self.last_result:
            result = self.last_result
            return f"{result['pose']}: {result['match_percent']:.0f}% matched; longest hold {result['longest_hold_seconds']:.2f}s"
        return "Press 1-5 to begin a timed gesture trial"


def default_report(root):
    return Path(root)/"output"/f"gesture-trials-{datetime.now():%Y%m%d-%H%M%S-%f}.json"
