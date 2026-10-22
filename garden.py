"""A shared, freely planted garden of L-system poems. Run: python garden.py."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import math
import queue
import random
import threading
import time
import uuid

from plant_poem import ROOT, PLANTS, PAPER, INK, HIGHLIGHT, Session, Renderer, Speech, inside

WORLD = (1200, 800)
PLANT_SCALE = .55
ROOT_CUSHION = 28
# Upright plants need more room above their roots than below them.
PLANTING_BOUNDS = (.10, .22, .90, .90)


class GardenRenderer(Renderer):
    def make_sprites(self, session, layout):
        sprites = super().make_sprites(session, layout)
        for _, normal, lit, _, _ in sprites:
            # Preserve antialiased alpha while making the glyphs truly black.
            normal.fill((0, 0, 0, 255), special_flags=self.pg.BLEND_RGBA_MULT)
            lit.fill((0, 0, 0, 255), special_flags=self.pg.BLEND_RGBA_MULT)
        return sprites


@dataclass
class Plant:
    id: str
    x: float
    y: float
    session: Session
    renderer: Renderer


class Garden:
    """UI-independent model. Coordinates are normalized ground coordinates."""

    def __init__(self, seed=None, turns=True, connectors=False):
        self.seed = seed if seed is not None else random.SystemRandom().getrandbits(64)
        self.turns, self.connectors = turns, connectors
        self.plants = []
        self.history = []
        self.serial = 0

    def get(self, plant_id):
        return next(p for p in self.plants if p.id == plant_id)

    @staticmethod
    def position(x, y):
        if not all(type(v) in (float, int) and math.isfinite(v) and 0 <= v <= 1 for v in (x, y)):
            raise ValueError("Tap coordinates must be between 0 and 1.")

    def near_root(self, x, y):
        self.position(x, y)
        candidates = [(math.hypot((x-p.x)*WORLD[0], (y-p.y)*WORLD[1]), p) for p in self.plants]
        distance, plant = min(candidates, key=lambda item: item[0], default=(math.inf, None))
        return plant if distance < ROOT_CUSHION else None

    def snap_root(self, x, y, current_id=None, radius=70):
        """Nearby root selection with hysteresis; never uses overlapping foliage."""
        self.position(x,y)
        distances = sorted(((math.hypot((x-p.x)*WORLD[0], (y-p.y)*WORLD[1]), p)
                            for p in self.plants), key=lambda item: (item[0], item[1].id))
        if not distances:
            return None
        distance, nearest = distances[0]
        current = next(((d,p) for d,p in distances if p.id == current_id), None)
        if current and current[0] <= radius*1.3 and (distance > radius or distance+15 >= current[0]):
            return current[1]
        return nearest if distance <= radius else None

    def plant(self, x, y, kind, text, allow_edge=False):
        self.position(x, y)
        if not allow_edge and not self.plantable(x, y):
            raise ValueError("Plant inside the garden border to leave room for growth.")
        if kind not in PLANTS:
            raise ValueError("Choose flower, conifer, or fern.")
        if self.near_root(x, y):
            raise ValueError("That root is occupied. Water it or choose a nearby spot.")
        if len(self.plants) >= 100:
            raise ValueError("This prototype supports 100 plants per garden.")
        seed = random.Random(f"{self.seed}:{self.serial}").getrandbits(64)
        session = Session(kind, seed, self.turns, self.connectors)
        session.add(text)
        renderer = GardenRenderer()
        renderer.update(session)
        plant = Plant(uuid.uuid4().hex, x, y, session, renderer)
        self.plants.append(plant)
        self.history.append(plant.id)
        self.serial += 1
        return plant

    def water_plant(self, plant_id, text):
        plant = self.get(plant_id)
        # Build off to the side; an invalid or crowded submission cannot damage it.
        session = Session.from_data(plant.session.pack(plant.renderer.layout))
        session.add(text)
        renderer = GardenRenderer()
        renderer.update(session)
        plant.session, plant.renderer = session, renderer
        self.history.append(plant_id)
        return plant

    def undo(self):
        if not self.history:
            return None
        plant = self.get(self.history[-1])
        session = Session.from_data(plant.session.pack(plant.renderer.layout))
        session.undo()
        if session.words:
            renderer = GardenRenderer()
            renderer.update(session)
            plant.session, plant.renderer = session, renderer
        else:
            self.plants.remove(plant)
        self.history.pop()
        return plant.id

    def pack(self):
        return {"format": "poetree-garden", "version": 1, "seed": self.seed,
                "turns": self.turns, "connectors": self.connectors, "serial": self.serial,
                "history": self.history[:], "plants": [
                    {"id": p.id, "x": p.x, "y": p.y, "session": p.session.pack(p.renderer.layout)}
                    for p in self.plants]}

    @staticmethod
    def plantable(x, y):
        left, top, right, bottom = PLANTING_BOUNDS
        return left <= x <= right and top <= y <= bottom

    @classmethod
    def load(cls, path):
        path = inside(path)
        if path.stat().st_size > 30_000_000:
            raise ValueError("Garden file is too large.")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("format") != "poetree-garden" or data.get("version") != 1:
            raise ValueError("Unsupported garden file.")
        if type(data.get("seed")) is not int or any(type(data.get(k)) is not bool for k in ("turns", "connectors")):
            raise ValueError("Invalid garden settings.")
        rows = data.get("plants")
        if not isinstance(rows, list) or len(rows) > 100:
            raise ValueError("Invalid plant list.")
        garden = cls(data["seed"], data["turns"], data["connectors"])
        for row in rows:
            if not isinstance(row, dict) or not all(k in row for k in ("id", "x", "y", "session")):
                raise ValueError("Invalid plant record.")
            if not isinstance(row["id"], str) or not row["id"] or any(p.id == row["id"] for p in garden.plants):
                raise ValueError("Duplicate or invalid plant ID.")
            garden.position(row["x"], row["y"])
            session = Session.from_data(row["session"])
            if not session.words or garden.near_root(row["x"], row["y"]):
                raise ValueError("Empty plant or overlapping roots in save.")
            renderer = GardenRenderer()
            renderer.update(session)
            garden.plants.append(Plant(row["id"], row["x"], row["y"], session, renderer))
        history = data.get("history")
        ids = {p.id for p in garden.plants}
        if not isinstance(history, list) or not all(isinstance(v, str) and v in ids for v in history):
            raise ValueError("Invalid undo history.")
        if any(history.count(p.id) != len(p.session.submissions) for p in garden.plants):
            raise ValueError("Undo history does not match submissions.")
        if type(data.get("serial")) is not int or data["serial"] < len(garden.plants):
            raise ValueError("Invalid planting counter.")
        garden.serial, garden.history = data["serial"], history
        return garden


class Dictation:
    """One short recording; recognition never submits words automatically."""

    def __init__(self, events, device=None, language="en-US", silence=False):
        self.events = events
        self.busy = False
        self.stop_event = threading.Event()
        self.ticket = 0
        self.device=device
        self.language=language
        self.silence = silence

    def cancel(self):
        self.ticket += 1
        self.stop_event.set()

    def start(self, seconds=8):
        if self.busy:
            self.stop_event.set()
            return
        self.busy = True
        self.ticket += 1
        ticket = self.ticket
        self.stop_event = threading.Event()
        stop = self.stop_event

        def record():
            outcome=None
            try:
                import sounddevice as sd
                import speech_recognition as sr
                rate = int(sd.query_devices(self.device,kind="input")["default_samplerate"])
                if self.silence:
                    rate = 16000
                chunks = []
                with sd.RawInputStream(samplerate=rate, channels=1, dtype="int16",device=self.device) as stream:
                    if self.silence:
                        import webrtcvad
                        from speech_input import capture_speech
                        pcm = capture_speech(stream, stop, seconds, webrtcvad.Vad(2))
                        if pcm is None:
                            return
                        chunks.append(pcm)
                    else:
                        deadline = time.monotonic() + seconds
                        while not stop.is_set() and time.monotonic() < deadline:
                            chunk, overflow = stream.read(max(1, rate // 10))
                            if overflow:
                                raise RuntimeError("Microphone overflow. Please try again.")
                            chunks.append(bytes(chunk))
                if ticket != self.ticket:
                    return
                if not chunks:
                    raise ValueError("No recording captured.")
                self.events.put(("dictating", ticket))
                recognizer = sr.Recognizer()
                recognizer.operation_timeout = 15
                if ticket != self.ticket:
                    return
                text = recognizer.recognize_google(sr.AudioData(b"".join(chunks), rate, 2),language=self.language)
                outcome=("dictation",(ticket,text))
            except Exception as exc:
                outcome=("dictation_error",(ticket,str(exc) or "Speech could not be understood."))
            finally:
                self.busy = False
                if outcome is not None and ticket==self.ticket:
                    self.events.put(outcome)
        threading.Thread(target=record, daemon=True).start()


class GardenApp:
    def __init__(self, garden, args):
        self.garden, self.args = garden, args
        self.gallery_mode = getattr(args, "gallery_mode", False)
        self.dirt = None
        self.hand = None
        self.hand_cursor = None
        self.hand_hover = None
        self.hand_confirm_until = 0.
        self.hand_click = getattr(args, "hand_click", False)
        self.hand_gate = None
        self.probe_map = None
        self.dirt_cell = None
        self.dirt_flash_until = 0
        self.dirt_last_ms = None
        self.dirt_peak = 0
        if getattr(args, "serial_port", None) and not getattr(args, "mouse_only", False):
            from dirt_input import ProbeMap, TapDetector
            self.probe_map = ProbeMap(getattr(args, "probe_map", "output/probe-map.json"),
                                      getattr(args, "map_probes", False))
            self.tap_detector = TapDetector(getattr(args, "touch_threshold", 12),
                                           getattr(args, "release_threshold", 6))
        self.ui = Renderer()
        self.pg = self.ui.pg
        self.pg.display.init()
        self.screen = self.pg.display.set_mode((1280, 860), self.pg.RESIZABLE)
        self.pg.display.set_caption("Poetree | a garden of words")
        self.pg.key.start_text_input()
        self.pg.key.set_repeat(400, 35)
        self.texture = self.pg.image.load(str(ROOT / "assets/grass-summer.png")).convert()
        self.backgrounds = {}
        self.sprite_cache = {}
        self.events = queue.Queue()
        self.speech = Speech(self.events, args.voice)
        self.dictation = Dictation(self.events,getattr(args,"mic_device",None),getattr(args,"speech_language","en-US"),
                                  silence=getattr(args,"voice_input",False))
        from voice_flow import VoiceFlow
        self.voice_flow=VoiceFlow(self) if getattr(args,"voice_input",False) else None
        self.selected = None
        self.pending = None
        self.kind = "flower"
        self.draft = ""
        self.caret = 0
        self.select_all = False
        self.focus = False
        self.zoom = 1.0
        self.pan = [0, 0]
        self.drag = None
        self.scroll = 0
        self.max_scroll = 0
        self.finished = False
        self.running = True
        self.buttons = []
        self.hits = []
        self.status = "Click the grass to plant. Click a plant to water it."
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        self.save_base = inside(args.output or f"output/garden-{stamp}")
        self.relayout()
        if self.probe_map is not None:
            from dirt_input import SerialInput
            self.dirt = SerialInput(args.serial_port)
        if getattr(args, "hand_stream", False):
            from hand_input import HandReceiver, IntentGate, ClickGate
            gate_type = ClickGate if self.hand_click else IntentGate
            self.hand_gate = gate_type(getattr(args, "hand_rows", 2), getattr(args, "hand_cols", 3))
            self.hand = HandReceiver(getattr(args, "hand_host", "127.0.0.1"), getattr(args, "hand_port", 8765))
            self.status = "Camera mode: one visitor. Exit tray to arm. Gesture mappings are shown in camera preview/Terminal."

    def handle_hand_click(self, x, y, target_id=None):
        """Same click cultivates a snapped root or previews free-position planting."""
        if self.finished:
            return
        if self.voice_flow is not None and self.voice_flow.active:
            self.voice_flow.retry_click()
            return
        if self.draft.strip() or self.dictation.busy:
            self.status = "Submit this draft or Escape to clear it before choosing another spot."
            return
        self.garden.position(x,y)
        plant = next((p for p in self.garden.plants if p.id == target_id), None)
        if target_id is not None and plant is None:
            self.status = "Target changed. Point again before clicking."
            return
        self.selected = self.pending = None
        self.focus = False
        if plant is None and not self.garden.plantable(x,y):
            self.status = "Choose empty ground inside the pale planting border."
            return
        self.speech.stop()
        self.dictation.cancel()
        self.selected = plant.id if plant else None
        self.pending = None if plant else (x,y)
        self.focus, self.zoom, self.pan, self.scroll = bool(plant), 1, [0,0], 0
        self.status = "Cultivate selected plant: enter 1-5 words, then Enter/Water." if plant else "New planting spot: choose type, enter 1-5 words, then Enter/Water."
        if self.voice_flow is not None:
            self.voice_flow.begin()

    def poll_hand_click(self):
        data = self.hand.poll()
        if data is None:
            if self.hand.last_received is None or time.monotonic()-self.hand.last_received > .5:
                self.hand_cursor = self.hand_hover = None
                self.hand_gate.interrupt()
            return
        intent = None
        for received, observation in self.hand.batch:
            if (observation.get("rows"), observation.get("cols")) != (self.hand_gate.rows,self.hand_gate.cols):
                self.hand_cursor = self.hand_hover = None
                self.hand_gate.interrupt()
                self.hand.message = "Camera layout mismatch; commands stopped"
                intent = None
                continue
            self.hand_cursor = (observation["x"],observation["y"]) if observation["state"] == "ok" else None
            plant = self.garden.snap_root(*self.hand_cursor, self.hand_hover) if self.hand_cursor else None
            self.hand_hover = plant.id if plant else None
            flow = self.voice_flow
            if flow is not None and flow.active and flow.phase != "error":
                self.hand_gate.interrupt()
                continue
            retry = flow is not None and flow.phase == "error"
            target = (self.selected or "voice-retry") if retry else self.hand_hover
            event = self.hand_gate.update(observation, received, target_id=target)
            if event is not None:
                intent = event
            if intent and (self.hand_cursor is None or observation["gesture"] != "click" or
                           observation["score"] < self.hand_gate.score or intent["target_id"] != target):
                intent = None
            if intent and intent["target_id"] is None and math.hypot((intent["x"]-observation["x"])*WORLD[0],
                                                                     (intent["y"]-observation["y"])*WORLD[1]) > 48:
                intent = None
        if intent is not None:
            self.hand_confirm_until = time.monotonic()+.4
            self.handle_hand_click(**intent)

    def handle_hand_intent(self, gesture, row, col):
        """Camera sections own roots; foliage never steals another section's input."""
        if self.finished:
            return
        if self.draft.strip() or self.dictation.busy:
            self.status = "Submit this draft or Escape to clear it before selecting another plot."
            return
        # A rejected new selection must not leave an unrelated old target writable.
        self.selected = self.pending = None
        self.focus = False
        rows, cols = self.hand_gate.rows, self.hand_gate.cols
        occupants = [p for p in self.garden.plants
                     if min(rows-1, int(p.y*rows)) == row and min(cols-1, int(p.x*cols)) == col]
        if len(occupants) > 1:
            self.status = "Several roots in this section. Use the mouse to select explicitly."
            return
        if gesture == "closed_fist" and occupants:
            self.status = "Plot occupied. Use your cultivation gesture."
            return
        if gesture == "open_palm" and not occupants:
            self.status = "Empty plot. Use your planting gesture."
            return
        self.speech.stop()
        self.dictation.cancel()
        if gesture == "open_palm":
            self.selected, self.pending = occupants[0].id, None
            self.status = "Cultivate: type or dictate 1-5 words, then Enter / Water."
        else:
            # Keep anchor within its section AND the existing safe planting border.
            x, y = (col+.5)/cols, (row+.5)/rows
            left, top, right, bottom = PLANTING_BOUNDS
            x, y = max(left, min(right, x)), max(top, min(bottom, y))
            if not (col/cols <= x < (col+1)/cols and row/rows <= y < (row+1)/rows):
                self.status = "Section has no safe root anchor. Use a 2x2 or 2x3 layout."
                return
            self.selected, self.pending = None, (x, y)
            self.status = "Plant: choose type, type or dictate 1-5 words, then Enter / Water."
        self.focus, self.zoom, self.pan, self.scroll = False, 1, [0, 0], 0

    def poll_hand(self):
        if self.hand is None:
            return
        if self.hand_click:
            self.poll_hand_click()
            return
        data = self.hand.poll()
        if data is None:
            if self.hand.last_received is None or time.monotonic()-self.hand.last_received > .5:
                self.hand_cursor = None
                self.hand_gate.interrupt()
            return
        intent = None
        for received, observation in self.hand.batch:
            if (observation.get("rows"), observation.get("cols")) != (self.hand_gate.rows, self.hand_gate.cols):
                self.hand_cursor = None
                self.hand_gate.interrupt()
                self.hand.message = "Camera layout mismatch; commands stopped"
                intent = None
                continue
            # Preserve interruptions inside a batch even though only the last cursor is drawn.
            self.hand_cursor = (observation["x"], observation["y"]) if observation["state"] == "ok" else None
            event = self.hand_gate.update(observation, received)
            if event is not None:
                intent = event
            current_cell = self.hand_gate.cell(observation["x"], observation["y"]) if observation["state"] == "ok" else None
            if intent and (current_cell is None or (observation["gesture"], *current_cell) != intent or observation["score"] < self.hand_gate.score):
                intent = None
        if intent is not None:
            self.handle_hand_intent(*intent)

    def checkpoint(self):
        """Atomic accepted-word recovery in camera mode; full Save also exports PNG."""
        base = self.save_base.with_suffix("") if self.save_base.suffix in (".json", ".png") else self.save_base
        base.parent.mkdir(parents=True, exist_ok=True)
        target = inside(base.with_suffix(".json"))
        pending = inside(base.with_suffix(".checkpoint.json"))
        pending.write_text(json.dumps(self.garden.pack(), ensure_ascii=False, indent=2), encoding="utf-8")
        pending.replace(target)

    def handle_dirt_tap(self, row, col):
        """Select by root's grid cell, never by an overlapping word sprite."""
        if not (0 <= row < 4 and 0 <= col < 6) or self.finished:
            return
        if self.draft.strip() and (self.selected or self.pending):
            self.status = "Water this draft first, or Escape to clear it before changing cells."
            return
        self.speech.stop()
        self.dictation.cancel()
        self.dirt_cell = (row, col)
        self.dirt_flash_until = time.monotonic()+1
        # Positions persist in the normal garden JSON, so cell ownership survives reload.
        occupants = [p for p in self.garden.plants
                     if min(3, int(p.y*4)) == row and min(5, int(p.x*6)) == col]
        if len(occupants) > 1:
            self.status = "Multiple existing plants in this cell. Use mouse mode to select, or start a new dirt garden."
            return
        self.selected = occupants[0].id if occupants else None
        self.pending = None if occupants else ((col+.5)/6, (row+.5)/4)
        self.focus, self.zoom, self.pan, self.scroll = False, 1, [0, 0], 0
        self.status = f"Dirt row {row+1}, column {col+1}: " + ("add words to water." if occupants else "choose a plant and add words.")

    def poll_dirt(self):
        if self.dirt is None:
            return
        try:
            stamp, (ms, values) = self.dirt.frames.get_nowait()
        except queue.Empty:
            return
        if time.monotonic()-stamp > .5:
            self.tap_detector.reset()
            return
        if self.dirt_last_ms is not None and ms <= self.dirt_last_ms:
            self.tap_detector.reset()
        self.dirt_last_ms = ms
        self.dirt_peak = max(0, max(values))
        if not self.probe_map.mapping:
            values = [v if i in self.probe_map.cells else -1024 for i, v in enumerate(values)]
        electrode = self.tap_detector.update(values, stamp)
        if electrode is None:
            return
        if self.probe_map.mapping:
            try:
                self.probe_map.record(electrode)
                self.status = "Location recorded. Lift your finger before the next highlighted cell."
            except ValueError as exc:
                self.status = str(exc)
        else:
            cell = self.probe_map.cell(electrode)
            if cell is not None:
                self.handle_dirt_tap(*cell)

    def draw_dirt_overlay(self):
        pg = self.pg
        mapping = self.probe_map.mapping
        if not mapping and time.monotonic() >= self.dirt_flash_until:
            return
        for row in range(4):
            for col in range(6):
                cell = row*6+col
                rect = pg.Rect(round(self.area.x+col*self.area.width/6), round(self.area.y+row*self.area.height/4),
                               round(self.area.width/6), round(self.area.height/4))
                if mapping:
                    pg.draw.rect(self.screen, PAPER, rect, 1)
                    label = str(cell+1)
                    if cell < len(self.probe_map.cells):
                        from dirt_input import electrode_name
                        label += " / " + electrode_name(self.probe_map.cells[cell])
                    self.label(label, rect.x+8, rect.y+8)
                if (mapping and cell == len(self.probe_map.cells)) or (not mapping and self.dirt_cell == (row, col)):
                    pg.draw.rect(self.screen, (255, 234, 120), rect.inflate(-6, -6), 5)
        if mapping:
            count = len(self.probe_map.cells)
            message = (f"Touch dirt at highlighted cell {count+1}/24, then lift." if count < 24
                       else "All locations mapped or skipped. Click Use mapping.")
            banner = pg.Rect(self.area.x+8, self.area.bottom-70, self.area.width-16, 62)
            pg.draw.rect(self.screen, PAPER, banner, border_radius=6)
            self.label(message, banner.x+8, banner.y+6)
            self.button("Undo location", (banner.x+8, banner.y+29, 140, 28), "map_undo")
            if count == 24:
                self.button("Use mapping", (banner.x+160, banner.y+29, 140, 28), "map_save", True)
            else:
                self.button("Skip location", (banner.x+160, banner.y+29, 140, 28), "map_skip")

    def relayout(self):
        w, h = self.screen.get_size()
        self.area = self.pg.Rect(20, 86, max(200, w-390), max(200, h-120))
        self.panel = self.pg.Rect(w-350, 86, 330, h-120)
        self.input_rect = self.pg.Rect(self.panel.x+16, 250, 298, 84)
        self.read_rect = self.pg.Rect(self.panel.x+16, 420, 298, max(45, h-510))

    def label(self, text, x, y, color=INK, font=None):
        self.screen.blit((font or self.ui.small).render(text, True, color), (x, y))

    def button(self, label, rect, action, active=False):
        rect = self.pg.Rect(rect)
        self.pg.draw.rect(self.screen, (210, 222, 194) if active else (232, 230, 214), rect, border_radius=7)
        self.screen.blit(self.ui.small.render(label, True, INK), self.ui.small.render(label, True, INK).get_rect(center=rect.center))
        self.buttons.append((rect, action))

    def background(self, size):
        if size not in self.backgrounds:
            self.backgrounds.clear()
            # One cover-scaled field avoids visible seams in the supplied raster.
            ratio = max(size[0]/self.texture.get_width(), size[1]/self.texture.get_height())
            image = self.pg.transform.scale(self.texture, (math.ceil(self.texture.get_width()*ratio), math.ceil(self.texture.get_height()*ratio)))
            surface = self.pg.Surface(size)
            surface.blit(image, ((size[0]-image.get_width())//2, (size[1]-image.get_height())//2))
            self.backgrounds[size] = surface
        return self.backgrounds[size]

    def badge(self, surface, text, position, bounds):
        """Readable labels over any grass pixel, constrained to the garden."""
        glyph = self.ui.small.render(text, True, PAPER)
        rect = glyph.get_rect().inflate(18, 10)
        rect.topleft = position
        rect.clamp_ip(bounds)
        self.pg.draw.rect(surface, INK, rect, border_radius=6)
        surface.blit(glyph, (rect.x+9, rect.y+5))

    def panel_text(self, text, x, y, width=290, color=INK):
        line = ""
        for word in text.split():
            candidate = (line+" "+word).strip()
            if line and self.ui.small.size(candidate)[0] > width:
                self.label(line, x, y, color)
                y += 23
                line = word
            else:
                line = candidate
        self.label(line, x, y, color)
        return y+23

    def draw_garden(self, surface, area, selected=None, interactive=False):
        pg = self.pg
        surface.blit(self.background(area.size), area)
        if interactive and self.probe_map is None:
            left, top, right, bottom = PLANTING_BOUNDS
            inner = pg.Rect(round(area.x+left*area.width), round(area.y+top*area.height),
                            round((right-left)*area.width), round((bottom-top)*area.height))
            border = pg.Surface(area.size, pg.SRCALPHA)
            border.fill((155, 158, 153, 115))
            border.fill((0, 0, 0, 0), inner.move(-area.x, -area.y))
            surface.blit(border, area)
            pg.draw.rect(surface, (206, 217, 160), inner, 1, border_radius=8)
        previous = surface.get_clip()
        surface.set_clip(area)
        scale = min(area.width/WORLD[0], area.height/WORLD[1]) * PLANT_SCALE
        ordered = sorted(self.garden.plants, key=lambda p: p.y)
        if selected:
            ordered.sort(key=lambda p: p.id == selected)
        hits = []
        for plant in ordered:
            ox, oy = area.x+plant.x*area.width, area.y+plant.y*area.height
            pg.draw.ellipse(surface, (85, 110, 57), (ox-17, oy-4, 34, 9))
            faded = selected is not None and plant.id != selected
            if plant.session.connectors:
                for x1, y1, x2, y2 in plant.renderer.layout["lines"]:
                    pg.draw.aaline(surface, (155, 169, 112), (ox+x1*scale, oy+y1*scale), (ox+x2*scale, oy+y2*scale))
            highlight = self.speech.highlighted() if interactive and plant.id == self.selected else None
            for word_id, normal, lit, rect, _ in plant.renderer.sprites:
                key = (plant.id, id(plant.renderer), word_id, word_id == highlight, round(scale, 5), faded)
                if key not in self.sprite_cache:
                    original = lit if word_id == highlight else normal
                    sprite = pg.transform.smoothscale(original, (max(1, round(original.get_width()*scale)), max(1, round(original.get_height()*scale))))
                    outline = pg.mask.from_surface(sprite).to_surface(setcolor=(255, 253, 237, 255), unsetcolor=(0, 0, 0, 0))
                    combined = pg.Surface((sprite.get_width()+6, sprite.get_height()+6), pg.SRCALPHA)
                    for dx in range(-2, 3):
                        for dy in range(-2, 3):
                            if dx*dx+dy*dy <= 5:
                                combined.blit(outline, (3+dx, 3+dy))
                    combined.blit(sprite, (3, 3))
                    if faded:
                        combined.set_alpha(175)
                    self.sprite_cache[key] = combined
                sprite = self.sprite_cache[key]
                dest = sprite.get_rect(center=(round(ox+rect.centerx*scale), round(oy+rect.centery*scale)))
                surface.blit(sprite, dest)
                if word_id == highlight:
                    pg.draw.rect(surface, HIGHLIGHT, dest.inflate(4, 4), 1, border_radius=3)
                hits.append((dest, plant.id))
        # Root markers stay above foliage so a covered plant can still be reached.
        for plant in ordered:
            center = (round(area.x+plant.x*area.width), round(area.y+plant.y*area.height))
            pg.draw.circle(surface, PAPER if plant.id == selected else (174, 191, 120), center, 7)
            pg.draw.circle(surface, INK, center, 7, 1)
        if interactive and self.pending:
            center = (round(area.x+self.pending[0]*area.width), round(area.y+self.pending[1]*area.height))
            pg.draw.circle(surface, PAPER, center, 14, 2)
            pg.draw.line(surface, PAPER, (center[0]-20, center[1]), (center[0]+20, center[1]))
            pg.draw.line(surface, PAPER, (center[0], center[1]-20), (center[0], center[1]+20))
        surface.set_clip(previous)
        if interactive:
            self.hits = hits
            if self.hand is not None:
                rows, cols = self.hand_gate.rows, self.hand_gate.cols
                for row in range(rows):
                    for col in range(cols):
                        rect = pg.Rect(round(area.x+col*area.width/cols), round(area.y+row*area.height/rows),
                                       round(area.width/cols), round(area.height/rows))
                        pg.draw.rect(surface, (240, 235, 195), rect, 1)
                        surface.blit(self.ui.small.render(str(row*cols+col+1), True, INK), (rect.x+8, rect.y+8))
                if self.hand_cursor is not None:
                    cursor = self.hand_cursor
                    hovered = next((p for p in self.garden.plants if p.id == self.hand_hover), None)
                    if self.hand_click and hovered:
                        cursor = (hovered.x,hovered.y)
                    xy = (round(area.x+cursor[0]*area.width), round(area.y+cursor[1]*area.height))
                    pg.draw.circle(surface, INK, xy, 19, 6)
                    pg.draw.circle(surface, PAPER, xy, 17, 3)
                    if self.hand_click:
                        progress = 1. if time.monotonic() < self.hand_confirm_until else self.hand_gate.progress
                        if progress > 0:
                            points = [(xy[0]+17*math.cos(-math.pi/2+2*math.pi*progress*i/64),
                                       xy[1]+17*math.sin(-math.pi/2+2*math.pi*progress*i/64)) for i in range(65)]
                            pg.draw.lines(surface, (46, 202, 181), False, points, 5)
                    if self.hand_click:
                        label = "Cultivate this plant" if hovered else "Plant here" if self.garden.plantable(*cursor) else "Reserved edge"
                        if self.voice_flow is not None and self.voice_flow.active:
                            label = "Hold pinch 2s to retry" if self.voice_flow.phase == "error" else "Voice target locked"
                        elif self.hand_gate.latched:
                            label = "Open pinch to rearm"
                        elif self.hand_gate.progress > 0:
                            label = "Hold pinch 2s"
                        self.badge(surface, label, (xy[0]+18, xy[1]-34), area.inflate(-8, -8))
                fresh = self.hand.last_received is not None and time.monotonic()-self.hand.last_received < .5
                status = self.hand.message if fresh else "Camera stream stopped - move outside tray after reconnect"
                self.badge(surface, status, (area.x+8, area.bottom-34), area.inflate(-8, -8))

    def handle_garden_tap(self, x_normalized, y_normalized):
        """Public tap API: call on the UI thread; coordinates exclude controls."""
        self.garden.position(x_normalized, y_normalized)
        if self.probe_map is not None:
            if not self.probe_map.mapping:
                self.handle_dirt_tap(min(3, int(y_normalized*4)), min(5, int(x_normalized*6)))
            return
        if self.draft.strip() and (self.selected or self.pending):
            self.status = "Water this draft first, or press Escape to discard it before changing plants."
            return
        self.speech.stop()
        self.dictation.cancel()
        plant = self.garden.near_root(x_normalized, y_normalized)
        if not plant:
            point = (self.area.x+x_normalized*self.area.width, self.area.y+y_normalized*self.area.height)
            plant_id = next((pid for rect, pid in reversed(self.hits) if rect.collidepoint(point)), None)
            plant = self.garden.get(plant_id) if plant_id else None
        if not plant and not self.garden.plantable(x_normalized, y_normalized):
            self.status = "Plant inside the pale border; the edge is reserved for growing branches."
            return
        self.selected = plant.id if plant else None
        self.pending = None if plant else (x_normalized, y_normalized)
        self.focus, self.zoom, self.pan, self.scroll = bool(plant), 1, [0, 0], 0
        self.status = "Add 1-5 words to water this plant." if plant else "Choose a plant and enter its first 1-5 words."

    def water_plant(self, plant_id, text):
        if self.finished:
            raise ValueError("Garden finished. Reopen the saved JSON to continue.")
        self.speech.stop()
        self.dictation.cancel()
        plant = self.garden.water_plant(plant_id, text)
        self.sprite_cache.clear()
        return plant

    def insert_text(self, text):
        if self.select_all:
            self.draft, self.caret = "", 0
            self.select_all = False
        text = " ".join(text.splitlines())
        if len(self.draft)+len(text) > 1000:
            self.status = "Draft is too long; water 1-5 words at a time."
            return
        self.draft = self.draft[:self.caret]+text+self.draft[self.caret:]
        self.caret += len(text)

    def action(self, action):
        try:
            if self.probe_map is not None and self.probe_map.mapping:
                if action == "map_undo":
                    if self.probe_map.cells:
                        self.probe_map.cells.pop()
                    self.tap_detector.reset()
                    self.status = "Lift your finger, then retry the highlighted location."
                elif action == "map_save":
                    self.probe_map.save()
                    self.tap_detector.reset()
                    self.status = "Mapping saved. Lift, then tap dirt to plant or water."
                elif action == "map_skip":
                    self.probe_map.skip()
                    self.tap_detector.reset()
                    self.status = "Location skipped. Continue with the working probes."
                else:
                    self.status = "Finish the location mapping first."
                return
            if action in PLANTS:
                self.kind = action
            elif action == "water":
                if self.voice_flow is not None and self.voice_flow.active and self.voice_flow.phase!="confirm":
                    raise ValueError("Finish voice entry and review the draft before confirming.")
                if self.finished:
                    raise ValueError("Garden finished. Reopen its JSON to continue.")
                if self.dictation.busy:
                    raise ValueError("Wait for the dictation draft, or stop it first.")
                if self.selected:
                    self.water_plant(self.selected, self.draft)
                elif self.pending:
                    plant = self.garden.plant(*self.pending, self.kind, self.draft,
                                              allow_edge=self.probe_map is not None)
                    self.selected, self.pending = plant.id, None
                else:
                    raise ValueError("Click the grass or an existing plant first.")
                self.draft, self.caret, self.select_all = "", 0, False
                self.status = "Watered. Add more words, or click another spot."
                if self.hand is not None:
                    try:
                        self.checkpoint()
                    except OSError as exc:
                        self.status = f"Words accepted but recovery save failed: {exc}. Use Ctrl/Cmd+S."
                if self.voice_flow is not None and self.voice_flow.active:
                    self.voice_flow.submitted()
            elif action == "undo":
                if self.finished:
                    raise ValueError("Reopen the saved garden to continue.")
                self.speech.stop()
                self.dictation.cancel()
                changed = self.garden.undo()
                if self.selected and not any(p.id == self.selected for p in self.garden.plants):
                    self.selected, self.focus = None, False
                self.sprite_cache.clear()
                self.status = "Last watering undone." if changed else "Nothing to undo."
                if self.hand is not None and changed:
                    try:
                        self.checkpoint()
                    except OSError as exc:
                        self.status = f"Undo applied but recovery save failed: {exc}. Use Ctrl/Cmd+S."
            elif action == "focus":
                self.focus = bool(self.selected) and not self.focus
                self.zoom, self.pan = 1, [0, 0]
            elif action == "read":
                if self.voice_flow is not None and self.voice_flow.active:
                    raise ValueError("Finish or cancel voice entry before reading aloud.")
                if not self.selected:
                    raise ValueError("Choose a plant to read.")
                self.dictation.cancel()
                self.speech.request(self.garden.get(self.selected).session.words)
                self.status = "Preparing online spoken playback (Microsoft speech service)."
            elif action == "stop":
                self.speech.stop()
                self.dictation.cancel()
                if self.voice_flow is not None:
                    self.voice_flow.cancel(clear=False)
                self.status = "Stopped."
            elif action == "mic":
                if self.voice_flow is not None:
                    if self.voice_flow.active:
                        self.voice_flow.retry_click()
                    elif not (self.selected or self.pending) or self.finished:
                        raise ValueError("Choose a planting spot or a plant first.")
                    elif self.draft.strip():
                        self.voice_flow.target=(self.selected,self.pending)
                        self.voice_flow.failures=0
                        self.voice_flow.schedule("confirm")
                    else:
                        self.voice_flow.begin()
                    return
                if not (self.selected or self.pending) or self.finished:
                    raise ValueError("Choose a planting spot or a plant first.")
                self.speech.stop()
                self.dictation.start()
                self.status = "Listening up to 8 seconds; click Mic again to transcribe."
            elif action in ("save", "finish"):
                if action == "finish" and self.draft.strip():
                    raise ValueError("Water your draft first, or press Escape to discard it before finishing.")
                self.save()
                if action == "finish":
                    self.finished = True
                    self.dictation.cancel()
                    self.status = "Finished and saved. Reopen the JSON to water again."
        except (ValueError, OSError, RuntimeError, self.pg.error) as exc:
            self.status = str(exc)

    def save(self):
        base = self.save_base
        if base.suffix in (".json", ".png"):
            base = base.with_suffix("")
        base.parent.mkdir(parents=True, exist_ok=True)
        pending = inside(base.with_suffix(".pending.json"))
        pending.write_text(json.dumps(self.garden.pack(), ensure_ascii=False, indent=2), encoding="utf-8")
        image = self.pg.Surface(WORLD)
        self.draw_garden(image, image.get_rect())
        png = inside(base.with_suffix(".pending.png"))
        self.pg.image.save(image, str(png))
        png.replace(inside(base.with_suffix(".png")))
        pending.replace(inside(base.with_suffix(".json")))
        self.status = f"Saved {base.name}.json + .png"

    def draw(self):
        pg = self.pg
        self.screen.fill(PAPER)
        self.buttons = []
        self.label("POETREE", 22, 18, font=self.ui.title)
        self.label("a garden of words", 22, 49)
        if self.dirt is not None:
            hardware_status = self.dirt.message
            if self.dirt.last_frame is not None and time.monotonic()-self.dirt.last_frame > 2:
                hardware_status = "No fresh dirt readings. " + hardware_status
            self.label(f"{hardware_status} | peak {self.dirt_peak} | " +
                       ("ready" if self.tap_detector.armed else "lift finger to rearm"), 210, 52,
                       font=self.pg.font.Font(None, 18))
        actions = [("Undo", "undo")]
        if not self.gallery_mode:
            actions += [("Save", "save"), ("Finish", "finish")]
        for i, (label, action) in enumerate(actions):
            self.button(label, (self.screen.get_width()-20-(len(actions)-i)*94, 24, 86, 34), action)
        if self.focus and self.selected and self.hand is None:
            pg.draw.rect(self.screen, (236, 236, 214), self.area)
            plant = self.garden.get(self.selected)
            old = self.screen.get_clip()
            self.screen.set_clip(self.area)
            target = self.area.inflate(-40, -40)
            target.size = (round(target.width*self.zoom), round(target.height*self.zoom))
            target.center = (self.area.centerx+self.pan[0], self.area.centery+self.pan[1])
            plant.renderer.draw_plant(self.screen, target, plant.session.connectors, self.speech.highlighted())
            self.screen.set_clip(old)
            self.label("Scroll to zoom / drag to pan / Focus to return", self.area.x+12, self.area.y+12)
        else:
            self.draw_garden(self.screen, self.area, self.selected, True)
        if self.probe_map is not None and not self.focus:
            self.draw_dirt_overlay()
        pg.draw.rect(self.screen, (241, 239, 226), self.panel, border_radius=10)
        x = self.panel.x+16
        title = "Cultivate this plant" if self.selected else "Plant a poem"
        self.label("Garden finished" if self.finished else title, x, 102, font=self.ui.title)
        if self.voice_flow is not None:
            flow = self.voice_flow
            if self.selected:
                plant = self.garden.get(self.selected)
                self.panel_text(f"SELECTED: {plant.session.plant.title()} / {len(plant.session.words)} words", x, 139)
                self.label("Selection stays until you choose again.", x, 166, font=pg.font.Font(None, 19))
            elif self.pending:
                self.label("New planting spot selected", x, 139)
            else:
                self.panel_text("Point, then hold pinch for 2 seconds.", x, 139)
            steps = [("Type", "type"), ("Words", "words"), ("Confirm", "confirm")]
            for i, (name, phase) in enumerate(steps):
                rect = pg.Rect(x+i*100, 194, 94, 29)
                active = flow.phase == phase
                pg.draw.rect(self.screen, INK if active else (221, 226, 209), rect, border_radius=6)
                glyph = self.ui.small.render(name, True, PAPER if active else INK)
                self.screen.blit(glyph, glyph.get_rect(center=rect.center))
            # Status distinguishes capture from transcription, where speech is no longer recorded.
            listening = self.status.startswith("Listening") and self.dictation.busy
            state = "LISTENING" if listening else "TRANSCRIBING" if self.dictation.busy else "GET READY" if flow.pending else "VOICE PAUSED" if flow.phase == "error" else "READY"
            self.label(state, x, 232, INK)
            self.panel_text(flow.prompt, x, 257)
            preview = pg.Rect(x, 310, 298, 65)
            pg.draw.rect(self.screen, (255, 253, 243), preview, border_radius=6)
            old = self.screen.get_clip()
            self.screen.set_clip(preview.inflate(-12, -8))
            self.panel_text(self.draft or "Your spoken words appear here.", x+8, 318, 280)
            self.screen.set_clip(old)
            self.label(f"{len(self.draft.split())} / 5 words", x, 380, font=pg.font.Font(None, 19))
            self.label("Say confirm to save; retry or cancel.", x, 400, font=pg.font.Font(None, 19))
            self.read_rect.top = 442
            self.read_rect.height = max(30, self.panel.bottom-64-self.read_rect.top)
            self.label("Mic uses Google / internet required", x, 421, font=pg.font.Font(None, 17))
        else:
            if self.selected:
                plant = self.garden.get(self.selected)
                self.label(f"{plant.session.plant.title()} / {len(plant.session.words)} words", x, 139)
            else:
                self.label("Choose a spot on the grass.", x, 139)
                for i, kind in enumerate(PLANTS):
                    self.button("Tree" if kind == "conifer" else kind.title(), (x+i*100, 174, 94, 34), kind, self.kind == kind)
            self.label(self.voice_flow.prompt if self.voice_flow else "Add 1-5 words / Enter to water", x, 222)
            pg.draw.rect(self.screen, (221, 231, 207) if self.select_all else (255, 253, 243), self.input_rect, border_radius=6)
            old = self.screen.get_clip()
            self.screen.set_clip(self.input_rect.inflate(-12, -8))
            # A horizontal draft with a visible caret; long text scrolls with the caret.
            offset = max(0, self.ui.small.size(self.draft[:self.caret])[0]-self.input_rect.width+28)
            self.label(self.draft or "Type here...", x+8-offset, 267)
            caret_x = x+8+self.ui.small.size(self.draft[:self.caret])[0]-offset
            pg.draw.line(self.screen, INK, (caret_x, 265), (caret_x, 288))
            self.label(f"{len(self.draft.split())} words", x+8, 306)
            self.screen.set_clip(old)
            self.button("Water", (x, 345, 92, 34), "water", True)
            self.button("Mic / end", (x+102, 345, 94, 34), "mic", self.dictation.busy)
            self.button("Focus", (x+206, 345, 92, 34), "focus", self.focus)
            self.label("Mic sends audio to Google for transcription.", x, 390, font=pg.font.Font(None, 17))
        old = self.screen.get_clip()
        self.screen.set_clip(self.read_rect)
        if self.selected:
            words = self.garden.get(self.selected).session.words
            tx, ty = self.read_rect.x, self.read_rect.y-self.scroll
            highlight = self.speech.highlighted()
            for i, word in enumerate(words):
                width = self.ui.small.size(word+" ")[0]
                if tx > self.read_rect.x and tx+width > self.read_rect.right:
                    tx, ty = self.read_rect.x, ty+24
                self.label(word, tx, ty, HIGHLIGHT if i == highlight else INK)
                tx += width
            self.max_scroll = max(0, ty+26+self.scroll-self.read_rect.bottom)
        else:
            self.max_scroll = 0
            self.label("Your poem appears here in entry order.", self.read_rect.x, self.read_rect.y)
        self.screen.set_clip(old)
        self.scroll = min(self.scroll, self.max_scroll)
        self.button("Read aloud", (x, self.panel.bottom-46, 140, 32), "read")
        self.button("Stop", (x+152, self.panel.bottom-46, 146, 32), "stop")
        # Status fits the footer; full messages also remain available in the title.
        self.label(self.status, 22, self.screen.get_height()-25, font=pg.font.Font(None, 19))
        pg.display.flip()

    def event(self, event):
        pg = self.pg
        if self.probe_map is not None and self.probe_map.mapping and event.type in (pg.TEXTINPUT, pg.KEYDOWN):
            return
        if event.type == pg.QUIT:
            if self.draft.strip():
                self.status = "Unsubmitted draft: Water it, or press Escape to discard it before closing."
                return
            try:
                self.save()
                self.running = False
            except (OSError, ValueError, pg.error) as exc:
                self.status = f"Save failed; window kept open: {exc}"
        elif event.type == pg.VIDEORESIZE:
            self.screen = pg.display.set_mode((max(940, event.w), max(700, event.h)), pg.RESIZABLE)
            self.sprite_cache.clear()
            self.relayout()
        elif event.type == pg.TEXTINPUT and not self.finished:
            self.insert_text(event.text)
        elif event.type == pg.KEYDOWN:
            ctrl = event.mod & (pg.KMOD_CTRL | pg.KMOD_META)
            if event.key == pg.K_ESCAPE:
                self.draft, self.caret, self.select_all = "", 0, False
                self.dictation.cancel()
                self.focus = False
                self.status = "Draft cleared. Click a plant or a new spot."
            elif event.key == pg.K_RETURN:
                self.action("water")
            elif ctrl and event.key == pg.K_s:
                self.action("save")
            elif ctrl and event.key == pg.K_z:
                self.action("undo")
            elif ctrl and event.key == pg.K_a:
                self.select_all = True
            elif ctrl and event.key == pg.K_v:
                try:
                    pg.scrap.init()
                    raw = pg.scrap.get(pg.SCRAP_TEXT)
                    if raw:
                        self.insert_text(raw.decode("utf-8", errors="replace").rstrip("\x00"))
                except pg.error:
                    self.status = "Clipboard unavailable. Type or dictate instead."
            elif event.key in (pg.K_BACKSPACE, pg.K_DELETE):
                if self.select_all:
                    self.draft, self.caret, self.select_all = "", 0, False
                elif event.key == pg.K_BACKSPACE and self.caret:
                    self.draft = self.draft[:self.caret-1]+self.draft[self.caret:]
                    self.caret -= 1
                elif event.key == pg.K_DELETE:
                    self.draft = self.draft[:self.caret]+self.draft[self.caret+1:]
            elif event.key in (pg.K_LEFT, pg.K_RIGHT, pg.K_HOME, pg.K_END):
                self.select_all = False
                self.caret = (0 if event.key == pg.K_HOME else len(self.draft) if event.key == pg.K_END
                              else max(0, min(len(self.draft), self.caret+(-1 if event.key == pg.K_LEFT else 1))))
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            for rect, action in self.buttons:
                if rect.collidepoint(event.pos):
                    self.action(action)
                    return
            if self.area.collidepoint(event.pos):
                if self.focus:
                    self.drag = event.pos
                else:
                    self.handle_garden_tap((event.pos[0]-self.area.x)/self.area.width, (event.pos[1]-self.area.y)/self.area.height)
        elif event.type == pg.MOUSEBUTTONUP:
            self.drag = None
        elif event.type == pg.MOUSEMOTION and self.drag:
            self.pan[0] += event.pos[0]-self.drag[0]
            self.pan[1] += event.pos[1]-self.drag[1]
            self.drag = event.pos
        elif event.type == pg.MOUSEWHEEL:
            if self.read_rect.collidepoint(pg.mouse.get_pos()):
                self.scroll = max(0, min(self.max_scroll, self.scroll-event.y*48))
            elif self.focus:
                self.zoom = max(.5, min(8, self.zoom*1.15**event.y))

    def process_messages(self):
        while not self.events.empty():
            kind, data = self.events.get_nowait()
            if kind == "speech" and data[0] == self.speech.ticket:
                try:
                    self.speech.play(data[1], data[2])
                    self.status = "Reading in entry order."
                except Exception as exc:
                    self.status = f"Playback unavailable: {exc}"
            elif kind == "speech_error" and data[0] == self.speech.ticket:
                self.status = str(data[1])
            elif kind == "dictating" and data == self.dictation.ticket:
                self.status = "Transcribing online..."
            elif kind == "dictation" and data[0] == self.dictation.ticket:
                if self.voice_flow is not None and self.voice_flow.receive(data[0],text=data[1]):
                    continue
                self.insert_text((" " if self.draft else "")+data[1])
                self.status = "Review your draft, then Water. Use 1-5 words."
            elif kind == "dictation_error" and data[0] == self.dictation.ticket:
                if self.voice_flow is not None and self.voice_flow.receive(data[0],error=data[1]):
                    continue
                self.status = f"Dictation unavailable: {data[1]}"

    def run(self):
        clock = self.pg.time.Clock()
        try:
            while self.running:
                for event in self.pg.event.get():
                    self.event(event)
                self.process_messages()
                if self.voice_flow is not None:
                    self.voice_flow.poll()
                self.poll_dirt()
                self.poll_hand()
                self.draw()
                clock.tick(30)
        finally:
            if self.hand is not None:
                self.hand.close()
            if self.dirt is not None:
                self.dirt.close()
            self.dictation.cancel()
            self.speech.close()
            self.pg.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--load", help="Saved garden JSON inside this folder")
    parser.add_argument("--output", help="Save basename inside this folder")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--connectors", action="store_true")
    parser.add_argument("--no-turns", action="store_true")
    parser.add_argument("--gallery-mode", "--gallery_mode", action="store_true",
                        help="Hide Save and Finish buttons; close still saves the garden")
    parser.add_argument("--voice", default="en-US-AriaNeural")
    parser.add_argument("--voice-input",action="store_true",help="After a hand click, speak type, words, and confirm/retry/cancel")
    parser.add_argument("--mic-device",type=lambda value:int(value) if value.isdigit() else value,help="sounddevice microphone index or name (default: system input)")
    parser.add_argument("--speech-language",default="en-US",help="Transcription language")
    parser.add_argument("--serial-port", help="auto, or Metro USB port such as COM6 or /dev/cu.usbmodem...")
    parser.add_argument("--hand-stream", action="store_true", help="Receive normalized hand+gesture UDP packets")
    parser.add_argument("--hand-click", action="store_true", default=True, help="Default: one click gesture; snap to nearby roots or plant at cursor")
    parser.add_argument("--legacy-hand-gestures", dest="hand_click", action="store_false", help="Compatibility only: old two-gesture section selection")
    parser.add_argument("--hand-host", default="127.0.0.1", help="Bind address; use 0.0.0.0 only on trusted LAN")
    parser.add_argument("--hand-port", type=int, default=8765)
    parser.add_argument("--hand-rows", type=int, default=2)
    parser.add_argument("--hand-cols", type=int, default=3)
    parser.add_argument("--mouse-only", action="store_true", help="Use mouse input; ignore serial and probe mapping options")
    parser.add_argument("--probe-map", default="output/probe-map.json", help="Saved 24-cell location map")
    parser.add_argument("--map-probes", action="store_true", help="Redo the guided location mapping")
    parser.add_argument("--touch-threshold", type=int, default=12, help="Minimum baseline-minus-filtered delta")
    parser.add_argument("--release-threshold", type=int, default=6, help="All probes must fall to this level to rearm")
    args = parser.parse_args()
    if args.mouse_only:
        args.serial_port = None
        args.map_probes = False
    if args.map_probes and not args.serial_port:
        parser.error("--map-probes requires --serial-port")
    if args.hand_stream and (args.serial_port or args.mouse_only):
        parser.error("Use --hand-stream separately from --serial-port / --mouse-only")
    if args.voice_input and not (args.hand_stream and args.hand_click):
        parser.error("--voice-input requires --hand-stream in single-click mode")
    try:
        garden = Garden.load(args.load) if args.load else Garden(args.seed, not args.no_turns, args.connectors)
        GardenApp(garden, args).run()
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Poetree: {exc}\n")


if __name__ == "__main__":
    main()
