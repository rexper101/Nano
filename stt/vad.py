"""
Voice Activity Detection
========================
Direct port of the reference project's VADDetector.
Works on Windows with PyAudio + webrtcvad.
"""

import time
import collections
import numpy as np
import pyaudio
import webrtcvad

RATE     = 16000
CHUNK    = 160       # 10ms frames required by webrtcvad
CHANNELS = 1
FORMAT   = pyaudio.paInt16


class VADDetector:
    """
    Listens to the microphone and fires on_speech_end(audio_array)
    when the user finishes speaking. Identical logic to the reference project.
    """

    def __init__(self, on_speech_start, on_speech_end, sensitivity: float = 0.3):
        self.on_speech_start = on_speech_start
        self.on_speech_end   = on_speech_end
        self.sensitivity     = sensitivity   # seconds of silence before firing

        self.vad = webrtcvad.Vad()
        self.vad.set_mode(3)                 # most aggressive filtering

        self.voiced_frames          = collections.deque(maxlen=1000)
        self.frame_history          = [False]
        self.blocks_since_last_spoke = 0
        self.interval_ms            = 10
        self.sample_rate            = RATE

        self._audio = pyaudio.PyAudio()

    def _is_speech(self, raw_bytes: bytes) -> bool:
        try:
            return self.vad.is_speech(raw_bytes, self.sample_rate)
        except Exception:
            return False

    def _audio_callback(self, raw: bytes):
        detected = self._is_speech(raw)
        arr      = np.frombuffer(raw, dtype=np.int16)

        if self.frame_history[-1] and detected:
            self.on_speech_start()
            self.voiced_frames.append(arr)
            self.blocks_since_last_spoke = 0
        else:
            silence_threshold = int(
                self.sensitivity * 10 * self.interval_ms
            )
            if self.blocks_since_last_spoke == silence_threshold:
                if len(self.voiced_frames) > 0:
                    combined = np.concatenate(list(self.voiced_frames))
                    self.on_speech_end(combined)
                self.voiced_frames.clear()
            else:
                if len(self.voiced_frames) > 0:
                    self.voiced_frames.append(arr)
            self.blocks_since_last_spoke += 1

        self.frame_history.append(detected)
        if len(self.frame_history) > 50:
            self.frame_history = self.frame_history[-50:]

    def start(self):
        """Blocking loop — run in a background thread."""
        stream = self._audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )
        print("[VAD] Microphone open.")
        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                self._audio_callback(data)
            except Exception as e:
                print(f"[VAD] Error: {e}")
                break
