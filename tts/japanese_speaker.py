"""
Nano TTS — English Female Voice (Python 3.11 compatible)
=========================================================
Fixes:
  - No pydub (audioop broken in Python 3.11+)
  - Uses soundfile or ffmpeg for MP3 decoding
  - Falls back cleanly to pyttsx3 Windows voice

Voice priority:
  1. edge-tts  en-US-AvaNeural   (warm American female, online)
  2. edge-tts  en-US-JennyNeural (fallback online)
  3. pyttsx3   Zira              (Windows built-in, always works)

Install:
    pip install edge-tts soundfile
"""

import io
import re
import wave
import asyncio
import tempfile
import os
import numpy as np
from pathlib import Path


ENGLISH_VOICES = [
    "en-US-AvaNeural",
    "en-US-JennyNeural",
    "en-GB-SoniaNeural",
]


class JapaneseTTSSpeaker:
    def __init__(self):
        self._voice   = ENGLISH_VOICES[0]
        self._edge_ok = self._check_edge()
        if self._edge_ok:
            print(f"[TTS] Edge TTS ready — {self._voice}")
        else:
            print("[TTS] Using Windows built-in voice (pyttsx3)")

    def _check_edge(self) -> bool:
        try:
            import edge_tts  # noqa
            return True
        except ImportError:
            return False

    # ── Main interface ────────────────────────────────────────────────────

    def synthesise(self, text: str) -> tuple:
        clean = self._clean(text)
        if not clean:
            return None, 0

        if self._edge_ok:
            result = self._edge(clean)
            if result[0] is not None:
                return result

        self._pyttsx3(clean)
        return None, 0

    # ── Edge TTS ─────────────────────────────────────────────────────────

    def _edge(self, text: str) -> tuple:
        try:
            import edge_tts

            async def _run():
                com = edge_tts.Communicate(text, voice=self._voice, rate="+0%")
                buf = b""
                async for chunk in com.stream():
                    if chunk["type"] == "audio":
                        buf += chunk["data"]
                return buf

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                mp3 = loop.run_until_complete(_run())
            finally:
                loop.close()

            if not mp3:
                return None, 0

            return self._decode_mp3(mp3)

        except Exception as e:
            print(f"[TTS] Edge TTS error: {e}")
            return None, 0

    def _decode_mp3(self, mp3_bytes: bytes) -> tuple:
        """
        Convert MP3 bytes to float32 numpy array.
        Tries 3 methods — no pydub needed.
        """

        # ── Method 1: soundfile (best, no audioop) ───────────────────────
        try:
            import soundfile as sf
            audio, rate = sf.read(io.BytesIO(mp3_bytes))
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            return audio.astype(np.float32), int(rate)
        except Exception:
            pass

        # ── Method 2: ffmpeg via temp file ───────────────────────────────
        try:
            import subprocess
            tmp_mp3 = tempfile.mktemp(suffix=".mp3")
            tmp_wav = tempfile.mktemp(suffix=".wav")
            with open(tmp_mp3, "wb") as f:
                f.write(mp3_bytes)
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_mp3,
                 "-ar", "22050", "-ac", "1", tmp_wav],
                capture_output=True, timeout=10
            )
            if Path(tmp_wav).exists():
                with wave.open(tmp_wav, "rb") as wf:
                    rate   = wf.getframerate()
                    frames = wf.readframes(wf.getnframes())
                os.unlink(tmp_mp3)
                os.unlink(tmp_wav)
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                return audio, rate
        except Exception:
            pass

        # ── Method 3: audioop-lts (if installed) ─────────────────────────
        try:
            import audioop
            from pydub import AudioSegment
            seg   = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
            seg   = seg.set_channels(1).set_frame_rate(22050)
            raw   = bytes(seg.raw_data)
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            return audio, 22050
        except Exception:
            pass

        print("[TTS] MP3 decode failed — falling back to pyttsx3")
        return None, 0

    # ── pyttsx3 fallback ─────────────────────────────────────────────────

    def _pyttsx3(self, text: str):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            for v in voices:
                if any(x in v.name.lower() for x in ["zira","hazel","female","eva"]):
                    engine.setProperty("voice", v.id)
                    break
            engine.setProperty("rate",   165)
            engine.setProperty("volume", 1.0)
            # Do NOT set pitch — not supported on Windows SAPI5
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS] pyttsx3 error: {e}")

    # ── Text cleaning ─────────────────────────────────────────────────────

    def _clean(self, text: str) -> str:
        text = re.sub(r"\[.*?\]",        "",        text)
        text = re.sub(r"\*\*?(.*?)\*\*?",r"\1",     text)
        text = re.sub(r"`[^`]+`",        "",        text)
        text = re.sub(r"https?://\S+",   "the link",text)
        text = re.sub(r"<[^>]+>",        "",        text)
        text = re.sub(r"⚡.*",            "",        text)  # remove action result
        text = re.sub(r"\s+",            " ",       text).strip()
        return text if len(text) > 2 else ""