"""Gesture-only measurements; no calibration, coordinates, or action mutations."""
from collections import Counter
from datetime import datetime
import json
from pathlib import Path

POSES = ("Closed_Fist", "Open_Palm", "Victory", "Pointing_Up", "Thumb_Up")


def pose_configuration(source, plant=None, cultivate=None):
    if source != "model":
        raise ValueError("Use the bundled model; custom landmark gestures have been retired")
    choices = POSES
    plant = plant or choices[0]
    cultivate = cultivate or choices[1]
    if plant not in choices or cultivate not in choices or plant == cultivate:
        raise ValueError(f"Choose different {source} poses from: {', '.join(choices)}")
    return choices, plant, cultivate


class GestureTrials:
    def __init__(self, report_path, setup=None, poses=POSES):
        self.path = Path(report_path)
        self.setup = setup or {}
        self.target = None
        self.results = []
        self.last_result = None
        self.poses = poses

    def start(self, index, now):
        self.target = self.poses[index]
        self.starts = now + 3.
        self.ends = self.starts + 5.
        self.samples = self.hits = 0
        self.labels = Counter()
        self.raw_labels = Counter()
        self.states = Counter()
        self.reasons = Counter()
        self.raw_matches = self.pose_hits = self.position_hits = 0
        self.max_target_score = 0.
        self.hold_start = self.previous = None
        self.longest = 0.

    def update(self, observation, now):
        if self.target is None or now < self.starts:
            return None
        if now >= self.ends:
            if not self.samples:
                diagnosis = "No sampled frames. Repeat the trial and wait for its countdown/hold to finish."
            elif not self.raw_matches:
                diagnosis = "Detector never named the requested pose. Check raw_label_counts and state_counts."
            elif not self.pose_hits:
                diagnosis = "Requested label appeared, but its score never reached 0.70."
            elif not self.hits:
                diagnosis = "Pose recognized at >=0.70, but position/processing gates rejected every match."
            elif self.longest < .6:
                diagnosis = "Some valid matches, but recognition did not stay continuous for 0.60 seconds."
            else:
                diagnosis = "At least one usable hold detected. Repeat across plots and ordinary movements."
            result = dict(pose=self.target, samples=self.samples, matching_samples=self.hits,
                          match_percent=round(100*self.hits/self.samples, 1) if self.samples else 0.,
                          longest_hold_seconds=round(self.longest, 2),
                          met_600ms_hold=self.longest >= .6, observed_labels=dict(self.labels),
                          raw_label_counts=dict(self.raw_labels), state_counts=dict(self.states),
                          reason_counts=dict(self.reasons),
                          position_ok_percent=round(100*self.position_hits/self.samples, 1) if self.samples else 0.,
                          requested_label_percent=round(100*self.raw_matches/self.samples, 1) if self.samples else 0.,
                          requested_pose_at_threshold_any_position_percent=round(100*self.pose_hits/self.samples, 1) if self.samples else 0.,
                          max_score_when_requested_label_is_top=round(self.max_target_score, 3), diagnosis=diagnosis)
            self.results.append(result)
            self.last_result = result
            self.target = None
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(dict(setup=self.setup, trials=self.results), indent=2), encoding="utf-8")
            print("Gesture trial: " + json.dumps(result), flush=True)
            return result
        self.samples += 1
        label = observation.get("raw_pose", "None")
        self.raw_labels[label] += 1
        self.states[observation["state"]] += 1
        self.reasons[observation.get("reason", "unspecified")] += 1
        self.position_hits += observation["state"] == "ok"
        if label == self.target:
            self.raw_matches += 1
            self.max_target_score = max(self.max_target_score, observation["score"])
            if observation["score"] >= .7:
                self.pose_hits += 1
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
            return (f"{result['pose']}: label {result['requested_label_percent']:.0f}%, "
                    f"inside {result['position_ok_percent']:.0f}%, action {result['match_percent']:.0f}%")
        return f"Press 1-{len(self.poses)} to begin a timed gesture trial"


def default_report(root):
    return Path(root)/"output"/f"gesture-trials-{datetime.now():%Y%m%d-%H%M%S-%f}.json"
