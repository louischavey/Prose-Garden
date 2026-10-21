import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import argparse
import json
import queue
import unittest
from unittest.mock import patch

from dirt_input import parse_frame, ProbeMap, TapDetector, resolve_port
from garden import Garden, GardenApp
from plant_poem import ROOT


def readings(electrode=None):
    values = [0]*24
    if electrode is not None:
        values[electrode] = 35
    return values


class FakeSerial:
    def __init__(self, port):
        self.frames = queue.Queue(maxsize=1)
        self.message = "Simulated serial"
        self.last_frame = None

    def close(self):
        pass


class DirtTests(unittest.TestCase):
    def test_missing_board_and_recovery(self):
        detector = TapDetector()
        idle = [0]*12 + [-1024]*12
        line = "D,100,"+",".join(map(str, idle))
        self.assertEqual(parse_frame(line), (100, idle))
        detector.update(idle, 0)
        detector.update(idle, .2)
        touched = idle[:]
        touched[10] = 40
        detector.update(touched, .3)
        self.assertEqual(detector.update(touched, .4), 10)
        self.assertIsNone(detector.update([-1024]*24, .5))
        self.assertFalse(detector.armed)
        # A recovered board while touched cannot fire until hands-off rearming.
        self.assertIsNone(detector.update(readings(20), .6))
        self.assertIsNone(detector.update(readings(20), .8))
        detector.update(readings(), .9)
        detector.update(readings(), 1.1)
        detector.update(readings(20), 1.2)
        self.assertEqual(detector.update(readings(20), 1.3), 20)

    def test_partial_location_map(self):
        path = ROOT / "test-output/probe-partial.json"
        mapping = ProbeMap(path, remap=True)
        mapping.record(10)
        for _ in range(23):
            mapping.skip()
        mapping.save()
        restored = ProbeMap(path)
        self.assertEqual(restored.cell(10), (0, 0))
        self.assertIsNone(restored.cell(11))
        restored.mapping = True
        restored.cells = [None]*24
        with self.assertRaises(ValueError):
            restored.save()

    def test_auto_port(self):
        ports = [argparse.Namespace(device="COM3", vid=None),
                 argparse.Namespace(device="COM6", vid=0x239A)]
        self.assertEqual(resolve_port("auto", ports), "COM6")
        self.assertEqual(resolve_port("com6", ports), "COM6")
        with self.assertRaises(ValueError):
            resolve_port("COM5", ports)
        with self.assertRaises(ValueError):
            resolve_port("auto", ports+[argparse.Namespace(device="COM7", vid=0x239A)])

    def setUp(self):
        (ROOT / "test-output").mkdir(exist_ok=True)

    def test_protocol(self):
        valid = "D,123,"+",".join(map(str, readings(23)))+"\r\n"
        self.assertEqual(parse_frame(valid), (123, readings(23)))
        for line in ("ERR,no board", "D,0,1", valid.replace("35", "9999"), valid.replace("35", "nan")):
            self.assertIsNone(parse_frame(line))

    def test_one_tap_per_release_and_no_tie(self):
        detector = TapDetector()
        self.assertIsNone(detector.update(readings(2), 0))  # Must first release.
        detector.update(readings(), .1)
        detector.update(readings(), .3)
        both = readings(2)
        both[3] = 35
        self.assertIsNone(detector.update(both, .4))
        self.assertIsNone(detector.update(readings(2), .5))
        self.assertEqual(detector.update(readings(2), .6), 2)
        self.assertIsNone(detector.update(readings(3), .7))
        detector.update(readings(), .8)
        detector.update(readings(), 1.)
        detector.update(readings(3), 1.1)
        self.assertEqual(detector.update(readings(3), 1.2), 3)
        self.assertIsNone(detector.update(readings(4), 3.))  # Stream gap requires release.

    def test_mapping_roundtrip_and_duplicates(self):
        path = ROOT / "test-output/probe-unit.json"
        mapping = ProbeMap(path, remap=True)
        mapping.record(23)
        with self.assertRaises(ValueError):
            mapping.record(23)
        with self.assertRaises(ValueError):
            mapping.save()
        for electrode in range(22, -1, -1):
            mapping.record(electrode)
        mapping.save()
        restored = ProbeMap(path)
        self.assertEqual(restored.cell(23), (0, 0))
        self.assertEqual(restored.cell(0), (3, 5))
        data = json.loads(path.read_text())
        data["cells"][1] = 23
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            ProbeMap(path)

    def test_serial_mapping_plant_water_save_undo(self):
        args = argparse.Namespace(output="test-output/dirt-garden", voice="en-US-AriaNeural",
                                  serial_port="SIMULATED", probe_map="test-output/probe-ui.json",
                                  map_probes=True, gallery_mode=True)
        with patch("dirt_input.SerialInput", FakeSerial):
            app = GardenApp(Garden(42), args)
        tick = 10.

        def frame(values, increment=.1):
            nonlocal tick
            tick += increment
            wire = "D,"+str(int(tick*1000))+","+",".join(map(str, values))
            parsed = parse_frame(wire)
            app.dirt.frames.put_nowait((tick, parsed))
            app.dirt.last_frame = tick
            with patch("garden.time.monotonic", return_value=tick):
                app.poll_dirt()

        def tap(electrode):
            frame(readings())
            frame(readings(), .2)
            frame(readings(electrode))
            frame(readings(electrode))

        try:
            # Unknown/reversed physical wiring, discovered entirely through frames.
            for electrode in range(23, -1, -1):
                tap(electrode)
            self.assertEqual(app.probe_map.cells, list(range(23, -1, -1)))
            app.draw()
            app.pg.image.save(app.screen, str(ROOT / "test-output/dirt-mapping.png"))
            app.action("map_save")
            self.assertFalse(app.probe_map.mapping)
            tap(23)  # Corner cell outside the mouse-mode planting border.
            app.insert_text("here we grow")
            app.action("water")
            first = app.selected
            self.assertEqual(len(app.garden.plants), 1)
            tap(0)
            app.insert_text("across the soil")
            app.action("water")
            self.assertEqual(len(app.garden.plants), 2)
            tap(23)
            self.assertEqual(app.selected, first)
            app.insert_text("together")
            tap(0)  # Draft cannot migrate to another plant.
            self.assertEqual(app.selected, first)
            app.action("water")
            self.assertEqual(app.garden.get(first).session.words, ["here", "we", "grow", "together"])
            app.save()
            restored = Garden.load(ROOT / "test-output/dirt-garden.json")
            self.assertEqual(restored.pack(), app.garden.pack())
            app.garden = restored
            tap(0)
            tap(23)
            self.assertEqual(app.selected, first)
            app.draw()
            app.pg.image.save(app.screen, str(ROOT / "test-output/dirt-garden-window.png"))
            app.action("undo")
            self.assertEqual(app.garden.get(first).session.words, ["here", "we", "grow"])
        finally:
            app.dirt.close()
            app.speech.close()
            app.pg.quit()


if __name__ == "__main__":
    unittest.main()
