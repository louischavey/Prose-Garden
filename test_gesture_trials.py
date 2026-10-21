import argparse
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

from camera_stream import hand_observation, main
from gesture_trials import GestureTrials, POSES


def sample(label="Victory", state="ok", score=.99):
    return dict(raw_pose=label, state=state, score=score)


class GestureTrialTests(unittest.TestCase):
    def test_pose_mapping_does_not_change_anchor_or_position(self):
        landmarks = [SimpleNamespace(x=.2+i*.01, y=.3+i*.007) for i in range(21)]
        matrix = np.array([[1.2,0,-.1],[0,1.1,-.1],[0,0,1.]])
        reference = None
        for pose in POSES:
            result = SimpleNamespace(hand_landmarks=[landmarks], gestures=[[SimpleNamespace(category_name=pose, score=.99)]])
            original = hand_observation(result, matrix)
            remapped = hand_observation(result, matrix, plant_pose="Victory", cultivate_pose="Pointing_Up")
            for key in ("anchor", "mapped", "point", "state"):
                if isinstance(original[key], np.ndarray):
                    np.testing.assert_array_equal(original[key], remapped[key])
                else:
                    self.assertEqual(original[key], remapped[key])
            if reference is not None:
                np.testing.assert_array_equal(remapped["anchor"], reference["anchor"])
                self.assertEqual(remapped["point"], reference["point"])
            reference = remapped
            self.assertEqual(remapped["gesture"], "closed_fist" if pose == "Victory" else "open_palm" if pose == "Pointing_Up" else "unknown")

    def test_trials_measure_confusion_and_require_continuous_hold(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"report.json"
            trials = GestureTrials(path)
            trials.start(2, 0)
            trials.update(sample(), 2.9)  # Countdown excluded.
            for tick in (3.,3.2,3.4,3.7):
                trials.update(sample(), tick)
            trials.update(sample("Open_Palm"), 4.)
            trials.update(sample(state="outside"), 4.2)
            result = trials.update(sample(), 8.)
            self.assertEqual(result["samples"], 6)
            self.assertEqual(result["matching_samples"], 4)
            self.assertTrue(result["met_600ms_hold"])
            self.assertEqual(result["observed_labels"]["Open_Palm"], 1)
            self.assertEqual(json.loads(path.read_text())["trials"][0], result)

    def test_gap_or_low_confidence_cannot_count_as_continuous_hold(self):
        with tempfile.TemporaryDirectory() as directory:
            trials = GestureTrials(Path(directory)/"report.json")
            trials.start(2, 0)
            for tick in (3.,3.2,4.,4.2):
                trials.update(sample(), tick)
            trials.update(sample(score=.4), 4.3)
            trials.update(sample(), 4.4)
            result = trials.update(sample(), 8.)
            self.assertFalse(result["met_600ms_hold"])

    def test_test_mode_sends_no_udp_and_does_not_rewrite_profile(self):
        # Run the production test-mode loop with fake camera/model, real mapping.
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)/"profile.json"
            contents = json.dumps(dict(version=1,id="unchanged",camera=0,width=640,height=480,
                                       rows=2,cols=3,corners=[[.1,.1],[.9,.1],[.9,.9],[.1,.9]]))
            profile.write_text(contents)
            camera = MagicMock()
            camera.isOpened.return_value = True
            camera.read.return_value = (True, np.zeros((480,640,3), dtype=np.uint8))
            recognizer = MagicMock()
            recognizer.recognize_for_video.return_value = SimpleNamespace(hand_landmarks=[], gestures=[])
            context = MagicMock()
            context.__enter__.return_value = recognizer
            with patch("sys.argv", ["camera_stream.py", "--confirm-setup", "--gesture-test", "--profile", str(profile)]), \
                 patch("cv2.VideoCapture", return_value=camera), patch("cv2.imshow"), patch("cv2.destroyAllWindows"), \
                 patch("cv2.waitKey", return_value=ord('q')), patch("socket.socket") as socket_factory, \
                 patch("mediapipe.tasks.python.vision.GestureRecognizer.create_from_options", return_value=context):
                main()
            socket_factory.return_value.sendto.assert_not_called()
            self.assertEqual(profile.read_text(), contents)
            camera.release.assert_called_once()


if __name__ == '__main__':
    unittest.main()
