import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import argparse
import json
import socket
import time
import unittest
from unittest.mock import patch
from hand_input import ClickGate, validate
from test_hand_input import packet
from garden import Garden, GardenApp


class ClickTests(unittest.TestCase):
    def test_single_click_hold_release_and_target_change(self):
        gate=ClickGate(hold=.6)
        outside=packet(state="outside",gesture="unknown")
        gate.update(outside,0)
        gate.update(outside,.31)
        click=packet(gesture="click")
        self.assertIsNone(gate.update(click,.4,target_id="A"))
        self.assertIsNone(gate.update(click,.7,target_id="B"))
        self.assertIsNone(gate.update(click,1.,target_id="B"))
        event=gate.update(click,1.31,target_id="B")
        self.assertEqual(event["target_id"],"B")
        self.assertIsNone(gate.update(click,1.5,target_id="B"))
        gate.update(packet(state="no_hand"),1.6)
        self.assertIsNone(gate.update(click,1.7,target_id="A"))
        validate(click)

    def test_default_two_second_hold_progress_and_single_activation(self):
        gate=ClickGate()
        gate.update(packet(state="outside"),0)
        gate.update(packet(state="outside"),.31)
        event=None
        for i in range(21):
            event=gate.update(packet(gesture="click"),.4+i*.1,target_id="root")
            if i==10:
                self.assertAlmostEqual(gate.progress,.5)
            if i<20:
                self.assertIsNone(event)
        self.assertIsNotNone(event)
        self.assertIsNone(gate.update(packet(gesture="click"),2.5,target_id="root"))
        self.assertEqual(gate.progress,0)

    def test_brief_uncertainty_pauses_but_loss_clears_progress(self):
        gate=ClickGate()
        gate.update(packet(state="outside"),0)
        gate.update(packet(state="outside"),.31)
        for tick in (.4,.6,.8):
            gate.update(packet(gesture="click"),tick)
        progress=gate.progress
        gate.update(packet(gesture="unknown",score=.2),.85)
        gate.update(packet(gesture="click"),.95)
        self.assertAlmostEqual(gate.progress,progress)
        gate.update(packet(state="no_hand"),1.)
        self.assertEqual(gate.progress,0)
        self.assertIsNone(gate.update(packet(gesture="click"),1.1))
        self.assertEqual(gate.progress,0)

    def test_root_snap_and_hysteresis_ignore_foliage(self):
        garden=Garden(42)
        a=garden.plant(.3,.5,"fern","first")
        b=garden.plant(.4,.5,"fern","second")
        self.assertEqual(garden.snap_root(.32,.5).id,a.id)
        self.assertEqual(garden.snap_root(.35,.5,a.id).id,a.id)  # Near tie retains target.
        self.assertEqual(garden.snap_root(.39,.5,a.id).id,b.id)
        self.assertIsNone(garden.snap_root(.8,.8,a.id))

    def test_empty_cursor_movement_resets_confirmation(self):
        gate=ClickGate(hold=.6)
        gate.update(packet(state="outside"),0)
        gate.update(packet(state="outside"),.31)
        gate.update(packet(gesture="click",x=.2),.4)
        gate.update(packet(gesture="click",x=.3),.7)
        self.assertIsNone(gate.update(packet(gesture="click",x=.3),1.01))
        self.assertIsNotNone(gate.update(packet(gesture="click",x=.3),1.31))

    def test_udp_click_cultivates_or_plants_at_cursor_and_preserves_drafts(self):
        app=GardenApp(Garden(42),argparse.Namespace(hand_stream=True,hand_click=True,hand_port=0,
                      output="test-output/click-e2e",voice="en-US-AriaNeural"))
        sender=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        seq,tick=0,time.monotonic()
        def frame(state="ok",gesture="click",x=.18,y=.3):
            nonlocal seq,tick
            seq+=1
            tick+=.11
            data=packet(seq,state,gesture,x,y,raw_pose="Thumb_Up" if gesture=="click" else "None")
            sender.sendto(json.dumps(data).encode(),app.hand.socket.getsockname())
            time.sleep(.002)
            with patch("hand_input.time.monotonic",return_value=tick):
                app.poll_hand()
        def release():
            for _ in range(4): frame(state="outside",gesture="unknown")
        def click(x=.18,y=.3):
            for _ in range(22): frame(x=x,y=y)
        try:
            release(); click()
            self.assertEqual(app.pending,(.18,.3))  # Actual cursor, not section center.
            app.insert_text("first visitor"); app.action("water")
            first=app.selected
            release()
            frame(gesture="unknown",x=.225,y=.32)
            self.assertEqual(app.hand_hover,first)
            app.draw()
            click(.225,.32)
            self.assertEqual(app.selected,first)
            self.assertIsNone(app.pending)
            app.insert_text("and another")
            release(); click(.8,.75)
            self.assertEqual(app.selected,first)  # Protected draft cannot migrate.
            app.action("water")
            self.assertEqual(app.garden.get(first).session.words,["first","visitor","and","another"])
            release(); click(.29,.3)
            self.assertEqual(app.pending,(.29,.3))
            app.insert_text("same section"); app.action("water")
            self.assertEqual(len(app.garden.plants),2)  # No one-root-per-section cap.
            app.save()
            app.action("finish")
            before=app.garden.pack()
            release(); click(.8,.75)
            self.assertEqual(app.garden.pack(),before)
            self.assertIsNone(app.pending)
        finally:
            sender.close(); app.hand.close(); app.speech.close(); app.pg.quit()

    def test_batched_tracking_loss_does_not_complete_click(self):
        gate=ClickGate(hold=.6)
        gate.update(packet(state="outside"),0)
        gate.update(packet(state="outside"),.31)
        gate.update(packet(gesture="click"),.4,target_id="A")
        gate.update(packet(gesture="click"),.7,target_id="A")
        gate.update(packet(state="no_hand"),1.01)
        self.assertIsNone(gate.update(packet(gesture="click"),1.01,target_id="A"))


if __name__ == '__main__': unittest.main()
