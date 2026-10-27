import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import argparse
import json
import unittest
from garden import Garden, GardenApp
from plant_poem import ROOT


class GardenTests(unittest.TestCase):
    def test_gallery_border_and_black_text(self):
        garden = Garden(7)
        for x, y in ((.01, .5), (.5, .01), (.99, .5), (.5, .99)):
            with self.assertRaises(ValueError):
                garden.plant(x, y, "fern", "edge")
        plant = garden.plant(.1, .22, "fern", "inside")
        for sprite in plant.renderer.sprites:
            surface = sprite[1]
            opaque = [surface.get_at((x, y)) for x in range(surface.get_width())
                      for y in range(surface.get_height()) if surface.get_at((x, y)).a > 0]
            self.assertTrue(opaque)
            self.assertTrue(all(tuple(color)[:3] == (0, 0, 0) for color in opaque))
        app = GardenApp(garden, argparse.Namespace(output="test-output/gallery", voice="en-US-AriaNeural", gallery_mode=True))
        try:
            app.draw()
            actions = [action for _, action in app.buttons]
            self.assertNotIn("save", actions)
            self.assertNotIn("finish", actions)
            self.assertNotIn("undo", actions)
            app.handle_garden_tap(.99, .99)
            self.assertIsNone(app.pending)
            # Legacy edge plants remain reachable and waterable.
            plant.x, plant.y = .02, .02
            app.draw()
            app.handle_garden_tap(.02, .02)
            self.assertEqual(app.selected, plant.id)
            app.water_plant(plant.id, "still growing")
        finally:
            app.speech.close()
            app.pg.quit()

    def test_window_events_and_dictation_draft(self):
        garden = Garden(7)
        app = GardenApp(garden, argparse.Namespace(output="test-output/garden-events", voice="en-US-AriaNeural"))
        try:
            pg = app.pg
            app.draw()
            app.event(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=app.area.center))
            app.event(pg.event.Event(pg.TEXTINPUT, text="first"))
            app.event(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN, mod=0))
            self.assertEqual(garden.plants[0].session.words, ["first"])
            app.events.put(("dictation", (app.dictation.ticket, "next words")))
            app.process_messages()
            self.assertEqual(app.draft, "next words")
            self.assertEqual(garden.plants[0].session.words, ["first"])
            app.action("finish")
            self.assertFalse(app.finished)
            app.event(pg.event.Event(pg.QUIT))
            self.assertTrue(app.running)
            app.action("water")
            self.assertEqual(garden.plants[0].session.words, ["first", "next", "words"])
            app.dictation.cancel()
            app.events.put(("dictation", (app.dictation.ticket-1, "stale result")))
            app.process_messages()
            self.assertEqual(app.draft, "")
            # Exercise the actual loop through a clean auto-saving close.
            pg.event.post(pg.event.Event(pg.QUIT))
            app.run()
            self.assertFalse(app.running)
        finally:
            if app.running:
                app.speech.close()
                app.pg.quit()

    def test_water_append_and_transaction(self):
        garden = Garden(42)
        plant = garden.plant(.3, .5, "fern", "first word")
        garden.water_plant(plant.id, "next words")
        before = garden.pack()
        with self.assertRaises(ValueError):
            garden.water_plant(plant.id, "x"*121)
        self.assertEqual(before, garden.pack())
        self.assertEqual(plant.session.words, ["first", "word", "next", "words"])
        garden.undo()
        self.assertEqual(plant.session.words, ["first", "word"])
        garden.undo()
        self.assertEqual(garden.plants, [])

    def test_roots_and_validation(self):
        garden = Garden(42)
        plant = garden.plant(.5, .5, "flower", "hello")
        self.assertIs(garden.near_root(.501, .501), plant)
        with self.assertRaises(ValueError):
            garden.plant(.51, .5, "fern", "close")
        for x in (float("nan"), -1, 2, True):
            with self.assertRaises(ValueError):
                garden.near_root(x, .5)
        garden.plant(.54, .5, "fern", "foliage can overlap")

    def test_save_reopen_and_ui(self):
        garden = Garden(42)
        args = argparse.Namespace(output="test-output/garden-integration", voice="en-US-AriaNeural")
        app = GardenApp(garden, args)
        try:
            app.draw()
            app.handle_garden_tap(.25, .7)
            app.insert_text("we grow toward light")
            app.action("water")
            first = app.selected
            for text in ("and bend", "into the wind", "a circle", "of golden words", "around the sun", "then bloom", "beyond this moment"):
                app.water_plant(first, text)
            second = garden.plant(.55, .75, "conifer", "the forest")
            for text in ("holds", "our voices", "in its branches", "we listen", "and leave", "a little light"):
                app.water_plant(second.id, text)
            third = garden.plant(.8, .82, "fern", "here we begin")
            for text in ("again", "with softer words", "and open hands", "unfurling", "into morning"):
                app.water_plant(third.id, text)
            app.draw()
            # A draft cannot accidentally migrate to another plant.
            app.insert_text("stay here")
            app.handle_garden_tap(.8, .82)
            self.assertEqual(app.selected, first)
            app.draft, app.caret = "", 0
            app.save()
            loaded = Garden.load(ROOT / "test-output/garden-integration.json")
            self.assertEqual(garden.pack(), loaded.pack())
            garden.water_plant(first, "new morning")
            loaded.water_plant(first, "new morning")
            self.assertEqual(garden.pack(), loaded.pack())
            app.draw()
            app.pg.image.save(app.screen, str(ROOT / "test-output/garden-window.png"))
            app.action("focus")
            app.draw()
            app.pg.image.save(app.screen, str(ROOT / "test-output/garden-focus.png"))
            # Invalid history must not become executable undo operations.
            data = loaded.pack()
            data["history"] = ["unknown"]
            bad = ROOT / "test-output/garden-invalid.json"
            bad.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                Garden.load(bad)
        finally:
            app.dictation.cancel()
            app.speech.close()
            app.pg.quit()


if __name__ == "__main__":
    unittest.main()
