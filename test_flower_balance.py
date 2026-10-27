import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
from collections import Counter
import copy
import math
from pathlib import Path
import tempfile
import unittest
from garden import Garden, GardenRenderer
from plant_poem import ROOT, Session
from durable_save import save_json


class FlowerBalanceTests(unittest.TestCase):
    def counts(self,session):
        return Counter(m.args[1] for m in session.grammar.tape if m.op=="F")

    def test_stem_and_leaves_keep_receiving_words_with_one_head(self):
        session=Session("flower",42,growth_words=2)
        for _ in range(5):
            session.add("one two three four five six seven eight nine ten")
        counts=self.counts(session)
        self.assertGreater(counts["axis"],2)
        self.assertGreater(counts["leaf"],4)
        self.assertGreater(counts["petal"],counts["axis"])
        self.assertEqual(sum(m.op=="G" and m.args[0]==0 for m in session.grammar.tape),6)
        ids=[m.args[0] for m in session.grammar.tape if m.op=="F"]
        self.assertEqual(sorted(ids),list(range(len(session.words))))
        renderer=GardenRenderer();renderer.update(session)
        self.assertFalse(renderer.overlaps(renderer.sprites))

    def test_head_driven_stem_spacing_cannot_exceed_two(self):
        session=Session("flower",42,growth_words=2)
        session.add("stem leaf petal blossoms radiantly around the growing flower")
        renderer=GardenRenderer()
        # Deliberately enormous head to exercise the cap independently of allocation.
        from unittest.mock import patch
        with patch.object(renderer,"flower_origins",return_value=({},100000)):
            # Use only the initial axis modules so no G origin lookup is required.
            session.grammar.tape=[m for m in session.grammar.tape if m.op=="F" and m.args[1]=="axis"]
            nominal=sum(renderer.measure(session.words[m.args[0]])[0]+14 for m in session.grammar.tape)
            layout=renderer.interpret(session)
        length=sum(math.dist(row[:2],row[2:]) for row in layout["lines"])
        self.assertAlmostEqual(length,nominal*2)

    def test_old_flowers_rebalance_transactionally_and_roundtrip(self):
        (ROOT/"test-output").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/"test-output") as folder:
            path=Path(folder)/"garden.json"
            garden=Garden(42)
            flower=garden.plant(.4,.7,"flower","one two three four five six seven eight nine ten")
            tree=garden.plant(.7,.7,"conifer","some words for the tree")
            # Construct an actual old-style session/geometry, then drop the new metadata.
            old=Session("flower",flower.session.seed,growth_words=2,flower_balance=False)
            old.add("one two three four five six seven eight nine ten")
            renderer=GardenRenderer();renderer.update(old)
            flower.session,flower.renderer=old,renderer
            data=garden.pack()
            data["plants"][0]["session"].pop("flower_balance")
            save_json(path,data)
            loaded=Garden.load(path)
            before=copy.deepcopy(loaded.pack())
            self.assertEqual(loaded.rebalance_flowers(),1)
            self.assertEqual(loaded.rebalance_flowers(),0)
            after=loaded.pack()
            self.assertEqual(before["history"],after["history"])
            self.assertEqual(before["plants"][1],after["plants"][1])
            for key in ("id","x","y"):
                self.assertEqual(before["plants"][0][key],after["plants"][0][key])
            self.assertEqual(before["plants"][0]["session"]["submissions"],after["plants"][0]["session"]["submissions"])
            self.assertEqual(before["plants"][0]["session"]["words"],after["plants"][0]["session"]["words"])
            save_json(path,after)
            restored=Garden.load(path)
            self.assertEqual(restored.pack(),after)
            loaded.water_plant(flower.id,"another visitor cultivates the same flower")
            restored.water_plant(flower.id,"another visitor cultivates the same flower")
            self.assertEqual(restored.pack(),loaded.pack())

    def test_fern_and_tree_rules_are_unchanged(self):
        for kind in ("fern","conifer"):
            old=Session(kind,42,growth_words=2,flower_balance=False)
            new=Session(kind,42,growth_words=2,flower_balance=True)
            for session in (old,new):session.add("we leave a few words here for the people after us")
            self.assertEqual(old.pack(None),new.pack(None))
