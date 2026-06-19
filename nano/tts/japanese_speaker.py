"""
Nano TTS — English Female Voice
=================================
Priority order:
  1. edge-tts  → en-US-AvaNeural   (warm American female, online)
  2. edge-tts  → en-GB-SoniaNeural (British female, online)
  3. pyttsx3   → Zira / Hazel      (Windows built-in, offline, instant)

All voices speak ENGLISH only — clean, clear, no accent issues.

Install edge-tts once:
    pip install edge-tts
"""

import io
import re
import wave
import asyncio
import tempfile
import os
import numpy as np


# Best English female voices via Edge TTS (free, no API key)
ENGLISH_VOICES = [
    "en-US-AvaNeural",       # warm, natural American female — best pick
    "en-US-JennyNeural",     # friendly American female
    "en-GB-SoniaNeural",     # clear British female
    "en-AU-NatashaNeural",   # Australian female
]


class JapaneseTTSSpeaker:          # keep class name so imports don't break
    """
    Speaks in clear English using Edge TTS or Windows built-in TTS.
    """

    def __init__(self):
        self._voice    = ENGLISH_VOICES[0]
        self._edge_ok  = self._check_edge()
        if self._edge_ok:
            print(f"[TTS] Edge TTS ready — voice: {self._voice}")
        else:
            print("[TTS] Using Windows built-in TTS (pyttsx3)")

    def _check_edge(self) -> bool:
        try:
            import edge_tts          # noqa: F401
            return True
        except ImportError:
            return False

    # ── Public interface ──────────────────────────────────────────────────

    def synthesise(self, text: str) -> tuple:
        """
        Returns (float32_audio_array, sample_rate).
        Returns (None, 0) if TTS should be skipped.
        """
        clean = self._clean(text)
        if not clean:
            return None, 0

        if self._edge_ok:
            result = self._edge(clean)
            if result[0] is not None:
                return result

        # Fallback — pyttsx3 speaks directly (returns None, 0)
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

            # Always create a fresh event loop on Windows
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                mp3 = loop.run_until_complete(_run())
            finally:
                loop.close()

            if not mp3:
                return None, 0

            return self._mp3_to_array(mp3)

        except Exception as e:
            print(f"[TTS] Edge TTS error: {e}")
            # Try next voice
            idx = ENGLISH_VOICES.index(self._voice) if self._voice in ENGLISH_VOICES else 0
            if idx + 1 < len(ENGLISH_VOICES):
                self._voice = ENGLISH_VOICES[idx + 1]
                print(f"[TTS] Trying fallback voice: {self._voice}")
                return self._edge(text)
            return None, 0

    def _mp3_to_array(self, mp3_bytes: bytes) -> tuple:
        """Convert MP3 bytes → float32 numpy array."""

        # Method 1: pydub (best quality)
        try:
            from pydub import AudioSegment
            seg   = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
            seg   = seg.set_channels(1).set_frame_rate(22050)
            raw   = np.array(seg.get_array_of_samples(), dtype=np.int16)
            return raw.astype(np.float32) / 32768.0, 22050
        except Exception:
            pass

        # Method 2: soundfile
        try:
            import soundfile as sf
            audio, rate = sf.read(io.BytesIO(mp3_bytes))
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            return audio.astype(np.float32), rate
        except Exception:
            pass

        # Method 3: ffmpeg via temp file
        try:
            import subprocess
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(mp3_bytes)
                tmp_mp3 = f.name
            tmp_wav = tmp_mp3.replace(".mp3", ".wav")
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_mp3, "-ar", "22050", "-ac", "1", tmp_wav],
                capture_output=True, timeout=10
            )
            os.unlink(tmp_mp3)
            with wave.open(tmp_wav, "rb") as wf:
                rate   = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
            os.unlink(tmp_wav)
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            return audio, rate
        except Exception as e:
            print(f"[TTS] MP3 decode failed: {e}")
            return None, 0

    # ── pyttsx3 fallback (Windows built-in, speaks directly) ─────────────

    def _pyttsx3(self, text: str):
        try:
            import pyttsx3
            engine = pyttsx3.init()

            # Pick best female voice
            voices = engine.getProperty("voices")
            chosen = None
            # Priority: Zira (US female) > Hazel (UK female) > any female
            for priority in ["zira", "hazel", "female", "woman"]:
                for v in voices:
                    if priority in v.name.lower():
                        chosen = v.id
                        break
                if chosen:
                    break

            if chosen:
                engine.setProperty("voice", chosen)

            engine.setProperty("rate",   165)    # natural speaking speed
            engine.setProperty("volume", 1.0)
            # NOTE: do NOT set pitch — not supported on Windows SAPI5
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS] pyttsx3 error: {e}")

    # ── Text cleaning ─────────────────────────────────────────────────────

    def _clean(self, text: str) -> str:
        """Strip action tags, markdown, URLs before speaking."""
        text = re.sub(r"\[.*?\]",     "",        text)   # [Action] tags
        text = re.sub(r"\*\*?(.*?)\*\*?", r"\1", text)  # **bold**
        text = re.sub(r"`[^`]+`",     "",        text)   # `code`
        text = re.sub(r"https?://\S+","the link",text)   # URLs
        text = re.sub(r"<br>",        " ",       text)   # HTML breaks
        text = re.sub(r"<[^>]+>",     "",        text)   # any HTML tags
        text = re.sub(r"\s+",         " ",       text).strip()
        # Don't speak if it's just a code block or action result
        if len(text) < 3:
            return ""
        return text