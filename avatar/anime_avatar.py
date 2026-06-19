"""
Nano — 2D Anime Girl Avatar
=============================
A fully animated 2D anime-style avatar rendered with tkinter + canvas.
No external images needed — drawn entirely in Python using geometric shapes.

Features:
  - Large expressive anime eyes with highlights
  - Long hair with gradient layers
  - Facial expressions: idle, happy, thinking, speaking, error
  - Blinking animation
  - Mouth lip-sync animation
  - Hair bounce on speaking
  - Floating idle animation (subtle up/down)
  - Glowing aura ring that changes colour per emotion
  - Cat ears (optional — enabled by default for kawaii factor)
  - School uniform / futuristic outfit
"""

import tkinter as tk
import threading
import math
import time
import queue
import random

# ── Window dimensions ─────────────────────────────────────────────────────────
W, H = 260, 380
CX   = W // 2      # center x
FY   = 155         # face center y

# ── Emotion colour palettes ───────────────────────────────────────────────────
EMOTIONS = {
    "idle":      {"aura": "#00e5c8", "hair": "#7c4dff", "eye": "#00e5c8",
                  "cheek": "", "label": "IDLE",      "bg": "#05080f"},
    "listening": {"aura": "#1a8fff", "hair": "#7c4dff", "eye": "#1a8fff",
                  "cheek": "", "label": "LISTENING", "bg": "#05080f"},
    "thinking":  {"aura": "#ffb930", "hair": "#7c4dff", "eye": "#ffb930",
                  "cheek": "#ff6eb4", "label": "THINKING",  "bg": "#05080f"},
    "speaking":  {"aura": "#00e5c8", "hair": "#7c4dff", "eye": "#00e5c8",
                  "cheek": "#ff6eb4", "label": "SPEAKING",  "bg": "#05080f"},
    "happy":     {"aura": "#00e87a", "hair": "#7c4dff", "eye": "#00e87a",
                  "cheek": "#ff8fab", "label": "HAPPY",     "bg": "#050f08"},
    "error":     {"aura": "#ff4050", "hair": "#7c4dff", "eye": "#ff4050",
                  "cheek": "", "label": "ERROR",     "bg": "#0f0508"},
}

# Viseme mouth open levels for speaking (0=closed, 10=wide open)
MOUTH_SEQ = [0, 1, 3, 6, 8, 9, 8, 6, 3, 1, 0, 0, 0, 2, 5, 7, 5, 2, 0]


class AnimeAvatarWindow:
    """
    Floating always-on-top anime girl avatar.
    Controlled via set_state() and start/stop_speaking().
    """

    def __init__(self):
        self.root      = None
        self.canvas    = None
        self.state     = "idle"
        self._queue    = queue.Queue()
        self._tick     = 0
        self._speaking = False
        self._mouth_i  = 0
        self._blink    = False
        self._blink_t  = random.randint(150, 300)  # ticks until next blink
        self._hair_bob = 0.0     # hair animation phase
        self._float_y  = 0.0    # idle floating offset

    # ── Public API ────────────────────────────────────────────────────────────

    def set_state(self, state: str):
        self._queue.put(("state", state))

    def start_speaking(self):
        self._queue.put(("speak", True))

    def stop_speaking(self):
        self._queue.put(("speak", False))

    def start_in_thread(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        time.sleep(0.8)
        return t

    # ── Tkinter setup ────────────────────────────────────────────────────────

    def _run(self):
        self.root   = tk.Tk()
        self.canvas = tk.Canvas(
            self.root, width=W, height=H,
            bg="#05080f", highlightthickness=0,
        )
        self.canvas.pack()

        self.root.overrideredirect(True)
        self.root.attributes("-topmost",  True)
        self.root.attributes("-alpha",    0.96)
        self.root.configure(bg="#05080f")

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{W}x{H}+{sw - W - 16}+{sh - H - 56}")

        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>",     self._drag_move)

        self._animate()
        self.root.mainloop()

    # ── Animation loop ────────────────────────────────────────────────────────

    def _animate(self):
        try:
            # Drain command queue
            while not self._queue.empty():
                cmd, val = self._queue.get_nowait()
                if cmd == "state":   self.state     = val
                elif cmd == "speak": self._speaking  = val

            self._tick     += 1
            self._float_y   = 4.0 * math.sin(self._tick * 0.04)
            self._hair_bob  = math.sin(self._tick * 0.08) if self._speaking else 0.0

            # Blink logic
            self._blink_t -= 1
            if self._blink_t <= 0:
                self._blink   = True
                self._blink_t = random.randint(200, 400)
            elif self._blink:
                if self._blink_t % 4 == 0:
                    self._blink = False

            # Speaking mouth advance
            if self._speaking:
                self._mouth_i = (self._mouth_i + 1) % len(MOUTH_SEQ)
            else:
                self._mouth_i = 0

            self._draw()
        except Exception:
            pass

        if self.root:
            self.root.after(50, self._animate)   # 20 fps

    # ── Master draw ───────────────────────────────────────────────────────────

    def _draw(self):
        c  = self.canvas
        em = EMOTIONS.get(self.state, EMOTIONS["idle"])
        c.delete("all")

        # Background gradient simulation (dark scanlines)
        c.create_rectangle(0, 0, W, H, fill=em["bg"], outline="")
        for y in range(0, H, 6):
            c.create_line(0, y, W, y, fill="#ffffff06")

        fy = FY + self._float_y   # floating face center y

        # Draw layers back-to-front
        self._draw_aura(c, em, fy)
        self._draw_hair_back(c, em, fy)
        self._draw_neck_body(c, em, fy)
        self._draw_face(c, em, fy)
        self._draw_cat_ears(c, em, fy)
        self._draw_eyes(c, em, fy)
        self._draw_nose(c, fy)
        self._draw_mouth(c, em, fy)
        self._draw_blush(c, em, fy)
        self._draw_hair_front(c, em, fy)
        self._draw_hair_bangs(c, em, fy)
        self._draw_accessories(c, em, fy)
        self._draw_ui(c, em)
        self._draw_corner_accents(c, em)

    # ── Aura glow ring ────────────────────────────────────────────────────────

    def _draw_aura(self, c, em, fy):
        aura = em["aura"]
        r    = 88 + 3 * math.sin(self._tick * 0.06)
        # outer diffuse ring
        for dr in range(12, 0, -2):
            alpha_hex = format(int(255 * (1 - dr / 14) * 0.15), "02x")
            c.create_oval(
                CX - r - dr, fy - r - dr,
                CX + r + dr, fy + r + dr,
                outline=aura, width=1,
            )
        # solid ring
        c.create_oval(CX-r, fy-r, CX+r, fy+r, outline=aura, width=2)

    # ── Hair back layer ───────────────────────────────────────────────────────

    def _draw_hair_back(self, c, em, fy):
        h  = em["hair"]
        hd = em["aura"]
        bob = self._hair_bob * 3

        # Long flowing back hair
        c.create_polygon(
            CX - 68, fy - 60,
            CX - 80, fy + 20 + bob,
            CX - 72, fy + 90 + bob,
            CX - 50, fy + 160 + bob,
            CX - 30, fy + 200 + bob,
            CX,      fy + 210 + bob,
            CX + 30, fy + 200 + bob,
            CX + 50, fy + 160 + bob,
            CX + 72, fy + 90 + bob,
            CX + 80, fy + 20 + bob,
            CX + 68, fy - 60,
            fill=h, outline=hd, width=0.5, smooth=True,
        )

        # Side hair strands
        for sx, dir_ in [(-1, 1), (1, -1)]:
            base_x = CX + sx * 60
            c.create_polygon(
                base_x,            fy - 40,
                base_x + dir_*10,  fy + 40 + bob,
                base_x + dir_*20,  fy + 120 + bob,
                base_x + dir_*12,  fy + 180 + bob,
                base_x + dir_*2,   fy + 180 + bob,
                base_x - dir_*6,   fy + 100 + bob,
                base_x - dir_*4,   fy + 20 + bob,
                fill="#5c35c0", outline=hd, width=0.5, smooth=True,
            )

    # ── Neck and body (school uniform) ────────────────────────────────────────

    def _draw_neck_body(self, c, em, fy):
        aura = em["aura"]

        # Neck
        c.create_rectangle(CX-10, fy+64, CX+10, fy+90, fill="#f5cba7", outline="")

        # Shoulders / body
        c.create_polygon(
            CX - 70, fy + 90,
            CX - 80, fy + 160,
            CX - 60, fy + 200,
            CX,      fy + 210,
            CX + 60, fy + 200,
            CX + 80, fy + 160,
            CX + 70, fy + 90,
            CX + 10, fy + 90,
            CX,      fy + 100,
            CX - 10, fy + 90,
            fill="#1a1f3a", outline=aura, width=0.8, smooth=True,
        )

        # Collar (sailor style)
        c.create_polygon(
            CX - 28, fy + 88,
            CX,      fy + 120,
            CX + 28, fy + 88,
            CX + 22, fy + 82,
            CX,      fy + 110,
            CX - 22, fy + 82,
            fill="#0d1124", outline=aura, width=0.8,
        )
        # Collar bow
        c.create_polygon(
            CX - 10, fy + 100,
            CX,      fy + 108,
            CX + 10, fy + 100,
            CX,      fy + 95,
            fill=em["aura"], outline="", smooth=True,
        )

        # Ribbon accent
        c.create_line(CX - 30, fy + 94, CX + 30, fy + 94, fill=aura, width=1)

    # ── Face circle ───────────────────────────────────────────────────────────

    def _draw_face(self, c, em, fy):
        r  = 66
        # Face shadow
        c.create_oval(CX-r+2, fy-r+4, CX+r+2, fy+r+4, fill="#d4a570", outline="")
        # Face skin
        c.create_oval(CX-r, fy-r, CX+r, fy+r, fill="#fde8c8", outline="#e8c090", width=1)
        # Forehead highlight
        c.create_oval(CX-28, fy-56, CX+28, fy-26, fill="#fff8ee", outline="")

    # ── Cat ears ─────────────────────────────────────────────────────────────

    def _draw_cat_ears(self, c, em, fy):
        h    = em["hair"]
        aura = em["aura"]
        bob  = self._hair_bob * 4

        # Left ear
        c.create_polygon(
            CX - 52, fy - 62,
            CX - 72, fy - 102 + bob,
            CX - 32, fy - 80,
            fill=h, outline=aura, width=1, smooth=True,
        )
        c.create_polygon(
            CX - 52, fy - 65,
            CX - 66, fy - 96 + bob,
            CX - 36, fy - 78,
            fill="#f5b8c8", outline="", smooth=True,
        )

        # Right ear
        c.create_polygon(
            CX + 52, fy - 62,
            CX + 72, fy - 102 + bob,
            CX + 32, fy - 80,
            fill=h, outline=aura, width=1, smooth=True,
        )
        c.create_polygon(
            CX + 52, fy - 65,
            CX + 66, fy - 96 + bob,
            CX + 36, fy - 78,
            fill="#f5b8c8", outline="", smooth=True,
        )

    # ── Anime eyes ────────────────────────────────────────────────────────────

    def _draw_eyes(self, c, em, fy):
        eye_col = em["eye"]
        ey      = fy - 14

        for side in [-1, 1]:
            ex = CX + side * 24

            if self._blink:
                # Blink — just a line
                c.create_line(ex-14, ey, ex+14, ey, fill="#4a2810", width=3)
                continue

            # Eye white
            c.create_oval(ex-15, ey-12, ex+15, ey+12,
                          fill="#f0f8ff", outline="#c8b098", width=0.8)

            # Iris (large anime style)
            c.create_oval(ex-10, ey-10, ex+10, ey+10,
                          fill=eye_col, outline="")

            # Iris gradient (darker bottom half)
            c.create_arc(ex-10, ey, ex+10, ey+10,
                         start=0, extent=180,
                         fill="#003020" if "teal" in eye_col or eye_col == "#00e5c8"
                              else "#002040",
                         outline="")

            # Pupil
            c.create_oval(ex-5, ey-5, ex+5, ey+5, fill="#0a0a0a", outline="")

            # Highlights (2 dots — classic anime style)
            c.create_oval(ex+2,  ey-7, ex+7,  ey-3, fill="white", outline="")
            c.create_oval(ex-7,  ey+2, ex-4,  ey+5, fill="white", outline="")

            # Eyelashes (top)
            for i, (dx, dy) in enumerate([(-12,-14),(-6,-17),(0,-18),(6,-17),(12,-14)]):
                c.create_line(ex, ey-9, ex+dx, ey+dy,
                              fill="#2a1a08", width=2 if i in [1,2,3] else 1)

            # Lower lash line
            c.create_arc(ex-14, ey-2, ex+14, ey+14,
                         start=200, extent=140,
                         outline="#4a2810", width=1, style=tk.ARC)

            # Eyebrow
            brow_y = ey - 20
            if self.state == "thinking":
                brow_y -= 4 * abs(math.sin(self._tick * 0.1))
            if self.state == "happy":
                # Curved happy brow
                c.create_arc(ex-14, brow_y-4, ex+14, brow_y+6,
                             start=0, extent=180,
                             outline="#4a2810", width=2, style=tk.ARC)
            else:
                c.create_line(ex-13, brow_y+2, ex-4,  brow_y,
                              ex+4,  brow_y,   ex+13, brow_y+2,
                              fill="#4a2810", width=2, smooth=True)

    # ── Nose ─────────────────────────────────────────────────────────────────

    def _draw_nose(self, c, fy):
        # Tiny dot nose (anime style)
        c.create_oval(CX-2, fy+6, CX+2, fy+10, fill="#e8b090", outline="")

    # ── Mouth ────────────────────────────────────────────────────────────────

    def _draw_mouth(self, c, em, fy):
        my = fy + 24

        if self._speaking:
            mo = MOUTH_SEQ[self._mouth_i]
            # Open mouth oval
            c.create_oval(CX-12, my, CX+12, my+mo+2,
                          fill="#c0404a", outline="#8a2030", width=1)
            # Upper teeth
            if mo >= 4:
                c.create_rectangle(CX-9, my+1, CX+9, my+4,
                                   fill="white", outline="")
        elif self.state == "happy":
            # Big happy W-mouth
            c.create_polygon(
                CX-14, my, CX-7, my+8, CX, my+4, CX+7, my+8, CX+14, my,
                fill="#c0404a", outline="#8a2030", width=1, smooth=True,
            )
            # Teeth
            c.create_polygon(
                CX-10, my+1, CX, my+6, CX+10, my+1,
                fill="white", outline="",
            )
        else:
            # Small smile
            c.create_arc(CX-14, my-6, CX+14, my+10,
                         start=200, extent=140,
                         outline="#c06080", width=2, style=tk.ARC)

    # ── Blush ────────────────────────────────────────────────────────────────

    def _draw_blush(self, c, em, fy):
        if not em.get("cheek"):
            return
        for side in [-1, 1]:
            bx = CX + side * 42
            c.create_oval(bx-14, fy+4, bx+14, fy+16,
                          fill=em["cheek"], outline="", stipple="gray25")

    # ── Hair front ───────────────────────────────────────────────────────────

    def _draw_hair_front(self, c, em, fy):
        h  = em["hair"]
        hd = em["aura"]
        bob = self._hair_bob * 2

        # Top of head hair
        c.create_oval(CX-70, fy-80, CX+70, fy-10,
                      fill=h, outline=hd, width=0.5)

        # Left side strand
        c.create_polygon(
            CX-66, fy-40,
            CX-76, fy+10+bob,
            CX-60, fy+50+bob,
            CX-44, fy+40+bob,
            CX-50, fy+0,
            fill="#6030b0", outline=hd, width=0.5, smooth=True,
        )

        # Right side strand
        c.create_polygon(
            CX+66, fy-40,
            CX+76, fy+10+bob,
            CX+60, fy+50+bob,
            CX+44, fy+40+bob,
            CX+50, fy+0,
            fill="#6030b0", outline=hd, width=0.5, smooth=True,
        )

    # ── Bangs ────────────────────────────────────────────────────────────────

    def _draw_hair_bangs(self, c, em, fy):
        h  = em["hair"]
        hd = em["aura"]
        bob = self._hair_bob * 1.5

        # Centre bang
        c.create_polygon(
            CX-18, fy-80,
            CX-20, fy-32+bob,
            CX-10, fy-24+bob,
            CX,    fy-30+bob,
            CX+10, fy-24+bob,
            CX+20, fy-32+bob,
            CX+18, fy-80,
            fill=h, outline=hd, width=0.5, smooth=True,
        )

        # Left bang
        c.create_polygon(
            CX-50, fy-76,
            CX-54, fy-30+bob,
            CX-40, fy-20+bob,
            CX-24, fy-26+bob,
            CX-22, fy-80,
            fill="#7040d0", outline=hd, width=0.5, smooth=True,
        )

        # Right bang
        c.create_polygon(
            CX+50, fy-76,
            CX+54, fy-30+bob,
            CX+40, fy-20+bob,
            CX+24, fy-26+bob,
            CX+22, fy-80,
            fill="#7040d0", outline=hd, width=0.5, smooth=True,
        )

        # Hair highlight streak
        c.create_line(
            CX-10, fy-80,  CX-8, fy-50+bob,
            fill="#c090ff", width=1, smooth=True,
        )

    # ── Accessories ──────────────────────────────────────────────────────────

    def _draw_accessories(self, c, em, fy):
        aura = em["aura"]
        bob  = self._hair_bob * 2

        # Hair clip (left side)
        c.create_rectangle(CX-54, fy-58+bob, CX-44, fy-50+bob,
                           fill=aura, outline="#ffffff40")
        c.create_text(CX-49, fy-54+bob, text="✦",
                      fill="white", font=("Arial", 6))

        # Star on right
        c.create_text(CX+50, fy-56+bob, text="★",
                      fill=aura, font=("Arial", 8))

    # ── UI labels ────────────────────────────────────────────────────────────

    def _draw_ui(self, c, em):
        aura = em["aura"]

        # Name
        c.create_text(CX, H-44, text="NANO",
                      fill=aura, font=("Courier New", 13, "bold"))

        # Status
        c.create_text(CX, H-24, text=em["label"],
                      fill=aura, font=("Courier New", 8, "bold"))

        # Pulse dot
        pulse = abs(math.sin(self._tick * 0.1))
        dot_r = 4 + int(pulse * 2)
        c.create_oval(CX-dot_r-60, H-28-dot_r, CX+dot_r-60, H-28+dot_r,
                      fill=aura, outline="")

    # ── Corner accents ────────────────────────────────────────────────────────

    def _draw_corner_accents(self, c, em):
        col = em["aura"]
        sz  = 14
        for x1, y1, x2, y2 in [
            (0,0,sz,0),(0,0,0,sz),
            (W,0,W-sz,0),(W,0,W,sz),
            (0,H,sz,H),(0,H,0,H-sz),
            (W,H,W-sz,H),(W,H,W,H-sz),
        ]:
            c.create_line(x1, y1, x2, y2, fill=col, width=1)

    # ── Drag ─────────────────────────────────────────────────────────────────

    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + e.x - self._dx
        y = self.root.winfo_y() + e.y - self._dy
        self.root.geometry(f"+{x}+{y}")


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    av = AnimeAvatarWindow()
    av.start_in_thread()
    print("Nano anime avatar running. Testing all states...")
    states = ["idle","listening","thinking","happy","speaking","error","idle"]
    try:
        for s in states:
            print(f"  → {s}")
            av.set_state(s)
            if s == "speaking":
                av.start_speaking()
            else:
                av.stop_speaking()
            time.sleep(2.5)
    except KeyboardInterrupt:
        pass
