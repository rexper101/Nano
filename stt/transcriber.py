"""
Speech-to-Text Transcriber
===========================
Reference project used mlx-whisper (Mac only).
This version uses faster-whisper which works on Windows + NVIDIA GPU.

Install: pip install faster-whisper
"""

import numpy as np


class Transcriber:
    """
    Wraps faster-whisper. Same interface as the reference FastTranscriber.
    transcribe(audio_array) → {"text": "..."}
    """

    MODEL_SIZE  = "small"   # tiny | base | small | medium | large-v3
    DEVICE      = "auto"    # auto | cuda | cpu
    COMPUTE     = "auto"    # auto | float16 | int8

    def __init__(self):
        from faster_whisper import WhisperModel
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute = "float16" if device == "cuda" else "int8"

        print(f"[STT] Loading Whisper {self.MODEL_SIZE} on {device}...")
        self.model = WhisperModel(
            self.MODEL_SIZE,
            device=device,
            compute_type=compute,
        )
        print("[STT] Ready.")

    def transcribe(self, audio: np.ndarray, language: str = "en") -> dict:
        """
        audio: 16kHz int16 numpy array (same format as reference project)
        Returns: {"text": "transcribed string"}
        """
        # Convert int16 → float32 normalised
        audio_f32 = audio.astype(np.float32) / 32768.0

        segments, _ = self.model.transcribe(
            audio_f32,
            language=language,
            beam_size=5,
            vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return {"text": text}
