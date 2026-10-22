"""Bounded microphone capture with WebRTC speech detection."""
from collections import deque


def capture_speech(stream, stop, max_seconds, vad, silence_seconds=1.4, wait_seconds=8.):
    # WebRTC VAD requires 16-bit mono PCM at a supported rate and frame length.
    frames = deque(maxlen=10)  # 300 ms pre-roll preserves initial consonants.
    chunks = []
    voiced = quiet = 0
    started = False
    speech_frames = 0
    wait_frames = max(1, round(wait_seconds/.03))
    max_frames = max(3, round(max_seconds/.03))
    for index in range(wait_frames + max_frames):
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
                speech_frames = voiced
            elif index+1 >= wait_frames:
                break
            continue
        chunks.append(chunk)
        speech_frames += 1
        quiet = 0 if speech else quiet + 1
        if quiet * .03 >= silence_seconds or speech_frames >= max_frames:
            break
    if not started:
        raise ValueError("No speech detected. Move closer to the microphone and try again.")
    return b"".join(chunks)

