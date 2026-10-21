import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import argparse
import json
import socket
import time
import unittest
from unittest.mock import patch

from hand_input import HandReceiver, IntentGate, validate


def packet(seq=1, state="ok", gesture="closed_fist", x=.16, y=.25, **kwargs):
    data = dict(version=1, session="test", calibration="fixture", seq=seq, sent_at=time.time(),
                rows=2, cols=3, state=state, x=x if state == "ok" else None,
                y=y if state == "ok" else None, gesture=gesture, score=1.)
    data.update(kwargs)
    return data


class HandTests(unittest.TestCase):
    def test_gate_hold_release_loss_and_pose_transition(self):
        gate = IntentGate()
        self.assertIsNone(gate.update(packet(), 0))  # Cannot arrive already holding command.
        gate.update(packet(state="outside"), .1)
        gate.update(packet(state="outside"), .41)
        gate.update(packet(), .5)
        gate.update(packet(), .8)
        self.assertEqual(gate.update(packet(), 1.11), ("closed_fist", 0, 0))
        for i in range(30):
            self.assertIsNone(gate.update(packet(gesture="open_palm"), 1.2+i*.1))
        gate.update(packet(state="no_hand"), 4.3)
        self.assertIsNone(gate.update(packet(gesture="open_palm"), 4.4))
        gate.update(packet(state="outside"), 4.5)
        gate.update(packet(state="outside"), 4.81)
        gate.update(packet(gesture="open_palm"), 4.9)
        gate.update(packet(gesture="open_palm"), 5.2)
        self.assertEqual(gate.update(packet(gesture="open_palm"), 5.51), ("open_palm", 0, 0))
        gate.interrupt()
        self.assertIsNone(gate.update(packet(), 5.6))

    def test_boundary_and_low_confidence_do_not_arm(self):
        gate = IntentGate()
        for t in (0, .4, .8):
            gate.update(packet(gesture="unknown", score=.1), t)
        self.assertTrue(gate.latched)
        self.assertIsNone(gate.cell(1/3, .3))
        self.assertIsNone(gate.cell(.2, .5))
        self.assertIsNone(gate.cell(-.01, .2))
        self.assertEqual(gate.cell(.8, .8), (1, 2))

    def test_udp_and_malformed_stale_duplicate(self):
        receiver = HandReceiver(port=0)
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            address = receiver.socket.getsockname()
            def send(data):
                sender.sendto(json.dumps(data).encode(), address)
                time.sleep(.005)
                return receiver.poll()
            self.assertEqual(send(packet())["seq"], 1)
            self.assertIsNone(send(packet()))
            self.assertIsNone(send(packet(2, sent_at=time.time()-3)))
            self.assertIsNone(send(packet(3, x=float("nan"))))
            self.assertIsNone(send({"version": 9}))
            self.assertEqual(send(packet(4, state="no_hand"))["state"], "no_hand")
        finally:
            sender.close()
            receiver.close()

    def test_actual_udp_to_garden_plant_cultivate_save_reload(self):
        from garden import Garden, GardenApp
        from plant_poem import ROOT
        app = GardenApp(Garden(42), argparse.Namespace(output="test-output/camera-e2e", voice="en-US-AriaNeural",
                         hand_stream=True, hand_port=0))
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        address = app.hand.socket.getsockname()
        seq, tick = 0, time.monotonic()
        def frame(gesture="closed_fist", state="ok", x=.16, y=.25):
            nonlocal seq, tick
            seq += 1
            tick += .11
            sender.sendto(json.dumps(packet(seq, state, gesture, x, y)).encode(), address)
            time.sleep(.002)
            with patch("hand_input.time.monotonic", return_value=tick):
                app.poll_hand()
        def release():
            for _ in range(4):
                frame(state="outside")
        def hold(gesture="closed_fist", **kwargs):
            for _ in range(8):
                frame(gesture, **kwargs)
        try:
            release()
            hold()
            self.assertEqual(app.pending, (1/6, .25))
            self.assertEqual(len(app.garden.plants), 0)
            app.insert_text("we grow together")
            app.action("water")
            first = app.selected
            self.assertEqual(len(app.garden.plants), 1)
            # Accepted words are recoverable even before a full Save/PNG export.
            checkpoint = Garden.load(ROOT/"test-output/camera-e2e.json")
            self.assertEqual(checkpoint.plants[0].session.words, ["we", "grow", "together"])
            hold("open_palm")  # Direct pose change is latched.
            release()
            hold("open_palm")
            self.assertEqual(app.selected, first)
            app.handle_hand_intent("open_palm", 1, 2)  # Empty target clears old selection.
            self.assertIsNone(app.selected)
            self.assertIsNone(app.pending)
            app.handle_hand_intent("open_palm", 0, 0)
            app.insert_text("under shared skies")
            release()
            hold(x=.8, y=.75)  # Draft cannot migrate to an empty plot.
            self.assertEqual(app.selected, first)
            app.action("water")
            self.assertEqual(app.garden.get(first).session.words,
                             ["we", "grow", "together", "under", "shared", "skies"])
            release()
            hold(x=.8, y=.75)
            self.assertIsNotNone(app.pending)
            app.insert_text("another visitor")
            app.action("water")
            self.assertEqual(len(app.garden.plants), 2)
            app.draw()
            app.pg.image.save(app.screen, str(ROOT/"test-output/camera-e2e-ui.png"))
            app.save()
            restored = Garden.load(ROOT/"test-output/camera-e2e.json")
            self.assertEqual(restored.pack(), app.garden.pack())
            app.garden = restored
            release()
            hold("open_palm")
            self.assertEqual(app.selected, first)
            app.action("undo")
            self.assertEqual(len(app.garden.plants), 1)
            app.action("finish")
            release()
            hold(x=.8, y=.75)
            self.assertIsNone(app.pending)
        finally:
            sender.close()
            app.hand.close()
            app.speech.close()
            app.pg.quit()

    def test_batch_does_not_hide_tracking_interruption(self):
        from garden import Garden, GardenApp
        app = GardenApp(Garden(42), argparse.Namespace(output="test-output/batch-camera", voice="en-US-AriaNeural",
                         hand_stream=True, hand_port=0))
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        address = app.hand.socket.getsockname()
        seq = 0
        def send(state="ok"):
            nonlocal seq
            seq += 1
            sender.sendto(json.dumps(packet(seq, state=state)).encode(), address)
        def tick(now):
            time.sleep(.002)
            with patch("hand_input.time.monotonic", return_value=now):
                app.poll_hand()
        try:
            send("outside"); tick(0)
            send("outside"); tick(.31)
            send(); tick(.4)
            send(); tick(.7)
            # Both packets arrive in one UI tick: invalid sample must reset dwell.
            send("no_hand")
            send()
            tick(1.01)
            self.assertIsNone(app.pending)
            send(); tick(1.3)
            self.assertIsNone(app.pending)
            send(); tick(1.65)
            self.assertIsNotNone(app.pending)
        finally:
            sender.close()
            app.hand.close()
            app.speech.close()
            app.pg.quit()

    def test_homography_maps_independent_points_and_rejects_bad_corners(self):
        from camera_stream import map_point, transform_from_corners
        matrix = transform_from_corners([[.1,.1], [.9,.1], [.9,.9], [.1,.9]], 640, 480)
        self.assertAlmostEqual(map_point(matrix, .5,.5)[0], .5, places=6)
        self.assertAlmostEqual(map_point(matrix, .3,.7)[1], .75, places=6)
        with self.assertRaises(ValueError):
            transform_from_corners([[.1,.1], [.9,.9], [.9,.1], [.1,.9]], 640, 480)


if __name__ == "__main__":
    unittest.main()
