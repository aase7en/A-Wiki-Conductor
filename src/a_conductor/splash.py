"""Splash screen — pixel-particle logo, version, credits (user request)."""

from __future__ import annotations

import tkinter as tk


PIXEL_LOGO = [
    "                                    ",
    "                                    ",
    "      ██████    ██████    ██        ",
    "      ██   ██   ██   ██   ██        ",
    "      ██   ██   ██   ██   ██        ",
    "      ██████    ██████    ██        ",
    "      ██         ██   ██  ██        ",
    "      ██         ██   ██  ██        ",
    "      ██         ██████   ███████   ",
    "                                    ",
    "   ══════════════════════════════   ",
    "   ║  A·SUNDAY CONDUCTOR        ║   ",
    "   ══════════════════════════════   ",
    "                                    ",
]

# Pixel colors (theme: warm Sunday morning)
COLORS = {
    "█": "#F59E0B",   # amber-500
    "═": "#3B82F6",   # blue-500
    "║": "#64748B",   # slate-500
}

PARTICLE_COLORS = ["#F59E0B", "#3B82F6", "#10B981", "#EF4444", "#8B5CF6", "#06B6D4"]

PIXEL_SIZE = 8
COLS = max(len(row) for row in PIXEL_LOGO)
ROWS = len(PIXEL_LOGO)
WIDTH = COLS * PIXEL_SIZE + 40
HEIGHT = ROWS * PIXEL_SIZE + 120


class SplashScreen:
    """Animated pixel-particle splash with version and credits."""

    def __init__(self, app_name: str, version: str, developer: str = "Human + AI 'A'") -> None:
        self.root = tk.Tk()
        self.root.title("A-Sunday Conductor")
        self.root.overrideredirect(True)
        self.root.configure(bg="#0A0E1A")
        self.root.geometry(f"{WIDTH}x{HEIGHT}+{self._center_x()}+{self._center_y()}")

        self.canvas = tk.Canvas(
            self.root, width=WIDTH, height=HEIGHT, bg="#0A0E1A",
            highlightthickness=0, bd=0
        )
        self.canvas.pack(fill="both", expand=True)

        self._pixels: list[tuple[int, int, str]] = []
        self._particles: list[dict] = []
        self._draw_pixel_logo()
        self._init_particles()
        self._draw_text(app_name, version, developer)
        self.root.after(3000, self._close)

    def _center_x(self) -> int:
        return (self.root.winfo_screenwidth() - WIDTH) // 2

    def _center_y(self) -> int:
        return (self.root.winfo_screenheight() - HEIGHT) // 2

    def _draw_pixel_logo(self) -> None:
        for row_idx, row in enumerate(PIXEL_LOGO):
            for col_idx, char in enumerate(row):
                if char in COLORS:
                    x = 20 + col_idx * PIXEL_SIZE
                    y = 20 + row_idx * PIXEL_SIZE
                    color = COLORS[char]
                    self._pixels.append((x, y, color))
                    self.canvas.create_rectangle(
                        x, y, x + PIXEL_SIZE - 1, y + PIXEL_SIZE - 1,
                        fill=color, outline=""
                    )

    def _init_particles(self, count: int = 30) -> None:
        import random

        for _ in range(count):
            self._particles.append({
                "x": random.randint(0, WIDTH),
                "y": random.randint(0, HEIGHT),
                "vx": random.uniform(-0.5, 0.5),
                "vy": random.uniform(-0.3, 0.3),
                "color": random.choice(PARTICLE_COLORS),
                "size": random.randint(2, 4),
                "id": None,
            })

    def _animate_particles(self) -> None:
        import math

        for p in self._particles:
            if p["id"]:
                self.canvas.delete(p["id"])
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["x"] < 0: p["x"] = WIDTH
            if p["x"] > WIDTH: p["x"] = 0
            if p["y"] < 0: p["y"] = HEIGHT
            if p["y"] > HEIGHT: p["y"] = 0
            pulse = 0.5 + 0.5 * math.sin(p["x"] * 0.02 + p["y"] * 0.01)
            alpha_color = p["color"] if pulse > 0.3 else "#1E293B"
            p["id"] = self.canvas.create_rectangle(
                p["x"], p["y"],
                p["x"] + p["size"], p["y"] + p["size"],
                fill=alpha_color, outline=""
            )
        if self.root.winfo_exists():
            self.root.after(50, self._animate_particles)

    def _draw_text(self, app_name: str, version: str, developer: str) -> None:
        y_offset = ROWS * PIXEL_SIZE + 30
        self.canvas.create_text(
            WIDTH // 2, y_offset,
            text=app_name,
            fill="#F59E0B", font=("Consolas", 13, "bold")
        )
        self.canvas.create_text(
            WIDTH // 2, y_offset + 22,
            text=f"v{version}",
            fill="#64748B", font=("Consolas", 10)
        )
        self.canvas.create_text(
            WIDTH // 2, y_offset + 42,
            text=f"by {developer}",
            fill="#475569", font=("Consolas", 9)
        )
        self.canvas.create_text(
            WIDTH // 2, HEIGHT - 10,
            text="Uses Serena engine (MIT) · Python stdlib only",
            fill="#334155", font=("Consolas", 7)
        )

    def _close(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def show(self) -> None:
        self._animate_particles()
        self.root.mainloop()


def show_splash(app_name: str, version: str, developer: str = "Human + AI 'A'") -> None:
    """Display the splash for ~3 seconds, then close."""
    try:
        splash = SplashScreen(app_name, version, developer)
        splash.show()
    except tk.TclError:
        pass
