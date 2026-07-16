"""
Screen Tool
============
Takes a screenshot and answers questions about it using LLaVA vision model.
Also reads text from the screen using OCR.

Examples:
  "what's on my screen"
  "read the error on screen"
  "what does this error mean"
  "take a screenshot"
  "read the text on screen"
"""

import re
import base64
import time
import httpx
from pathlib import Path
from datetime import datetime


OLLAMA_URL    = "http://localhost:11434/api/chat"
VISION_MODEL  = "llava:7b"
SCREENSHOT_DIR = Path("data/screenshots")


class ScreenTool:
    def run(self, user_text: str) -> str:
        text = user_text.lower()

        if any(w in text for w in ["screenshot", "take a screenshot", "capture screen"]):
            return self._take_screenshot()

        if any(w in text for w in ["read", "ocr", "text on screen", "what does it say"]):
            return self._read_screen()

        # Default: describe the screen
        return self._describe_screen(user_text)

    def _capture(self) -> tuple[str, Path]:
        """Capture screen and return (base64_string, saved_path)."""
        try:
            import mss
            from PIL import Image
            import io

            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = SCREENSHOT_DIR / f"screen_{ts}.png"

            with mss.mss() as sct:
                raw = sct.grab(sct.monitors[1])
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                # Resize to 1280px wide to reduce tokens
                w, h = img.size
                if w > 1280:
                    img = img.resize((1280, int(h * 1280 / w)))
                img.save(str(path))

            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()

            return b64, path

        except ImportError as e:
            return "", Path("")

    def _describe_screen(self, question: str) -> str:
        """Ask LLaVA what's on the screen."""
        b64, path = self._capture()
        if not b64:
            return "Could not capture screen. Install mss: pip install mss Pillow"

        try:
            resp = httpx.post(
                OLLAMA_URL,
                json={
                    "model": VISION_MODEL,
                    "messages": [{
                        "role":    "user",
                        "content": question or "Describe what is on this screen. Be concise.",
                        "images":  [b64],
                    }],
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 300},
                },
                timeout=60.0,
            )
            answer = resp.json()["message"]["content"].strip()
            return answer

        except httpx.ConnectError:
            return "LLaVA not available. Pull it with: ollama pull llava:7b"
        except Exception as e:
            return f"Screen analysis failed: {e}"

    def _read_screen(self) -> str:
        """Extract text from screen using OCR."""
        try:
            import easyocr
            import numpy as np
            from PIL import Image

            _, path = self._capture()
            if not path.exists():
                return "Could not capture screen."

            reader = easyocr.Reader(["en"], gpu=False)
            img    = np.array(Image.open(path))
            result = reader.readtext(img)
            text   = " ".join(r[1] for r in result if r[2] > 0.3)
            return text[:600] if text else "No readable text found on screen."

        except ImportError:
            # Fallback to vision model for text reading
            return self._describe_screen("Read and list all the text you can see on this screen.")

    def _take_screenshot(self) -> str:
        """Just save the screenshot and confirm."""
        _, path = self._capture()
        if path.exists():
            import os
            os.startfile(str(path.parent))
            return f"Screenshot saved to {path}"
        return "Could not take screenshot. Install mss: pip install mss"
