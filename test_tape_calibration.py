import unittest
import argparse
from pathlib import Path
import tempfile
from unittest.mock import patch
import cv2
import numpy as np
from tape_calibration import detect_tape_corners, StableTape
from camera_stream import transform_from_corners, map_point


def fixture():
    # Deliberately perspective-skewed corners, with warm brown soil and dark surrounds.
    image = np.full((480, 640, 3), (35, 55, 80), dtype=np.uint8)
    centers = [(100, 90), (530, 110), (550, 390), (80, 370)]
    for x, y in centers:
        cv2.rectangle(image, (x-10, y-10), (x+10, y+10), (235, 235, 235), -1)
    return image, np.array(centers)/[640, 480]


class TapeTests(unittest.TestCase):
    def test_calibration_auto_proposal_requires_enter_and_saves_profile(self):
        from camera_stream import calibrate
        image, expected = fixture()
        class Camera:
            def read(self):
                return True, image.copy()
        with tempfile.TemporaryDirectory() as folder:
            args = argparse.Namespace(rows=2, cols=3, camera=0, profile=Path(folder)/"profile.json")
            with patch("cv2.namedWindow"), patch("cv2.setMouseCallback"), patch("cv2.imshow"), \
                 patch("cv2.destroyWindow"), patch("cv2.waitKey", side_effect=[ord('a')]+[-1]*7+[13]):
                profile = calibrate(Camera(), args)
            self.assertEqual(profile["method"], "white_tape_centers")
            np.testing.assert_allclose(profile["corners"], expected, atol=.001)
            self.assertTrue(args.profile.exists())

    def test_four_centers_order_and_mapping(self):
        image, expected = fixture()
        points, mask, message = detect_tape_corners(image)
        np.testing.assert_allclose(points, expected, atol=.001)
        matrix = transform_from_corners(points, 640, 480)
        for point, target in zip(points, [(0,0),(1,0),(1,1),(0,1)]):
            np.testing.assert_allclose(map_point(matrix, *point), target, atol=1e-6)

    def test_refuses_missing_extra_and_saturated_bright_objects(self):
        image, _ = fixture()
        cv2.rectangle(image, (70, 350), (95, 390), (35,55,80), -1)
        self.assertIsNone(detect_tape_corners(image)[0])
        image, _ = fixture()
        cv2.rectangle(image, (300, 220), (320, 240), (255,255,255), -1)
        self.assertIsNone(detect_tape_corners(image)[0])
        image, expected = fixture()
        cv2.rectangle(image, (300, 220), (320, 240), (0,255,255), -1)
        np.testing.assert_allclose(detect_tape_corners(image)[0], expected, atol=.001)

    def test_search_box_excludes_white_background_distraction(self):
        image, expected = fixture()
        cv2.rectangle(image, (8, 8), (30, 30), (255,255,255), -1)
        self.assertIsNone(detect_tape_corners(image)[0])
        points, _, _ = detect_tape_corners(image, roi=(50,60,540,370))
        np.testing.assert_allclose(points, expected, atol=.001)

    def test_dim_tape_threshold_adjustment(self):
        image, _ = fixture()
        image[np.all(image == (235,235,235), axis=2)] = (155,155,155)
        self.assertIsNone(detect_tape_corners(image)[0])
        self.assertIsNotNone(detect_tape_corners(image, value_min=140)[0])

    def test_stability_resets_after_occlusion_or_motion(self):
        _, points = fixture()
        stable = StableTape(required=3)
        self.assertIsNone(stable.update(points))
        self.assertIsNone(stable.update(points))
        self.assertIsNotNone(stable.update(points))
        stable.update(None)
        self.assertIsNone(stable.update(points))
        self.assertIsNone(stable.update(points+.03))
        self.assertIsNone(stable.update(points+.03))
        self.assertIsNotNone(stable.update(points+.03))


if __name__ == '__main__':
    unittest.main()
