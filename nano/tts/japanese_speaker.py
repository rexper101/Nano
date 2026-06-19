"""
Japanese-Accent English TTS
=============================
Uses Microsoft Edge TTS (free, no API key) with the Japanese
female voice speaking English — gives that natural Japanese accent.

Voice: ja-JP-NanamiNeural — Japanese female, speaks English with
       a natural Japanese accent and feminine tone.

Fallback chain:
  1. edge-tts  (Japanese accent, online)
  2. Piper TTS (offline, English)
  3. pyttsx3   (offline, basic)

Install: pip install edge-tts
"""

import io
import asyncio
import re
import wave
import numpy as np
import tempfile
import os
from pathlib import Path


# Japanese female voices that speak English with natural accent
JAPANESE_VOICES = [
    "ja-JP-NanamiNeural",     # Best: warm, natural Japanese girl voice
    "ja-JP-AoiNeural",        # Alternative: slightly younger sounding
    "zh-CN-XiaoxiaoNeural",   # Fallback: Chinese girl voice (similar accent)
]

# Speaking style modifiers for more natural anime-girl speech
SSML_TEMPLATE = """<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis'
       xmlns:mstts='http://www.w3.org/2001/mstts'
       xml:lang='en-US'>
  <voice name='{voice}'>
    <mstts:express-as style='cheerful' styledegree='1.2'>
      <prosody rate='+5%' pitch='+8%'>
        {text}
      </prosody>
    </mstts:express-as>
  </voice>
</speak>"""


class JapaneseTTSSpeaker:
    """
    TTS with Japanese-accent English voice.
    synthesise(text) → (float32_audio_array, sample_rate)
    """

    def __init__(self):
        self._voice        = JAPANESE_VOICES[0]
        self._edge_ok      = self._check_edge_tts()
        self._piper_ok     = False
        self._piper_voice  = None

        if self._edge_ok:
            print(f"[TTS] Edge TTS ready — voice: {self._voice}")
        else:
            print("[TTS] Edge TTS not available — loading Piper fallback...")
            self._load_piper()

    def _check_edge_tts(self) -> bool:
        try:
            import edge_tts
            return True
        except ImportError:
            return False

    def _load_piper(self):
        voice_path = Path("assets/en_US-lessac-medium.onnx")
        if voice_path.exists():
            try:
                from piper.voice import PiperVoice
                self._piper_voice = PiperVoice.load(str(voice_path))
                self._piper_ok    = True
                print("[TTS] Piper fallback loaded.")
            except Exception:
                pass

    # ── Main interface ────────────────────────────────────────────────────────

    def synthesise(self, text: str) -> tuple[np.ndarray | None, int]:
        """
        Returns (float32_audio, sample_rate).
        Returns (None, 0) if all TTS methods fail.
        """
        clean = self._clean(text)
        if not clean:
            return None, 0

        if self._edge_ok:
            result = self._synth_edge(clean)
            if result[0] is not None:
                return result

        if self._piper_ok and self._piper_voice:
            return self._synth_piper(clean)

        return self._synth_pyttsx3(clean)

    # ── Edge TTS (Japanese voice) ─────────────────────────────────────────────

    def _synth_edge(self, text: str) -> tuple[np.ndarray | None, int]:
        try:
            import edge_tts

            async def _run():
                communicate = edge_tts.Communicate(
                    text,
                    voice=self._voice,
                    rate="+5%",
                    # pitch not set — causes issues on some systems
                )
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                return audio_data

            # Windows needs a fresh event loop — always create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                audio_bytes = loop.run_until_complete(_run())
            finally:
                loop.close()

            if not audio_bytes:
                return None, 0

            return self._mp3_to_array(audio_bytes)

        except Exception as e:
            print(f"[TTS] Edge TTS error: {e}")
            return None, 0

    def _mp3_to_array(self, mp3_bytes: bytes) -> tuple[np.ndarray | None, int]:
        """Convert MP3 bytes to float32 numpy array."""
        try:
            # Try pydub first
            from pydub import AudioSegment
            seg   = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
            seg   = seg.set_channels(1).set_frame_rate(22050)
            raw   = np.array(seg.get_array_of_samples(), dtype=np.int16)
            audio = raw.astype(np.float32) / 32768.0
            return audio, 22050
        except ImportError:
            pass

        try:
            # Try soundfile
            import soundfile as sf
            audio, rate = sf.read(io.BytesIO(mp3_bytes))
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            return audio.astype(np.float32), rate
        except Exception:
            pass

        # Save to temp file and use wave
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(mp3_bytes)
                tmp = f.name
            import subprocess
            wav_tmp = tmp.replace(".mp3", ".wav")
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp, "-ar", "22050", "-ac", "1", wav_tmp],
                capture_output=True, timeout=10
            )
            os.unlink(tmp)
            with wave.open(wav_tmp, "rb") as wf:
                rate   = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
            os.unlink(wav_tmp)
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            return audio, rate
        except Exception as e:
            print(f"[TTS] MP3 decode failed: {e}")
            return None, 0

    # ── Piper fallback ────────────────────────────────────────────────────────

    def _synth_piper(self, text: str) -> tuple[np.ndarray, int]:
        try:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                self._piper_voice.synthesize(text, wf)
            buf.seek(0)
            with wave.open(buf, "rb") as wf:
                rate   = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            return audio, rate
        except Exception as e:
            print(f"[TTS] Piper error: {e}")
            return None, 0

    # ── pyttsx3 fallback ─────────────────────────────────────────────────────

    def _synth_pyttsx3(self, text: str) -> tuple[None, int]:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            # Select female voice (Zira on Windows)
            for v in engine.getProperty("voices"):
                if any(x in v.name.lower() for x in ["zira","hazel","female","helen"]):
                    engine.setProperty("voice", v.id)
                    break
            engine.setProperty("rate", 160)
            # NOTE: pitch is not supported on Windows SAPI5 — skip it
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS] pyttsx3 error: {e}")
        return None, 0

    # ── Text cleaning ─────────────────────────────────────────────────────────

    def _clean(self, text: str) -> str:
        """Remove action tags, markdown, emoji from spoken text."""
        text = re.sub(r"\[.*?\]", "", text)        # [Action] tags
        text = re.sub(r"\*\*?.*?\*\*?", "", text)  # **bold**
        text = re.sub(r"`[^`]+`", "", text)        # `code`
        text = re.sub(r"https?://\S+", "the link", text)
        text = text.strip()
        return text
