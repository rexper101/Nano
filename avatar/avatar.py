"""
Nano Avatar — Floating Desktop Overlay
========================================
A lightweight always-on-top floating avatar window built with
tkinter — no Godot or Unity required.

Shows:
  - Animated avatar face with emotion states
  - Speaking animation (mouth opens/closes in sync)
  - Status text (Listening / Thinking / Speaking / Idle)
  - Subtle idle breathing animation

Run standalone: python avatar/avatar.py
Or import and call: AvatarWindow().start_in_thread()
"""

import tkinter as tk
import threading
import math
import time
import queue


# ── Emotion colour themes ─────────────────────────────────────────────────────
THEMES = {
    "idle":      {"bg": "#0a0e1a", "ring": "#00e5c8", "text": "#00e5c8",  "label": "IDLE"},
    "listening": {"bg": "#0a0e1a", "ring": "#1a8fff", "text": "#1a8fff",  "label": "LISTENING"},
    "thinking":  {"bg": "#0a0e1a", "ring": "#ffb930", "text": "#ffb930",  "label": "THINKING"},
    "speaking":  {"bg": "#0a0e1a", "ring": "#00e5c8", "text": "#00e5c8",  "label": "SPEAKING"},
    "happy":     {"bg": "#0a1a0e", "ring": "#00e87a", "text": "#00e87a",  "label": "HAPPY"},
    "error":     {"bg": "#1a0a0e", "ring": "#ff4050", "text": "#ff4050",  "label": "ERROR"},
}

# Mouth shapes for speaking animation (open level 0-10)
MOUTH_SHAPES = [0, 2, 5, 8, 10, 8, 5, 2, 0, 0, 0, 2]

W, H = 200, 240   # window size


class AvatarWindow:
    def __init__(self):
        self.root         = None
        self.canvas       = None
        self.state        = "idle"
        self._cmd_queue   = queue.Queue()
        self._tick        = 0
        self._mouth_idx   = 0
        self._speaking    = False
        self._blink       = False
        self._blink_timer = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def set_state(self, state: str):
        """Set emotion state: idle | listening | thinking | speaking | happy | error"""
        self._cmd_queue.put(("state", state))

    def start_speaking(self):
        self._cmd_queue.put(("speak", True))

    def stop_speaking(self):
        self._cmd_queue.put(("speak", False))

    def start_in_thread(self):
        """Run the avatar window in a background daemon thread."""
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        time.sleep(0.5)   # give tkinter time to boot
        return t

    # ── Tkinter main loop ─────────────────────────────────────────────────────

    def _run(self):
        self.root   = tk.Tk()
        self.canvas = tk.Canvas(
            self.root,
            width=W, height=H,
            bg="#0a0e1a", highlightthickness=0,
        )
        self.canvas.pack()

        # Window setup — borderless, always on top, bottom-right corner
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.root.configure(bg="#0a0e1a")

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{W}x{H}+{sw - W - 20}+{sh - H - 60}")

        # Make window draggable
        self.canvas.bind("<ButtonPress-1>",   self._drag_start)
        self.canvas.bind("<B1-Motion>",       self._drag_motion)

        self._animate()
        self.root.mainloop()

    def _animate(self):
        """Called every 80ms — draws the full avatar frame."""
        try:
            while not self._cmd_queue.empty():
                cmd, val = self._cmd_queue.get_nowait()
                if cmd == "state":
                    self.state = val
                elif cmd == "speak":
                    self._speaking = val

            self._draw_frame()
            self._tick += 1

            # Blink every ~4 seconds
            self._blink_timer += 80
            if self._blink_timer > 4000:
                self._blink       = True
                self._blink_timer = 0
            elif self._blink:
                time.sleep(0.08)
                self._blink = False

        except Exception:
            pass

        if self.root:
            self.root.after(80, self._animate)

   