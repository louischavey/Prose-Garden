import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import argparse
import queue
import unittest
from unittest.mock import MagicMock, patch
from garden import Garden, GardenApp, Dictation
from voice_flow import plant_type, command


class FakeDictation:
    def __init__(self):
        self.ticket=0
        self.busy=False
        self.durations=[]
    def cancel(self):
        self.ticket+=1
        self.busy=False
    def start(self,seconds=8):
        self.ticket+=1
        self.busy=True
        self.durations.append(seconds)


class VoiceTests(unittest.TestCase):
    def setUp(self):
        self.app=GardenApp(Garden(42),argparse.Namespace(hand_stream=True,hand_click=True,hand_port=0,
                    voice_input=True,output="test-output/voice-e2e",voice="en-US-AriaNeural"))
        self.app.dictation=FakeDictation()
    def tearDown(self):
        self.app.hand.close()
        self.app.speech.close()
        self.app.pg.quit()
    def listen(self):
        self.app.voice_flow.ready_at=0
        self.app.voice_flow.poll()
        return self.app.dictation.ticket
    def say(self,text):
        ticket=self.listen()
        self.app.dictation.busy=False
        self.app.events.put(("dictation",(ticket,text)))
        self.app.process_messages()

    def test_full_voice_plant_then_cultivate_and_checkpoint(self):
        app=self.app
        app.handle_hand_click(.3,.6)
        self.assertEqual(app.voice_flow.phase,"type")
        self.say("a tree")
        self.assertEqual(app.kind,"conifer")
        self.say("we grow together")
        self.assertEqual(len(app.garden.plants),0)  # Dictation alone never saves.
        app.handle_hand_click(.8,.7)
        self.assertEqual(app.pending,(.3,.6))
        self.say("confirm")
        first=app.selected
        self.assertEqual(app.voice_flow.phase,"idle")
        self.assertEqual(app.garden.get(first).session.words,["we","grow","together"])
        app.handle_hand_click(.31,.6,target_id=first)
        self.assertTrue(app.focus)
        self.assertEqual(app.voice_flow.phase,"words")
        self.say("under shared skies")
        self.say("yes")
        self.assertEqual(app.selected,first)
        self.assertTrue(app.focus)
        self.assertEqual(app.garden.get(first).session.words,["we","grow","together","under","shared","skies"])
        from plant_poem import ROOT
        restored=Garden.load(ROOT/"test-output/voice-e2e.json")
        self.assertEqual(restored.pack(),app.garden.pack())
        app.draw()
        self.assertFalse(any(action in ("water", "mic", "flower", "conifer", "fern")
                             for _, action in app.buttons))
        app.handle_hand_click(.8,.7)
        self.assertIsNone(app.selected)
        self.assertFalse(app.focus)
        self.assertEqual(app.voice_flow.phase,"type")

    def test_retry_cancel_and_commands_are_not_poem_words(self):
        app=self.app
        app.handle_hand_click(.3,.6)
        self.say("flower")
        self.say("wrong phrase")
        app.action("read")
        self.assertTrue(app.voice_flow.active)
        self.assertEqual(app.voice_flow.phase,"confirm")
        self.say("retry")
        self.assertEqual(app.draft,"")
        self.say("correct phrase")
        self.say("cancel")
        self.assertEqual(app.draft,"")
        self.assertIsNone(app.pending)
        self.assertEqual(len(app.garden.plants),0)

    def test_invalid_word_count_and_three_errors_pause_then_pinch_retries(self):
        app=self.app
        app.handle_hand_click(.3,.6)
        self.say("fern")
        self.say("one two three four five six")
        self.assertEqual(app.voice_flow.phase,"words")
        self.assertEqual(app.draft,"")
        for _ in range(2):
            ticket=self.listen()
            app.dictation.busy=False
            app.events.put(("dictation_error",(ticket,"network unavailable")))
            app.process_messages()
        self.assertEqual(app.voice_flow.phase,"error")
        app.handle_hand_click(.8,.8)
        self.assertEqual(app.pending,(.3,.6))
        self.assertEqual(app.voice_flow.phase,"words")

    def test_stale_transcript_cannot_write_to_changed_target(self):
        app=self.app
        app.handle_hand_click(.3,.6)
        self.say("fern")
        ticket=self.listen()
        app.pending=(.8,.7)
        app.dictation.busy=False
        app.events.put(("dictation",(ticket,"old location words")))
        app.process_messages()
        self.assertEqual(app.draft,"")
        self.assertEqual(app.voice_flow.phase,"idle")
        self.assertEqual(len(app.garden.plants),0)

    def test_plant_kind_and_commands_have_narrow_contextual_grammar(self):
        self.assertEqual(plant_type("Plant a tree!"),"conifer")
        self.assertEqual(plant_type("fern"),"fern")
        self.assertIsNone(plant_type("flower and tree"))
        self.assertEqual(command("try again"),"retry")
        self.assertIsNone(command("yes no"))
        app=self.app
        app.handle_hand_click(.3,.6)
        self.say("flower")
        self.say("confirm")  # In words phase this is a poem word, not a command.
        self.assertEqual(app.draft,"confirm")
        self.assertEqual(len(app.garden.plants),0)

    def test_voice_pause_starts_fresh_hold_without_changing_locked_target(self):
        app=self.app
        app.handle_hand_click(.3,.6)
        gate=app.hand_gate
        from test_hand_input import packet
        gate.update(packet(state="outside"),0)
        gate.update(packet(state="outside"),.31)
        gate.latched=True
        for _ in range(3): app.voice_flow.fail("No words")
        self.assertEqual(app.voice_flow.phase,"error")
        self.assertFalse(gate.latched)
        self.assertEqual(gate.progress,0)
        for i in range(23):
            observation=packet(gesture="click",x=.7 if i%2 else .8,y=.8)
            app.hand.batch=[(.4+i*.1,observation)]
            with patch.object(app.hand,"poll",return_value=observation):
                app.poll_hand_click()
            if app.voice_flow.phase != "error":
                break
        self.assertEqual(app.pending,(.3,.6))
        self.assertEqual(app.voice_flow.phase,"type")

    def test_dictation_worker_publishes_result_after_busy_clears(self):
        events=queue.Queue()
        dictation=Dictation(events,device=3,language="en-US")
        stream=MagicMock()
        stream.read.return_value=(b'\0'*3200,False)
        context=MagicMock()
        context.__enter__.return_value=stream
        recognizer=MagicMock()
        recognizer.recognize_google.return_value="flower"
        class ImmediateThread:
            def __init__(self,target,**kwargs): self.target=target
            def start(self): self.target()
        with patch("garden.threading.Thread",ImmediateThread), \
             patch("garden.time.monotonic",side_effect=[0.,0.,5.]), \
             patch("sounddevice.query_devices",return_value={"default_samplerate":16000}) as query, \
             patch("sounddevice.RawInputStream",return_value=context), \
             patch("speech_recognition.Recognizer",return_value=recognizer):
            dictation.start(seconds=4)
        self.assertFalse(dictation.busy)
        query.assert_called_once_with(3,kind="input")
        messages=[]
        while not events.empty(): messages.append(events.get_nowait())
        self.assertIn(("dictation",(dictation.ticket,"flower")),messages)
        self.assertEqual(recognizer.recognize_google.call_args.kwargs["language"],"en-US")


if __name__ == '__main__': unittest.main()
