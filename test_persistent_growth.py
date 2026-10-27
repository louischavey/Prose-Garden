import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from garden import Garden, GardenApp
from plant_poem import ROOT, Session
from durable_save import save_json
from run_exhibit import recover, main
from sync_garden import export_snapshot, publish


class PersistentGrowthTests(unittest.TestCase):
    def setUp(self):
        (ROOT/"test-output").mkdir(exist_ok=True)
        self.folder=tempfile.TemporaryDirectory(dir=ROOT/"test-output")
        self.root=Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def test_long_contribution_forms_branches_and_roundtrips_all_species(self):
        text="we leave these little thoughts here for the people who walk through this garden tomorrow"
        for kind in ("flower","fern","conifer"):
            garden=Garden(42,growth_words=2)
            plant=garden.plant(.4,.7,kind,text)
            self.assertEqual(plant.session.words,text.split())
            self.assertEqual(len(plant.session.submissions),1)
            self.assertEqual(plant.session.grammar.generation,8)
            self.assertFalse(plant.renderer.overlaps(plant.renderer.sprites))
            path=self.root/f"{kind}.json"
            save_json(path,garden.pack())
            loaded=Garden.load(path)
            self.assertEqual(loaded.pack(),garden.pack())
            loaded.water_plant(plant.id,"and we return to see it grow")
            self.assertEqual((loaded.get(plant.id).x,loaded.get(plant.id).y),(.4,.7))

    def test_growth_tuning_preserves_words_and_legacy_save(self):
        text="one two three four five six seven eight"
        fast=Session("fern",42,growth_words=1)
        slow=Session("fern",42,growth_words=0)
        fast.add(text);slow.add(text)
        self.assertEqual(fast.words,slow.words)
        self.assertEqual(fast.grammar.generation,8)
        self.assertEqual(slow.grammar.generation,1)
        garden=Garden(42,growth_words=0)
        plant=garden.plant(.4,.6,"fern","old saved plant")
        data=garden.pack()
        data.pop("growth_words")
        data["plants"][0]["session"].pop("growth_words")
        path=self.root/"legacy.json"
        save_json(path,data)
        loaded=Garden.load(path)
        self.assertEqual(loaded.get(plant.id).renderer.layout,plant.renderer.layout)
        self.assertEqual(loaded.get(plant.id).session.growth_words,0)

    def test_failed_replace_preserves_current_and_corrupt_primary_recovers_backup(self):
        path=self.root/"exhibit.json"
        garden=Garden(42)
        plant=garden.plant(.4,.6,"fern","first visitor")
        import copy
        old=copy.deepcopy(garden.pack())
        save_json(path,old)
        garden.water_plant(plant.id,"another visitor leaves a few more thoughts")
        original_replace=Path.replace
        def fail_current(source,target):
            if Path(target)==path: raise OSError("simulated disk failure")
            return original_replace(source,target)
        with patch.object(Path,"replace",fail_current):
            with self.assertRaises(OSError): save_json(path,garden.pack())
        self.assertEqual(Garden.load(path).pack(),old)
        save_json(path,garden.pack())
        path.write_text("partial corrupt data",encoding="utf-8")
        recover(path)
        self.assertEqual(Garden.load(path).pack(),old)
        self.assertTrue(list(self.root.glob("*.corrupt-*")))

    def test_manual_start_resumes_by_default(self):
        from contextlib import nullcontext
        with patch("sys.argv",["run_exhibit.py","--output",str(self.root/"exhibit")]), \
             patch("run_exhibit.single_instance",return_value=nullcontext()), \
             patch("run_exhibit.fresh_session") as fresh, \
             patch("run_exhibit.start_sync") as sync, \
             patch("run_exhibit.supervise",return_value=0) as run:
            self.assertEqual(main(),0)
            fresh.assert_not_called()
            sync.assert_called_once()
            command=run.call_args.args[0]
            for flag,value in (("--camera","0"),("--mic-device","1"),("--hold-seconds","0.75"),
                               ("--word-compression","0.35"),("--words-seconds","15.0"),("--growth-words","2")):
                self.assertEqual(command[command.index(flag)+1],value)

    def test_export_is_read_only_complete_and_does_not_publish(self):
        garden=Garden(42)
        plant=garden.plant(.4,.6,"fern","visitors leave more than five words here")
        path=self.root/"exhibit.json"
        save_json(path,garden.pack())
        before=path.read_bytes()
        destination=self.root/"visitor-data"
        self.assertTrue(export_snapshot(path,destination))
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(json.loads((destination/"latest.json").read_text()),json.loads(json.dumps(garden.pack())))
        self.assertIn("visitors leave more than five words here",(destination/"README.md").read_text(encoding="utf-8"))
        self.assertFalse(export_snapshot(path,destination))

    def test_compression_shrinks_plant_without_moving_root(self):
        garden=Garden(42)
        plant=garden.plant(.4,.7,"fern","one two three four five six seven eight nine ten")
        app=GardenApp(garden,argparse.Namespace(output="test-output/compression",voice="en-US-AriaNeural",word_compression=0.))
        try:
            app.draw()
            original=[rect.copy() for rect,pid in app.hits if pid==plant.id]
            app.word_compression=.7
            app.draw()
            compressed=[rect for rect,pid in app.hits if pid==plant.id]
            self.assertLess(sum(rect.width*rect.height for rect in compressed),sum(rect.width*rect.height for rect in original))
            self.assertEqual((plant.x,plant.y),(.4,.7))
        finally:
            app.dictation.cancel();app.speech.close();app.pg.quit()

    def test_publish_commits_only_snapshot_paths_and_retries_push(self):
        import subprocess
        destination=self.root/"visitor-data"
        calls=[]
        def git(command,**kwargs):
            calls.append(command)
            output="main\n" if command[1]=="symbolic-ref" else "?? snapshot\n" if command[1]=="status" else ""
            return subprocess.CompletedProcess(command,0,stdout=output)
        with patch("sync_garden.subprocess.run",side_effect=git):
            publish(destination)
        commit=next(command for command in calls if command[1]=="commit")
        self.assertIn("--only",commit)
        self.assertEqual(commit[-2:],[str((destination/name).relative_to(ROOT)) for name in ("latest.json","README.md")])
        self.assertEqual(calls[-1],["git","push","origin","HEAD:refs/heads/main"])
        with patch("sync_garden.subprocess.run",side_effect=subprocess.CalledProcessError(1,"push")):
            with self.assertRaises(subprocess.CalledProcessError): publish(destination)

    def test_startup_sync_launch_failure_does_not_stop_exhibit(self):
        from run_exhibit import start_sync
        with patch("run_exhibit.subprocess.Popen",side_effect=OSError("unavailable")):
            start_sync(self.root/"exhibit.json",self.root/"logs")

    def test_startup_sync_can_be_disabled(self):
        from contextlib import nullcontext
        with patch("sys.argv",["run_exhibit.py","--output",str(self.root/"exhibit"),"--no-sync"]), \
             patch("run_exhibit.single_instance",return_value=nullcontext()), \
             patch("run_exhibit.start_sync") as sync, \
             patch("run_exhibit.supervise",return_value=0):
            self.assertEqual(main(),0)
            sync.assert_not_called()

    def test_background_git_has_timeout_and_no_credential_prompts(self):
        import subprocess
        def git(command,**kwargs):
            self.assertEqual(kwargs["timeout"],30)
            self.assertEqual(kwargs["env"]["GIT_TERMINAL_PROMPT"],"0")
            output="main\n" if command[1]=="symbolic-ref" else ""
            return subprocess.CompletedProcess(command,0,stdout=output)
        with patch("sync_garden.subprocess.run",side_effect=git):
            publish(self.root/"visitor-data",non_interactive=True)
