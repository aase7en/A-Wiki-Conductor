"""Interactive image-mapped particle logo for the desktop header.

The interaction model is inspired by image-mapped particle demos: particles
sample a source image, drift subtly while idle, repel from a moving pointer,
then spring back home. Eye-region particles receive an additional gaze offset
so the portrait appears to look toward the cursor anywhere inside the app.

The implementation intentionally stays dependency-free (Tk Canvas only) so the
desktop build does not need an embedded browser/WebGL runtime.
"""

from __future__ import annotations

from collections import deque
import math
from pathlib import Path
import random
import tkinter as tk
from typing import Iterable, Sequence

CANVAS_SIZE = 80
DOT_SIZE = 2.0
DOT_COLOR = "#5cc8d7"
EYE_COLOR = "#f59e0b"
MONO_DOT_COLOR = "#f2f2f2"
REPULSION_RADIUS = 28.0
REPULSION_FORCE = 4.2
TRAIL_RADIUS = 18.0
TRAIL_FORCE = 2.2
SPRING_K = 0.045
DAMPING = 0.82
ANIM_DELAY = 24  # ~42 fps
EYE_TRACK_RANGE = 4.5
IDLE_INTENSITY = 0.65
IDLE_SPEED = 0.0018
DEPTH_SCALE = 0.22
MAX_IMAGE_PARTICLES = 2600
FALLBACK_IDLE_PARTICLE_LIMIT = 600
BRIGHTNESS_THRESHOLD = 52

# Simple fallback face. E = eye particle, 1 = face particle, 0 = empty.
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

# Normalised eye centres tuned for the family particle portrait used by the app.
# These are only used when a loaded source is monochrome; coloured sources keep
# their explicit amber eye pixels instead.
FAMILY_EYE_REGIONS: tuple[tuple[float, float, float], ...] = (
    (0.195, 0.405, 0.034),
    (0.298, 0.408, 0.034),
    (0.472, 0.281, 0.032),
    (0.553, 0.285, 0.032),
    (0.797, 0.363, 0.030),
    (0.876, 0.389, 0.030),
)

# Tiny bitmap glyphs used to add the requested particle label over the chest.
# The exact mixed-case string is preserved even though the glyphs are deliberately
# minimal so they remain legible in a 120 px header widget.
_PARTICLE_FONT: dict[str, tuple[str, ...]] = {
    "S": ("1111", "1000", "1000", "1111", "0001", "0001", "1111"),
    "u": ("0000", "0000", "1001", "1001", "1001", "1011", "0111"),
    "n": ("0000", "0000", "1110", "1001", "1001", "1001", "1001"),
    "d": ("0001", "0001", "0111", "1001", "1001", "1011", "0111"),
    "a": ("0000", "0000", "0110", "0001", "0111", "1001", "0111"),
    "y": ("0000", "0000", "1001", "1001", "0111", "0001", "1110"),
    "-": ("000", "000", "000", "111", "000", "000", "000"),
    "F": ("1111", "1000", "1000", "1110", "1000", "1000", "1000"),
    "m": ("00000", "00000", "11011", "10101", "10101", "10101", "10101"),
    "i": ("1", "0", "1", "1", "1", "1", "1"),
    "l": ("10", "10", "10", "10", "10", "10", "01"),
}


def normalized_eye_hit(
    nx: float,
    ny: float,
    regions: Sequence[tuple[float, float, float]] = FAMILY_EYE_REGIONS,
) -> bool:
    """Return whether a normalised source coordinate belongs to an eye region."""
    for cx, cy, radius in regions:
        dx = nx - cx
        dy = ny - cy
        if dx * dx + dy * dy <= radius * radius:
            return True
    return False


def eye_target(
    home_x: float,
    home_y: float,
    mouse_x: float,
    mouse_y: float,
    max_shift: float = EYE_TRACK_RANGE,
) -> tuple[float, float]:
    """Return a bounded gaze target from an eye home position toward the cursor."""
    dx = mouse_x - home_x
    dy = mouse_y - home_y
    distance = math.hypot(dx, dy)
    if distance <= 1e-9:
        return home_x, home_y
    shift = min(max_shift, distance * 0.08)
    return home_x + dx / distance * shift, home_y + dy / distance * shift


def repulsion_impulse(
    particle_x: float,
    particle_y: float,
    mouse_x: float,
    mouse_y: float,
    radius: float = REPULSION_RADIUS,
    force: float = REPULSION_FORCE,
) -> tuple[float, float]:
    """Calculate a smooth radial impulse away from the cursor."""
    dx = particle_x - mouse_x
    dy = particle_y - mouse_y
    distance = math.hypot(dx, dy)
    if distance <= 1e-9 or distance >= radius:
        return 0.0, 0.0
    magnitude = force * (1.0 - distance / radius) ** 1.6
    return dx / distance * magnitude, dy / distance * magnitude


class Particle:
    __slots__ = (
        "home_x",
        "home_y",
        "x",
        "y",
        "vx",
        "vy",
        "is_eye",
        "id",
        "color",
        "base_radius",
        "seed",
        "phase",
        "depth",
    )

    def __init__(
        self,
        home_x: float,
        home_y: float,
        is_eye: bool = False,
        *,
        color: str = DOT_COLOR,
        radius: float = DOT_SIZE,
        seed: float | None = None,
    ) -> None:
        self.home_x = home_x
        self.home_y = home_y
        self.x = home_x
        self.y = home_y
        self.vx = 0.0
        self.vy = 0.0
        self.is_eye = is_eye
        self.id: int | None = None
        self.color = color
        self.base_radius = radius
        self.seed = random.random() if seed is None else seed
        self.phase = self.seed * math.tau
        self.depth = 0.65 + self.seed * 0.7


class InteractiveLogo:
    """Tk Canvas particle portrait with CodePen-like interaction and gaze tracking."""

    def __init__(self, parent: tk.Widget, size: int = CANVAS_SIZE) -> None:
        self.size = size
        self.canvas = tk.Canvas(
            parent,
            width=size,
            height=size,
            bg=parent.cget("bg") if hasattr(parent, "cget") else "#0A0E1A",
            highlightthickness=0,
            bd=0,
        )
        self.particles: list[Particle] = []
        self.mouse_x = -1000.0
        self.mouse_y = -1000.0
        self.mouse_active = False
        self._running = False
        self._started_ms: int | None = None
        self._last_pointer: tuple[float, float] | None = None
        self._mouse_speed = 0.0
        self._trail: deque[list[float]] = deque(maxlen=12)
        self._monochrome_source = False

        self._build_face()
        self.canvas.bind("<Motion>", self._on_mouse)
        self.canvas.bind("<Leave>", self._on_leave)

    def _new_particle(
        self,
        x: float,
        y: float,
        *,
        is_eye: bool = False,
        color: str = DOT_COLOR,
        radius: float = DOT_SIZE,
        seed: float | None = None,
    ) -> Particle:
        p = Particle(x, y, is_eye, color=color, radius=radius, seed=seed)
        p.id = self.canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=color,
            outline="",
        )
        self.particles.append(p)
        return p

    def _build_face(self) -> None:
        """Generate fallback particles from the compact face map."""
        rows = len(FACE_MAP)
        cols = len(FACE_MAP[0]) if FACE_MAP else 0
        if rows == 0 or cols == 0:
            return
        cell = min(self.size / cols, self.size / rows)
        offset_x = (self.size - cols * cell) / 2
        offset_y = (self.size - rows * cell) / 2
        radius = max(1.0, min(DOT_SIZE, cell * 0.27))

        for row_idx, row in enumerate(FACE_MAP):
            for col_idx, ch in enumerate(row):
                if ch == "0":
                    continue
                px = offset_x + col_idx * cell + cell / 2
                py = offset_y + row_idx * cell + cell / 2
                is_eye = ch == "E"
                self._new_particle(
                    px,
                    py,
                    is_eye=is_eye,
                    color=EYE_COLOR if is_eye else DOT_COLOR,
                    radius=radius,
                    seed=(row_idx * cols + col_idx + 1) / (rows * cols + 1),
                )

    @staticmethod
    def _is_amber(r: int, g: int, b: int) -> bool:
        return r > 170 and 70 < g < 210 and b < 120 and r > g * 1.05

    @staticmethod
    def _is_monochrome_bright(r: int, g: int, b: int) -> bool:
        return max(r, g, b) > 115 and max(r, g, b) - min(r, g, b) < 35

    def load_image(self, image_path) -> bool:
        """Load a PNG and convert its visible bright pixels into mapped particles.

        Colour sources preserve cyan/amber semantics. A mostly monochrome source is
        treated as the family portrait: its particles stay white, six eye regions are
        tagged for gaze tracking, and ``Sunday-Family`` is added as particle text.
        """
        try:
            photo = tk.PhotoImage(file=str(image_path))
        except tk.TclError:
            return False

        w, h = photo.width(), photo.height()
        if w <= 0 or h <= 0:
            return False
        family_asset = Path(image_path).name.lower() == "sunday-family-particle.png"

        # Read at up to ~2x canvas resolution so fine stipple survives without
        # creating tens of thousands of Tk canvas items.
        max_source = max(1, self.size * 2)
        subsample = max(1, max(w, h) // max_source)
        if subsample > 1:
            photo = photo.subsample(subsample, subsample)
        sw, sh = photo.width(), photo.height()

        fit = min(self.size / max(sw, 1), self.size / max(sh, 1))
        draw_w = sw * fit
        draw_h = sh * fit
        offset_x = (self.size - draw_w) / 2.0
        offset_y = (self.size - draw_h) / 2.0

        # First lightweight pass estimates whether this is white-on-black artwork.
        bright = mono = amber = 0
        probe_step = max(1, min(sw, sh) // 48)
        for y in range(0, sh, probe_step):
            for x in range(0, sw, probe_step):
                try:
                    r, g, b = photo.get(x, y)[:3]
                except Exception:
                    continue
                if max(r, g, b) < BRIGHTNESS_THRESHOLD:
                    continue
                bright += 1
                mono += int(self._is_monochrome_bright(r, g, b))
                amber += int(self._is_amber(r, g, b))
        self._monochrome_source = family_asset or (
            bright > 0 and mono / bright >= 0.82 and amber == 0
        )

        candidates: list[tuple[float, float, bool, str, float, float]] = []
        sample_step = 1 if max(sw, sh) <= self.size else 2
        for y in range(0, sh, sample_step):
            for x in range(0, sw, sample_step):
                try:
                    r, g, b = photo.get(x, y)[:3]
                except Exception:
                    continue
                luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
                if luminance < BRIGHTNESS_THRESHOLD:
                    continue

                nx = (x + 0.5) / sw
                ny = (y + 0.5) / sh
                px = offset_x + (x + 0.5) * fit
                py = offset_y + (y + 0.5) * fit
                amber_pixel = self._is_amber(r, g, b)
                is_eye = amber_pixel or (
                    self._monochrome_source and normalized_eye_hit(nx, ny)
                )
                if self._monochrome_source:
                    color = MONO_DOT_COLOR
                elif amber_pixel:
                    color = EYE_COLOR
                else:
                    color = DOT_COLOR
                # Bright samples get a slightly larger dot; this mimics image
                # luminance/depth mapping while retaining separated particles.
                radius = max(0.55, min(1.55, 0.55 + luminance / 255.0))
                seed = (x * 0.754877666 + y * 0.569840296) % 1.0
                candidates.append((px, py, is_eye, color, radius, seed))

        # Deterministically thin dense images to keep animation responsive.
        if len(candidates) > MAX_IMAGE_PARTICLES:
            stride = len(candidates) / MAX_IMAGE_PARTICLES
            candidates = [candidates[int(i * stride)] for i in range(MAX_IMAGE_PARTICLES)]

        self.canvas.delete("all")
        self.particles.clear()
        for px, py, is_eye, color, radius, seed in candidates:
            self._new_particle(
                px,
                py,
                is_eye=is_eye,
                color=color,
                radius=radius,
                seed=seed,
            )

        if self._monochrome_source and not family_asset:
            self._add_particle_label("Sunday-Family", y_ratio=0.72)
        return bool(self.particles)

    def _add_particle_label(self, text: str, *, y_ratio: float) -> None:
        """Add a tiny mixed-case particle label centred over the portrait chest."""
        glyphs = [_PARTICLE_FONT.get(ch) for ch in text]
        if any(glyph is None for glyph in glyphs):
            return
        widths = [len(glyph[0]) for glyph in glyphs if glyph is not None]
        logical_width = sum(widths) + max(0, len(widths) - 1)
        if logical_width <= 0:
            return
        cell = min(1.5, (self.size * 0.88) / logical_width)
        start_x = (self.size - logical_width * cell) / 2.0
        start_y = min(self.size - 8 * cell, self.size * y_ratio)
        radius = max(0.45, cell * 0.34)
        cursor = 0
        seed_index = 0
        for glyph in glyphs:
            assert glyph is not None
            width = len(glyph[0])
            for row, pattern in enumerate(glyph):
                for col, bit in enumerate(pattern):
                    if bit != "1":
                        continue
                    x = start_x + (cursor + col + 0.5) * cell
                    y = start_y + (row + 0.5) * cell
                    seed_index += 1
                    self._new_particle(
                        x,
                        y,
                        color=MONO_DOT_COLOR,
                        radius=radius,
                        seed=(seed_index * 0.61803398875) % 1.0,
                    )
            cursor += width + 1

    def _on_mouse(self, event) -> None:
        self.mouse_x = float(event.x)
        self.mouse_y = float(event.y)
        self.mouse_active = True

    def _on_leave(self, _event) -> None:
        # Do not clear the gaze here. _refresh_pointer() keeps tracking the cursor
        # across the whole A-Sunday Conductor window, not only over the logo.
        pass

    def _refresh_pointer(self) -> None:
        """Map the OS pointer into logo coordinates while it is inside the app."""
        try:
            if not self.canvas.winfo_ismapped():
                return
            top = self.canvas.winfo_toplevel()
            px = float(self.canvas.winfo_pointerx())
            py = float(self.canvas.winfo_pointery())
            left = float(top.winfo_rootx())
            top_y = float(top.winfo_rooty())
            right = left + float(top.winfo_width())
            bottom = top_y + float(top.winfo_height())
            inside = left <= px <= right and top_y <= py <= bottom
            self.mouse_active = inside
            if inside:
                self.mouse_x = px - float(self.canvas.winfo_rootx())
                self.mouse_y = py - float(self.canvas.winfo_rooty())
        except tk.TclError:
            self.mouse_active = False

    def _update_mouse_trail(self) -> None:
        for point in self._trail:
            point[2] *= 0.72
        while self._trail and self._trail[0][2] < 0.05:
            self._trail.popleft()

        if not self.mouse_active:
            self._last_pointer = None
            self._mouse_speed *= 0.75
            return

        current = (self.mouse_x, self.mouse_y)
        if self._last_pointer is None:
            self._last_pointer = current
            self._mouse_speed = 0.0
            return
        dx = current[0] - self._last_pointer[0]
        dy = current[1] - self._last_pointer[1]
        speed = math.hypot(dx, dy)
        self._mouse_speed = self._mouse_speed * 0.55 + speed * 0.45
        if speed >= 0.35:
            strength = min(1.0, 0.18 + self._mouse_speed / 18.0)
            self._trail.append([current[0], current[1], strength])
        self._last_pointer = current

    def _trail_impulse(self, p: Particle) -> tuple[float, float]:
        ix = iy = 0.0
        for tx, ty, strength in self._trail:
            dx = p.x - tx
            dy = p.y - ty
            distance = math.hypot(dx, dy)
            if distance <= 1e-9 or distance >= TRAIL_RADIUS:
                continue
            magnitude = TRAIL_FORCE * strength * (1.0 - distance / TRAIL_RADIUS) ** 2
            ix += dx / distance * magnitude
            iy += dy / distance * magnitude
        return ix, iy

    def _animate(self) -> None:
        if not self._running:
            return

        self._refresh_pointer()
        self._update_mouse_trail()
        now = int(self.canvas.tk.call("clock", "milliseconds"))
        if self._started_ms is None:
            self._started_ms = now
        elapsed = max(0, now - self._started_ms)

        # Tk Canvas becomes prohibitively expensive when thousands of ovals are
        # resized/repositioned every frame. Keep the full idle/depth effect for
        # the small built-in face, but for dense image fallbacks only touch
        # particles that are actually interacting or springing back.
        dense_fallback = len(self.particles) > FALLBACK_IDLE_PARTICLE_LIMIT

        for p in self.particles:
            if dense_fallback:
                target_x = p.home_x
                target_y = p.home_y
                idle_phase = p.phase
            else:
                idle_phase = p.phase + elapsed * IDLE_SPEED * p.depth
                idle_x = math.sin(idle_phase * 1.07) * IDLE_INTENSITY * p.depth
                idle_y = math.cos(idle_phase * 0.83 + p.seed * 2.0) * IDLE_INTENSITY * 0.75
                target_x = p.home_x + idle_x
                target_y = p.home_y + idle_y

            interaction = False
            if self.mouse_active:
                if p.is_eye:
                    gaze_x, gaze_y = eye_target(
                        p.home_x,
                        p.home_y,
                        self.mouse_x,
                        self.mouse_y,
                    )
                    target_x += gaze_x - p.home_x
                    target_y += gaze_y - p.home_y
                    interaction = True

                ix, iy = repulsion_impulse(
                    p.x,
                    p.y,
                    self.mouse_x,
                    self.mouse_y,
                )
                if abs(ix) > 1e-9 or abs(iy) > 1e-9:
                    interaction = True
                    p.vx += ix
                    p.vy += iy

            tx, ty = self._trail_impulse(p)
            if abs(tx) > 1e-9 or abs(ty) > 1e-9:
                interaction = True
                p.vx += tx
                p.vy += ty

            displaced = (
                abs(target_x - p.x) > 0.01
                or abs(target_y - p.y) > 0.01
                or abs(p.vx) > 0.01
                or abs(p.vy) > 0.01
            )

            # A dense fallback that is not moving does not need a Canvas write.
            if dense_fallback and not interaction and not displaced:
                continue

            p.vx += (target_x - p.x) * SPRING_K
            p.vy += (target_y - p.y) * SPRING_K
            p.vx *= DAMPING
            p.vy *= DAMPING
            p.x += p.vx
            p.y += p.vy

            if dense_fallback:
                radius = p.base_radius
            else:
                # Pseudo-depth is cheap enough for the small built-in face.
                depth_wave = math.sin(idle_phase * 0.9 + p.phase)
                radius = p.base_radius * (1.0 + DEPTH_SCALE * depth_wave)
                radius = max(0.35, radius)

            if p.id is not None:
                self.canvas.coords(
                    p.id,
                    p.x - radius,
                    p.y - radius,
                    p.x + radius,
                    p.y + radius,
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
