import unittest
from types import SimpleNamespace
import numpy as np
from camera_stream import hand_observation, transform_from_corners
from hand_input import IntentGate


def result(x=.5, y=.5, score=.4, category="None", hands=1):
    landmarks = [SimpleNamespace(x=x, y=y) for _ in range(21)]
    return SimpleNamespace(hand_landmarks=[landmarks for _ in range(hands)],
                           gestures=[[SimpleNamespace(score=score, category_name=category)] for _ in range(hands)])


class ObservationTests(unittest.TestCase):
    def test_low_confidence_pose_preserves_position_but_cannot_fire_or_rearm(self):
        observation = hand_observation(result(), np.eye(3))
        self.assertEqual(observation["state"], "ok")
        self.assertEqual(observation["point"], (.5, .5))
        self.assertEqual(observation["reason"], "gesture_uncertain")
        gate = IntentGate()
        data = dict(session="test", calibration="test", state="ok", x=.5, y=.5,
                    gesture="unknown", score=.4)
        for tick in (0, .3, .6, .9):
            self.assertIsNone(gate.update(data, tick))
        self.assertTrue(gate.latched)
        data.update(state="outside", x=None, y=None)
        gate.update(data, 1.)
        gate.update(data, 1.31)
        self.assertFalse(gate.latched)
        data.update(state="ok", x=.16, y=.25, gesture="closed_fist", score=.4)
        for tick in (1.4, 1.7, 2., 2.3):
            self.assertIsNone(gate.update(data, tick))

    def test_surface_projection_reports_outside_without_action_coordinates(self):
        matrix = transform_from_corners([[.2,.4],[.8,.4],[.8,.9],[.2,.9]], 640, 480)
        observation = hand_observation(result(x=.5, y=.3), matrix)
        self.assertEqual(observation["state"], "outside")
        self.assertIsNone(observation["point"])
        self.assertLess(observation["mapped"][1], 0)
        self.assertIsNotNone(observation["anchor"])
        self.assertEqual(observation["reason"], "palm_outside")

    def test_two_hands_and_stalled_frames_still_suppress_location(self):
        two = hand_observation(result(hands=2, score=.99, category="Open_Palm"), np.eye(3))
        self.assertEqual(two["reason"], "multiple_hands")
        self.assertIsNone(two["point"])
        slow = hand_observation(result(score=.99, category="Open_Palm"), np.eye(3), elapsed=.6)
        self.assertEqual(slow["reason"], "processing_slow")
        self.assertIsNone(slow["point"])


if __name__ == '__main__':
    unittest.main()
