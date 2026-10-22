import threading
import unittest
from unittest.mock import Mock
from speech_input import capture_speech


class SpeechInputTests(unittest.TestCase):
    def stream(self):
        stream = Mock()
        stream.read.return_value = (b"\0" * 960, False)
        return stream

    def test_speech_ends_after_silence_before_cap(self):
        stream = self.stream()
        vad = Mock()
        vad.is_speech.side_effect = [False]*5 + [True]*10 + [False]*27
        pcm = capture_speech(stream, threading.Event(), 7, vad)
        self.assertEqual(stream.read.call_count, 42)
        self.assertGreater(len(pcm), 960*10)
        self.assertLess(stream.read.call_count, 7/.03)

    def test_silence_never_sent_to_recognizer(self):
        vad = Mock()
        vad.is_speech.return_value = False
        with self.assertRaisesRegex(ValueError, "No speech"):
            capture_speech(self.stream(), threading.Event(), .3, vad)

    def test_continuous_noise_is_bounded_and_cancel_stops_capture(self):
        vad = Mock()
        vad.is_speech.return_value = True
        stream = self.stream()
        capture_speech(stream, threading.Event(), .3, vad)
        self.assertEqual(stream.read.call_count, 10)
        stop = threading.Event()
        stop.set()
        self.assertIsNone(capture_speech(stream, stop, 7, vad))
        self.assertEqual(stream.read.call_count, 10)

