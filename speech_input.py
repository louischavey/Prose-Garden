"""Bounded speech capture and a warm, loopback whisper.cpp backend."""
from collections import deque
import io
import json
import uuid
import wave
from urllib.request import Request, urlopen


def capture_speech(stream, stop, max_seconds, vad, silence_seconds=.8):
    # WebRTC VAD requires 16-bit mono PCM at a supported rate and frame length.
    frames = deque(maxlen=10)  # 300 ms pre-roll preserves initial consonants.
    chunks = []
    voiced = quiet = 0
    started = False
    for _ in range(max(1, round(max_seconds / .03))):
        if stop.is_set():
            return None
        chunk, overflow = stream.read(480)
        if overflow:
            raise RuntimeError("Microphone overflow. Please try again.")
        chunk = bytes(chunk)
        speech = vad.is_speech(chunk, 16000)
        if not started:
            frames.append(chunk)
            voiced = voiced + 1 if speech else 0
            if voiced >= 3:
                started = True
                chunks.extend(frames)
            continue
        chunks.append(chunk)
        quiet = 0 if speech else quiet + 1
        if quiet * .03 >= silence_seconds:
            break
    if not started:
        raise ValueError("No speech detected. Move closer to the microphone and try again.")
    return b"".join(chunks)


def local_transcribe(pcm, rate, language="en-US", port=8080):
    audio = io.BytesIO()
    with wave.open(audio, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm)
    boundary = "poetree-" + uuid.uuid4().hex
    fields = {"response_format":"json", "language":language.split("-")[0],
              "temperature":"0.0", "temperature_inc":"0.0"}
    body = bytearray()
    for name, value in fields.items():
        body.extend((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n').encode())
    body.extend((f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="speech.wav"\r\nContent-Type: audio/wav\r\n\r\n').encode())
    body.extend(audio.getvalue())
    body.extend((f"\r\n--{boundary}--\r\n").encode())
    request = Request(f"http://127.0.0.1:{port}/inference", data=bytes(body),
                      headers={"Content-Type":f"multipart/form-data; boundary={boundary}"})
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read(1048576))
    except Exception as exc:
        raise RuntimeError("Local transcription unavailable. Check whisper-server in the other Terminal. " + str(exc)) from exc
    text = result.get("text", "").strip()
    if not text:
        raise ValueError("No words recognized. Please try again.")
    return text
