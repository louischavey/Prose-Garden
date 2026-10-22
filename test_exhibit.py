import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from garden import Garden
from plant_poem import ROOT
from run_exhibit import recover, single_instance, supervise


class ExhibitTests(unittest.TestCase):
    def setUp(self):
        (ROOT/"test-output").mkdir(exist_ok=True)
        self.folder=tempfile.TemporaryDirectory(dir=ROOT/"test-output")
        self.root=Path(self.folder.name)
        self.checkpoint=self.root/"exhibit.json"

    def tearDown(self):
        self.folder.cleanup()

    def test_checkpoint_survives_recovery_and_invalid_save_is_not_replaced(self):
        import json
        recover(self.checkpoint)
        garden=Garden.load(self.checkpoint)
        garden.plant(.4,.6,"fern","accepted words")
        self.checkpoint.write_text(json.dumps(garden.pack()),encoding="utf-8")
        recover(self.checkpoint)
        self.assertEqual(Garden.load(self.checkpoint).pack(),garden.pack())
        self.checkpoint.write_text("broken",encoding="utf-8")
        with self.assertRaises(ValueError): recover(self.checkpoint)
        self.assertEqual(self.checkpoint.read_text(),"broken")

    def test_second_instance_is_rejected_and_lock_released(self):
        path=self.root/"exhibit.lock"
        with single_instance(path):
            with self.assertRaises(RuntimeError):
                with single_instance(path): pass
        with single_instance(path): pass

    def test_crash_restart_then_normal_exit_stops(self):
        children=[Mock(),Mock()]
        children[0].wait.return_value=1
        children[1].wait.return_value=0
        with patch("run_exhibit.subprocess.Popen",side_effect=children) as launch, \
             patch("run_exhibit.stop_tree") as stop, patch("run_exhibit.time.sleep"):
            self.assertEqual(supervise(["fake"],self.checkpoint,self.root/"logs"),0)
        self.assertEqual(launch.call_count,2)
        stop.assert_called_once_with(children[0])
        self.assertTrue(self.checkpoint.exists())

    def test_repeated_crashes_stop_at_budget(self):
        child=Mock()
        child.wait.return_value=1
        with patch("run_exhibit.subprocess.Popen",return_value=child) as launch, \
             patch("run_exhibit.stop_tree"), patch("run_exhibit.time.sleep"):
            self.assertEqual(supervise(["fake"],self.checkpoint,self.root/"logs",retries=2),1)
        self.assertEqual(launch.call_count,3)

    def test_camera_crash_restarts_sender_without_restarting_garden(self):
        import start_camera_garden as launcher
        garden=Mock(returncode=0)
        cameras=[]
        garden.poll.side_effect=lambda: 0 if len(cameras)==2 else None
        def launch(command, **kwargs):
            if any(str(arg).endswith("garden.py") and not str(arg).endswith("start_camera_garden.py") for arg in command):
                return garden
            camera=Mock(returncode=1)
            camera.poll.return_value=1 if not cameras else None
            cameras.append(camera)
            return camera
        with patch("sys.argv",["start_camera_garden.py","--confirm-setup","--voice-input","--resilient"]), \
             patch.object(launcher.subprocess,"Popen",side_effect=launch) as spawn, \
             patch.object(launcher.time,"sleep"), \
             patch.object(launcher.time,"monotonic",side_effect=range(0,1000,10)):
            self.assertEqual(launcher.main(),0)
        self.assertEqual(spawn.call_count,3)
        self.assertEqual(len(cameras),2)
        cameras[1].terminate.assert_called_once()
