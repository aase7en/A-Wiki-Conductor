"""Interactive particle-face logo — mouse tracking + repulsion effect.

Canvas-based widget for the header. Particles form a face outline;
eyes track the mouse; particles repel when the cursor gets close.
Supports loading a custom face image (assets/logo-face.png) —
each opaque pixel becomes a particle dot.
"""

from __future__ import annotations

import math
import tkinter as tk

CANVAS_SIZE = 80
DOT_SIZE = 2
DOT_COLOR = "#5cc8d7"
EYE_COLOR = "#f59e0b"
REPULSION_RADIUS = 25
REPULSION_FORCE = 5.0
SPRING_K = 0.03
DAMPING = 0.85
ANIM_DELAY = 30  # ms (~33fps)
EYE_TRACK_RANGE = 8.0  # how far eyes shift toward the mouse (pixels)

# Simple pixel-art face (placeholder until user provides a real image)
# E = eye dot (amber, tracks mouse), 1 = face dot (teal), 0 = empty
FACE_MAP = [
    "0000000000",
    "0111111110",
    "0111111110",
    "01E1111E10",
    "01E1111E10",
    "0111111110",
    "0111111110",
    "0110001110",
    "0110000110",
    "0000000000",
]


class Particle:
    __slots__ = ("home_x", "home_y", "x", "y", "vx", "vy", "is_eye", "id")

    def __init__(self, home_x: float, home_y: float, is_eye: bool = False) -> None:
        self.home_x = home_x
        self.home_y = home_y
        self.x = home_x
        self.y = home_y
        self.vx = 0.0
        self.vy = 0.0
        self.is_eye = is_eye
        self.id: int | None = None


class InteractiveLogo:
    """Canvas widget with particle-face, mouse tracking, and repulsion."""

    def __init__(self, parent: tk.Widget, size: int = CANVAS_SIZE) -> None:
        self.size = size
        self.canvas = tk.Canvas(
            parent,
            width=size,
            height=size,
            bg=parent.cget("bg") if hasattr(parent, "cget") else "#121820",
            highlightthickness=0,
            bd=0,
        )
        self.particles: list[Particle] = []
        self.mouse_x = -100.0
        self.mouse_y = -100.0
        self._running = False

        self._build_face()
        self.canvas.bind("<Motion>", self._on_mouse)
        self.canvas.bind("<Leave>", self._on_leave)

    def _build_face(self) -> None:
        """Generate particles from the pixel-art face map."""
        rows = len(FACE_MAP)
        cols = len(FACE_MAP[0]) if FACE_MAP else 0
        if rows == 0 or cols == 0:
            return
        cell = min(self.size / cols, self.size / rows)
        offset_x = (self.size - cols * cell) / 2
        offset_y = (self.size - rows * cell) / 2

        for row_idx, row in enumerate(FACE_MAP):
            for col_idx, ch in enumerate(row):
                if ch == "0":
                    continue
                px = offset_x + col_idx * cell + cell / 2
                py = offset_y + row_idx * cell + cell / 2
                is_eye = ch == "E"
                self.particles.append(Particle(px, py, is_eye))
                color = EYE_COLOR if is_eye else DOT_COLOR
                p = self.particles[-1]
                p.id = self.canvas.create_oval(
                    px - DOT_SIZE, py - DOT_SIZE, px + DOT_SIZE, py + DOT_SIZE,
                    fill=color, outline="",
                )

    def load_image(self, image_path) -> bool:
        """Load a PNG and convert each opaque pixel to a particle dot."""
        try:
            photo = tk.PhotoImage(file=str(image_path))
        except tk.TclError:
            return False

        # Downsample if too large
        w, h = photo.width(), photo.height()
        scale = max(1, max(w, h) // self.size)
        sw, sh = w // scale, h // scale
        photo = photo.subsample(scale, scale)

        self.canvas.delete("all")
        self.particles.clear()

        for y in range(sh):
            for x in range(sw):
                try:
                    r, g, b = photo.get(x, y)[:3]
                except Exception:
                    continue
                # Skip transparent/black pixels
                if r < 30 and g < 30 and b < 30:
                    continue
                px = x * (self.size / sw)
                py = y * (self.size / sh)
                is_eye = r > 200 and g > 150 and b < 100  # amber-ish = eye
                p = Particle(px, py, is_eye)
                p.id = self.canvas.create_oval(
                    px - DOT_SIZE, py - DOT_SIZE, px + DOT_SIZE, py + DOT_SIZE,
                    fill=EYE_COLOR if is_eye else DOT_COLOR, outline="",
                )
                self.particles.append(p)
        return True

    def _on_mouse(self, event) -> None:
        self.mouse_x = float(event.x)
        self.mouse_y = float(event.y)

    def _on_leave(self, _event) -> None:
        self.mouse_x = -100.0
        self.mouse_y = -100.0

    def _animate(self) -> None:
        if not self._running:
            return
        mx, my = self.mouse_x, self.mouse_y
        for p in self.particles:
            # Repulsion: push away from mouse
            dx = p.x - mx
            dy = p.y - my
            dist = math.hypot(dx, dy)
            if dist < REPULSION_RADIUS and dist > 0.01:
                force = REPULSION_FORCE * (1.0 - dist / REPULSION_RADIUS)
                p.vx += (dx / dist) * force
                p.vy += (dy / dist) * force

            # Eye tracking: eyes shift toward mouse
            if p.is_eye:
                angle = math.atan2(my - p.home_y, mx - p.home_x)
                target_x = p.home_x + math.cos(angle) * EYE_TRACK_RANGE
                target_y = p.home_y + math.sin(angle) * EYE_TRACK_RANGE
            else:
                target_x = p.home_x
                target_y = p.home_y

            # Spring toward home (or eye target)
            p.vx += (target_x - p.x) * SPRING_K
            p.vy += (target_y - p.y) * SPRING_K

            # Apply velocity with damping
            p.vx *= DAMPING
            p.vy *= DAMPING
            p.x += p.vx
            p.y += p.vy

            # Update canvas position
            if p.id is not None:
                self.canvas.coords(
                    p.id,
                    p.x - DOT_SIZE, p.y - DOT_SIZE,
                    p.x + DOT_SIZE, p.y + DOT_SIZE,
                )

        self.canvas.after(ANIM_DELAY, self._animate)

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._animate()

    def stop(self) -> None:
        self._running = False

    def pack(self, **kwargs) -> None:
        self.canvas.pack(**kwargs)

    def grid(self, **kwargs) -> None:
        self.canvas.grid(**kwargs)
