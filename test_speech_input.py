import io
import json
import threading
import unittest
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import Mock
from speech_input import capture_speech, local_transcribe


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

    def test_local_http_contract_contains_valid_wav_and_english(self):
        captured = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                captured.append((self.path, self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'text':' we grow together '}).encode())
            def log_message(self, *args): pass
        with HTTPServer(('127.0.0.1', 0), Handler) as server:
            worker = threading.Thread(target=server.handle_request)
            worker.start()
            result = local_transcribe(b'\0'*3200, 16000, port=server.server_port)
            worker.join(2)
        self.assertEqual(result, 'we grow together')
        path, body = captured[0]
        self.assertEqual(path, '/inference')
        self.assertIn(b'name="language"\r\n\r\nen\r\n', body)
        wav = body[body.index(b'RIFF'):]
        with wave.open(io.BytesIO(wav)) as audio:
            self.assertEqual(audio.getframerate(), 16000)
            self.assertEqual(audio.getnchannels(), 1)
            self.assertEqual(audio.readframes(1600), b'\0'*3200)
