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


