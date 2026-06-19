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

    def _draw_frame(self):
        c     = self.canvas
        theme = THEMES.get(self.state, THEMES["idle"])
        ring  = theme["ring"]
        bg    = theme["bg"]
        cx, cy = W // 2, 100   # face centre

        c.delete("all")

        # Background
        c.create_rectangle(0, 0, W, H, fill=bg, outline="")

        # Outer glow ring (animated rotation)
        angle = self._tick * 3
        r1, r2 = 72, 76
        for i in range(0, 360, 15):
            a  = math.radians(i + angle)
            a2 = math.radians(i + angle + 12)
            alpha = abs(math.sin(math.radians(i + angle))) * 0.8 + 0.2
            # Approximate glow with arc
            c.create_arc(
                cx - r2, cy - r2, cx + r2, cy + r2,
                start=i + angle, extent=10,
                outline=ring, width=2, style=tk.ARC,
            )

        # Face circle
        r = 62
        c.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#111827", outline=ring, width=1.5)

        # Eyes
        ey = cy - 14
        eye_h = 2 if self._blink else 10
        for ex in [cx - 18, cx + 18]:
            c.create_oval(ex-9, ey-eye_h//2, ex+9, ey+eye_h//2,
                          fill=ring, outline="")
            if not self._blink:
                # Pupil
                c.create_oval(ex-4, ey-4, ex+4, ey+4, fill="#0a0e1a", outline="")
                # Highlight
                c.create_oval(ex+2, ey-5, ex+6, ey-2, fill="white", outline="")

        # Thinking animation — eyebrow raise
        if self.state == "thinking":
            brow_y = ey - 16 - int(3 * math.sin(math.radians(self._tick * 8)))
            for ex in [cx - 18, cx + 18]:
                c.create_line(ex-9, brow_y, ex+9, brow_y, fill=ring, width=2)

        # Nose
        c.create_line(cx, cy + 2, cx - 4, cy + 10, cx + 4, cy + 10,
                      fill=ring, width=1, smooth=True)

        # Mouth — idle smile or speaking animation
        my = cy + 20
        if self._speaking:
            mo = MOUTH_SHAPES[self._mouth_idx % len(MOUTH_SHAPES)]
            self._mouth_idx += 1
            # Open mouth
            c.create_oval(cx-14, my, cx+14, my+mo+4,
                          fill="#1a0a2a", outline=ring, width=1.5)
            # Teeth
            if mo > 3:
                c.create_rectangle(cx-10, my+1, cx+10, my+4, fill="white", outline="")
        else:
            # Smile
            smile_y = 3 if self.state == "happy" else 0
            c.create_arc(cx-16, my-4, cx+16, my+8+smile_y,
                         start=200, extent=140,
                         outline=ring, width=2, style=tk.ARC)

        # Idle breathing — subtle body bob
        bob = int(2 * math.sin(math.radians(self._tick * 4)))

        # Neck
        c.create_rectangle(cx-8, cy+r+bob, cx+8, cy+r+18+bob,
                           fill="#1a2035", outline="")

        # Shoulders
        c.create_oval(cx-48, cy+r+10+bob, cx+48, cy+r+50+bob,
                      fill="#1a2035", outline=ring, width=1)

        # Collar detail
        c.create_line(cx, cy+r+18+bob, cx-20, cy+r+35+bob, fill=ring, width=1)
        c.create_line(cx, cy+r+18+bob, cx+20, cy+r+35+bob, fill=ring, width=1)

        # Status label
        c.create_text(W//2, H-36,
                      text=theme["label"],
                      fill=ring,
                      font=("Courier New", 9, "bold"))

        # Name
        c.create_text(W//2, H-18,
                      text="NANO",
                      fill=ring,
                      font=("Courier New", 11, "bold"))

        # Corner accent lines
        for x1, y1, x2, y2 in [(0,0,20,0),(0,0,0,20),(W,0,W-20,0),(W,0,W,20),
                                 (0,H,20,H),(0,H,0,H-20),(W,H,W-20,H),(W,H,W,H-20)]:
            c.create_line(x1, y1, x2, y2, fill=ring, width=1)

    # ── Drag support ──────────────────────────────────────────────────────────
    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_motion(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x  = self.root.winfo_x() + dx
        y  = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    avatar = AvatarWindow()
    t      = avatar.start_in_thread()

    print("Avatar running. Press Ctrl+C to quit.")
    print("Testing states:")
    states = ["idle","listening","thinking","speaking","happy","error","idle"]
    try:
        for state in states:
            print(f"  → {state}")
            avatar.set_state(state)
            if state == "speaking":
                avatar.start_speaking()
            else:
                avatar.stop_speaking()
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    print("Done.")
