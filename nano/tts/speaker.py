"""
Text-to-Speech Speaker
=======================
Reference project used MeloTTS (Mac).
This version uses Piper TTS — fast, offline, works on Windows.

Install: pip install piper-tts
Download voice: python -c "from speaker import Speaker; Speaker()"
  → auto-downloads en_US-lessac-medium on first run
"""

import io
import wave
import numpy as np
from pathlib import Path


VOICE_PATH  = "assets/en_US-lessac-medium.onnx"
SAMPLE_RATE = 22050


class Speaker:
    """
    Wraps Piper TTS. Same interface as reference MeloTTS.
    synthesise(text) → (audio_array_float32, sample_rate)
    """

    def __init__(self):
        self._voice = None
        self._load()

    def _load(self):
        voice_path = Path(VOICE_PATH)
        if not voice_path.exists():
            self._download_voice(voice_path)

        try:
            from piper.voice import PiperVoice
            print(f"[TTS] Loading Piper voice from {VOICE_PATH}...")
            self._voice = PiperVoice.load(str(voice_path))
            print("[TTS] Ready.")
        except Exception as e:
            print(f"[TTS] Piper failed ({e}), falling back to pyttsx3")
            self._voice = None

    def _download_voice(self, path: Path):
        import urllib.request
        path.parent.mkdir(parents=True, exist_ok=True)
        base = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
        print("[TTS] Downloading Piper voice (~60MB)...")
        for ext in [".onnx", ".onnx.json"]:
            url  = f"{base}/en_US-lessac-medium{ext}"
            dest = str(path) + (ext if ext != ".onnx" else "")
            urllib.request.urlretrieve(url, dest)
        print("[TTS] Voice downloaded.")

    def synthesise(self, text: str) -> tuple[np.ndarray | None, int]:
        """
        Returns (float32 audio array, sample_rate).
        Returns (None, 0) on failure — caller should skip playback.
        """
        # Remove action tags before speaking
        import re
        clean = re.sub(r'\[.*?\]', '', text).strip()
        if not clean:
            return None, 0

        if self._voice:
            return self._synthesise_piper(clean)
        else:
            return self._synthesise_pyttsx3(clean)

    def _synthesise_piper(self, text: str) -> tuple[np.ndarray, int]:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            self._voice.synthesize(text, wf)
        buf.seek(0)
        with wave.open(buf, "rb") as wf:
            rate   = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        return audio, rate

    def _synthesise_pyttsx3(self, text: str) -> tuple[np.ndarray | None, int]:
        """Fallback TTS using pyttsx3 (speaks directly, no array returned)."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            # Prefer female voice
            for v in voices:
                if "female" in v.name.lower() or "zira" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
            engine.setProperty("rate", 175)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS] pyttsx3 error: {e}")
        return None, 0
