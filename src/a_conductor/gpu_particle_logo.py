"""GPU-backed Sunday Family particle portrait for the Tk desktop UI.

The widget embeds an OpenGL surface inside the existing Tkinter application.
Particles are sampled from a white-on-black source image and displaced entirely
in the vertex shader: cursor repulsion, velocity swirl/trail, subtle idle drift,
and weighted gaze motion for the six family eye regions.

The module is deliberately optional at runtime.  If the OpenGL bridge or driver
cannot initialise, :class:`GPUParticleLogo` swaps itself to the existing
Tkinter :class:`InteractiveLogo` renderer instead of taking down the app.
"""

from __future__ import annotations

from array import array
import math
import os
from pathlib import Path
import sys
import time
import tkinter as tk

from .interactive_logo import FAMILY_EYE_REGIONS

try:  # Windows GPU path; import failures are expected on unsupported platforms.
    import moderngl
    from PIL import Image
    from pyopengltk import OpenGLFrame
except Exception as exc:  # pragma: no cover - exercised by fallback path on unsupported hosts
    moderngl = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]
    OpenGLFrame = None  # type: ignore[assignment]
    GPU_IMPORT_ERROR: Exception | None = exc
else:
    GPU_IMPORT_ERROR = None

GPU_FRAME_MS = 24  # ~42 fps; enough for gentle logo motion with lower load
GPU_MAX_PARTICLES = 40_000
GPU_SOURCE_MAX_DIMENSION = 520
GPU_BRIGHTNESS_THRESHOLD = 38
GPU_LUMINANCE_SAMPLING_POWER = 1.4
GPU_FACE_PARALLAX_CLIP = 0.012  # ~0.7 px at a 120 px logo
GPU_GAZE_CLIP = 0.032  # ~1.9 px at a 120 px logo
GPU_REPULSION_CLIP = 0.012  # ~0.7 px at a 120 px logo
GPU_TRAIL_CLIP = 0.005  # ~0.3 px at a 120 px logo
GPU_POINTER_POSITION_EASE = 0.24
GPU_POINTER_RETURN_EASE = 0.18
GPU_POINTER_STRENGTH_EASE = 0.18
GPU_POINT_BASE_SIZE = 0.72
GPU_POINT_LUMA_SIZE = 0.48
GPU_POINT_INTERACTION_SIZE = 0.12
GPU_MIN_VISIBLE_PIXEL_RATIO = 0.035
GPU_IDLE_BASE_CLIP = 0.0015
GPU_IDLE_LUMA_CLIP = 0.0022
GPU_IDLE_DRIFT_CLIP = GPU_IDLE_BASE_CLIP + GPU_IDLE_LUMA_CLIP


def _enable_compatibility_point_sprites() -> None:
    """Enable ``gl_PointCoord`` support only for legacy-compatible contexts.

    ``pyopengltk`` creates a compatibility-profile WGL context on Windows.  In
    that profile, point-coordinate replacement stays disabled until the legacy
    ``GL_POINT_SPRITE`` capability is enabled.  Core profiles provide point
    coordinates unconditionally and reject that legacy capability, so leave
    them untouched.
    """
    from OpenGL import GL

    profile_mask = 0
    try:
        raw_mask = GL.glGetIntegerv(GL.GL_CONTEXT_PROFILE_MASK)
        try:
            profile_mask = int(raw_mask)
        except (TypeError, ValueError):
            profile_mask = int(raw_mask[0])
    except Exception:
        # Do not guess here.  A core profile rejects the legacy capability;
        # unknown profiles therefore keep the modern default behaviour.
        profile_mask = 0

    compatibility_bit = int(
        getattr(GL, "GL_CONTEXT_COMPATIBILITY_PROFILE_BIT", 0x00000002)
    )
    if profile_mask & compatibility_bit:
        GL.glEnable(GL.GL_POINT_SPRITE)


def _read_nonblack_back_buffer(width: int, height: int) -> int:
    """Return the real non-black pixel count from the current back buffer."""
    from OpenGL import GL

    GL.glReadBuffer(GL.GL_BACK)
    # RGBA rows are always four-byte aligned, including odd widget widths.
    raw = bytes(
        GL.glReadPixels(0, 0, width, height, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
    )
    return sum(
        1
        for offset in range(0, len(raw), 4)
        if raw[offset] or raw[offset + 1] or raw[offset + 2]
    )


def minimum_visible_pixels(width: int, height: int) -> int:
    """Return meaningful portrait coverage for the one-time framebuffer gate."""
    return max(32, math.ceil(width * height * GPU_MIN_VISIBLE_PIXEL_RATIO))


def gpu_backend_available() -> bool:
    """Return whether the optional Python-side GPU stack imported successfully."""
    if os.environ.get("A_CONDUCTOR_GPU_PARTICLES", "").strip() == "0":
        return False
    return moderngl is not None and Image is not None and OpenGLFrame is not None


def _release_pyopengltk_context(gl_frame: object) -> None:
    """Release native handles that pyopengltk does not destroy itself.

    pyopengltk 0.0.x creates a WGL/GLX context in private attributes but its
    ``BaseOpenGLFrame`` has no teardown hook.  Keep this adapter deliberately
    small and best-effort: optional GPU cleanup must never prevent Tk shutdown.
    """
    context_attr = "_OpenGLFrame__context"
    window_attr = "_OpenGLFrame__window"
    context = getattr(gl_frame, context_attr, None)
    window = getattr(gl_frame, window_attr, None)

    try:
        if sys.platform.startswith("win32"):
            if context is not None:
                try:
                    from OpenGL.WGL import wglDeleteContext, wglMakeCurrent

                    wglMakeCurrent(None, None)
                    wglDeleteContext(context)
                except Exception:
                    pass
            if window is not None:
                try:
                    from ctypes import WinDLL, c_int, c_void_p
                    from ctypes.wintypes import HDC, HWND

                    release_dc = WinDLL("user32", use_last_error=True).ReleaseDC
                    release_dc.argtypes = [HWND, HDC]
                    release_dc.restype = c_int
                    hwnd = c_void_p(int(gl_frame.winfo_id()))  # type: ignore[attr-defined]
                    release_dc(hwnd, window)
                except Exception:
                    pass
        elif sys.platform.startswith("linux") and window is not None:
            try:
                from ctypes import c_int
                from OpenGL import GLX
                from pyopengltk import linux as pyopengltk_linux

                if context is not None:
                    GLX.glXMakeCurrent(window, 0, None)
                    GLX.glXDestroyContext(window, context)
                close_display = pyopengltk_linux._x11lib.XCloseDisplay
                close_display.argtypes = [type(window)]
                close_display.restype = c_int
                close_display(window)
            except Exception:
                pass
    finally:
        if hasattr(gl_frame, context_attr):
            setattr(gl_frame, context_attr, None)
        if hasattr(gl_frame, window_attr):
            setattr(gl_frame, window_attr, None)
        if hasattr(gl_frame, "context_created"):
            setattr(gl_frame, "context_created", False)


def _eye_weight(nx: float, ny: float) -> float:
    """Return a soft 0..1 gaze weight for the family portrait eye regions."""
    best = 0.0
    for cx, cy, radius in FAMILY_EYE_REGIONS:
        distance = math.hypot(nx - cx, ny - cy)
        if distance >= radius:
            continue
        weight = 1.0 - distance / radius
        # Smoothstep-like falloff keeps eyelids nearly fixed while pupils/centres move.
        weight = weight * weight * (3.0 - 2.0 * weight)
        best = max(best, weight)
    return best


def build_particle_vertices(
    image_path: str | Path,
    *,
    max_particles: int = GPU_MAX_PARTICLES,
    max_dimension: int = GPU_SOURCE_MAX_DIMENSION,
    threshold: int = GPU_BRIGHTNESS_THRESHOLD,
) -> tuple[array, int, float]:
    """Sample a particle portrait into packed GPU vertex data.

    Each vertex stores ``u, v, luminance, random_seed, eye_weight`` as floats.
    Coordinates stay in source-image UV space; the shader performs aspect-fit so
    resizing the desktop window cannot stretch the family portrait.
    """
    if Image is None:
        raise RuntimeError("Pillow is required for GPU particle sampling")
    path = Path(image_path)
    with Image.open(path) as source:
        image = source.convert("L")
        original_w, original_h = image.size
        if original_w <= 0 or original_h <= 0:
            raise ValueError(f"Invalid particle source dimensions: {image.size!r}")
        image_aspect = original_w / original_h
        largest = max(original_w, original_h)
        if largest > max_dimension:
            scale = max_dimension / largest
            resized = (
                max(1, round(original_w * scale)),
                max(1, round(original_h * scale)),
            )
            image = image.resize(resized, Image.Resampling.LANCZOS)

        width, height = image.size
        pixels = image.load()
        candidates: list[tuple[float, float, float, float, float]] = []
        for y in range(height):
            ny = (y + 0.5) / height
            for x in range(width):
                value = int(pixels[x, y])
                if value < threshold:
                    continue
                nx = (x + 0.5) / width
                luminance = value / 255.0
                # Deterministic hash-like seed avoids transferring per-frame CPU noise.
                seed = (x * 0.7548776662466927 + y * 0.5698402909980532) % 1.0
                # Preserve portrait contrast after downsampling: mid-gray areas
                # receive proportionally fewer points than bright landmarks.
                # Treating every above-threshold pixel equally flattens faces
                # into an indistinct cloud even though the vertex count is high.
                if seed >= luminance**GPU_LUMINANCE_SAMPLING_POWER:
                    continue
                candidates.append((nx, ny, luminance, seed, _eye_weight(nx, ny)))

    if not candidates:
        raise ValueError(f"Particle source contains no bright samples: {path}")
    if len(candidates) > max_particles:
        stride = len(candidates) / max_particles
        candidates = [candidates[int(index * stride)] for index in range(max_particles)]

    packed = array("f")
    for values in candidates:
        packed.extend(values)
    return packed, len(candidates), image_aspect


_VERTEX_SHADER = r"""
#version 330
in vec2 in_uv;
in float in_luma;
in float in_seed;
in float in_eye;

uniform float u_time;
uniform vec2 u_mouse;
uniform vec2 u_mouse_velocity;
uniform float u_mouse_active;
uniform float u_image_aspect;
uniform float u_view_aspect;

out float v_luma;
out float v_force;
out float v_eye;

vec2 aspect_fit(vec2 uv) {
    vec2 p = vec2(uv.x * 2.0 - 1.0, 1.0 - uv.y * 2.0);
    if (u_image_aspect > u_view_aspect) {
        p.y *= u_view_aspect / u_image_aspect;
    } else {
        p.x *= u_image_aspect / u_view_aspect;
    }
    return p * 0.965;
}

void main() {
    vec2 p = aspect_fit(in_uv);

    // Very small breathing motion keeps the portrait alive even when idle.
    float phase = in_seed * 6.28318530718;
    float drift = sin(u_time * 1.15 + phase)
        * (__IDLE_BASE__ + __IDLE_LUMA__ * in_luma);
    p += vec2(cos(phase * 1.73), sin(phase * 1.31)) * drift;

    // Whole-portrait parallax is deliberately smaller than eye motion.
    vec2 face_dir = length(u_mouse) > 0.0001 ? normalize(u_mouse) : vec2(0.0);
    p += face_dir * __FACE_PARALLAX__ * u_mouse_active;

    // Eye-region particles shift toward the pointer.  Soft per-vertex weighting
    // means centres move most while the surrounding eyelid structure stays stable.
    vec2 to_mouse = u_mouse - p;
    float mouse_len = max(length(to_mouse), 0.0001);
    vec2 gaze_dir = to_mouse / mouse_len;
    p += gaze_dir * (__GAZE__ * in_eye * u_mouse_active);

    // CodePen-like local distortion field: radial push plus a velocity-dependent
    // tangential component that reads visually as a short particle trail/swirl.
    vec2 delta = p - u_mouse;
    float distance_to_mouse = max(length(delta), 0.0001);
    float field = smoothstep(0.34, 0.0, distance_to_mouse) * u_mouse_active;
    float local_field = field * (1.0 - in_eye);
    vec2 away = delta / distance_to_mouse;
    float velocity = clamp(length(u_mouse_velocity) * 4.0, 0.0, 1.0);
    vec2 tangent = vec2(-away.y, away.x);
    p += away * local_field * __REPULSION__;
    p += tangent * local_field * velocity * __TRAIL__;

    gl_Position = vec4(p, 0.0, 1.0);
    // Keep dots fine and separated; interaction changes position more than size.
    gl_PointSize = __POINT_BASE__ + __POINT_LUMA__ * in_luma
        + local_field * __POINT_INTERACTION__;
    v_luma = in_luma;
    v_force = local_field;
    v_eye = in_eye;
}
"""

_VERTEX_SHADER = _VERTEX_SHADER.replace("__FACE_PARALLAX__", f"{GPU_FACE_PARALLAX_CLIP:.6f}")
_VERTEX_SHADER = _VERTEX_SHADER.replace("__GAZE__", f"{GPU_GAZE_CLIP:.6f}")
_VERTEX_SHADER = _VERTEX_SHADER.replace("__IDLE_BASE__", f"{GPU_IDLE_BASE_CLIP:.6f}")
_VERTEX_SHADER = _VERTEX_SHADER.replace("__IDLE_LUMA__", f"{GPU_IDLE_LUMA_CLIP:.6f}")
_VERTEX_SHADER = _VERTEX_SHADER.replace("__REPULSION__", f"{GPU_REPULSION_CLIP:.6f}")
_VERTEX_SHADER = _VERTEX_SHADER.replace("__TRAIL__", f"{GPU_TRAIL_CLIP:.6f}")
_VERTEX_SHADER = _VERTEX_SHADER.replace("__POINT_BASE__", f"{GPU_POINT_BASE_SIZE:.6f}")
_VERTEX_SHADER = _VERTEX_SHADER.replace("__POINT_LUMA__", f"{GPU_POINT_LUMA_SIZE:.6f}")
_VERTEX_SHADER = _VERTEX_SHADER.replace(
    "__POINT_INTERACTION__", f"{GPU_POINT_INTERACTION_SIZE:.6f}"
)


_FRAGMENT_SHADER = r"""
#version 330
in float v_luma;
in float v_force;
in float v_eye;
uniform float u_mouse_active;
out vec4 fragColor;

void main() {
    vec2 centred = gl_PointCoord - vec2(0.5);
    float radius = length(centred) * 2.0;
    if (radius > 1.0) {
        discard;
    }
    float edge = 1.0 - smoothstep(0.58, 1.0, radius);
    float alpha = edge * (0.42 + 0.58 * v_luma);
    float intensity = 0.78 + 0.22 * v_luma + 0.12 * v_force;
    vec3 neutral = vec3(intensity);
    float eye_core = smoothstep(0.72, 0.96, v_eye) * u_mouse_active;
    vec3 amber = vec3(0.96, 0.55, 0.10);
    vec3 colour = mix(neutral, amber, eye_core * 0.82);
    fragColor = vec4(colour, alpha);
}
"""


if OpenGLFrame is not None:

    class _ParticleGLFrame(OpenGLFrame):  # type: ignore[misc,valid-type]
        def __init__(self, owner: "GPUParticleLogo", parent: tk.Widget, *, size: int) -> None:
            self.owner = owner
            super().__init__(parent, width=size, height=size)

        def initgl(self) -> None:
            self.owner._init_gl(self)

        def redraw(self) -> None:
            self.owner._redraw_gl(self)

else:  # pragma: no cover - only instantiated after an availability bug

    class _ParticleGLFrame:  # type: ignore[no-redef]
        pass


class GPUParticleLogo:
    """Adaptive Tk widget: native GPU renderer with automatic Canvas fallback."""

    def __init__(self, parent: tk.Widget, size: int = 120) -> None:
        self.size = size
        try:
            background = parent.cget("bg")
        except Exception:
            background = "#000000"
        self.frame = tk.Frame(
            parent,
            width=size,
            height=size,
            bg=background,
            highlightthickness=0,
            bd=0,
        )
        self.frame.grid_propagate(False)
        self.frame.pack_propagate(False)
        # desktop_ui attaches help/tooltip behaviour to .canvas.  The wrapper is
        # stable even if the inner renderer changes from GL to Canvas.
        self.canvas = self.frame

        self._source_path: Path | None = None
        self._fallback = None
        self._fallback_after_id: str | None = None
        self._gl_frame = None
        self._ctx = None
        self._program = None
        self._buffer = None
        self._vao = None
        self._particle_count = 0
        self._image_aspect = 4.0 / 3.0
        self._gpu_ready = False
        self._frame_verified = False
        self._gpu_error: str | None = None
        self._running = False
        self._started_at = time.perf_counter()
        self._mouse_x = 0.0
        self._mouse_y = 0.0
        self._render_mouse_x = 0.0
        self._render_mouse_y = 0.0
        self._mouse_vx = 0.0
        self._mouse_vy = 0.0
        self._interaction_strength = 0.0
        self._last_mouse_time = time.perf_counter()
        self._mouse_active = False
        self._motion_binding: str | None = None
        self._destroyed = False

        if gpu_backend_available():
            try:
                self._gl_frame = _ParticleGLFrame(self, self.frame, size=size)
                self._gl_frame.pack(fill=tk.BOTH, expand=True)
            except Exception as exc:
                self._schedule_fallback(exc)
        else:
            self._schedule_fallback(GPU_IMPORT_ERROR or RuntimeError("GPU backend unavailable"))

    @property
    def renderer_name(self) -> str:
        if self._gpu_ready and self._frame_verified:
            return "gpu-opengl"
        if self._fallback is not None:
            return "tk-canvas-fallback"
        return "gpu-pending"

    @property
    def gpu_error(self) -> str | None:
        return self._gpu_error

    def _init_gl(self, gl_frame: _ParticleGLFrame) -> None:
        if self._gpu_ready:
            return
        try:
            assert moderngl is not None
            gl_frame.tkMakeCurrent()
            self._ctx = moderngl.create_context(require=330)
            _enable_compatibility_point_sprites()
            self._ctx.enable(moderngl.BLEND | moderngl.PROGRAM_POINT_SIZE)
            self._ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            self._program = self._ctx.program(
                vertex_shader=_VERTEX_SHADER,
                fragment_shader=_FRAGMENT_SHADER,
            )
            self._gpu_ready = True
            if self._source_path is not None:
                self._rebuild_gpu_buffer()
        except Exception as exc:
            self._gpu_ready = False
            self._schedule_fallback(exc)

    def _release_gpu_resources(self) -> None:
        for resource_name in ("_vao", "_buffer", "_program"):
            resource = getattr(self, resource_name, None)
            if resource is None:
                continue
            try:
                resource.release()
            except Exception:
                pass
            setattr(self, resource_name, None)

    def _release_gl_renderer(self, *, destroy_frame: bool) -> None:
        """Release ModernGL objects, the wrapper context, then native handles."""
        gl_frame = self._gl_frame
        if gl_frame is not None and getattr(gl_frame, "context_created", False):
            try:
                gl_frame.tkMakeCurrent()
            except Exception:
                pass

        self._release_gpu_resources()
        context = self._ctx
        self._ctx = None
        if context is not None:
            try:
                context.release()
            except Exception:
                pass

        if gl_frame is not None:
            _release_pyopengltk_context(gl_frame)
            if destroy_frame:
                try:
                    gl_frame.destroy()
                except Exception:
                    pass
                self._gl_frame = None

        self._particle_count = 0
        self._gpu_ready = False
        self._frame_verified = False

    def _rebuild_gpu_buffer(self) -> None:
        self._frame_verified = False
        if not self._gpu_ready or self._ctx is None or self._program is None:
            return
        if self._source_path is None:
            return
        target_particles = max(6_000, min(GPU_MAX_PARTICLES, int(self.size * self.size * 0.65)))
        packed, count, image_aspect = build_particle_vertices(
            self._source_path, max_particles=target_particles
        )
        self._release_gpu_resources()
        # _release_gpu_resources clears the program too; recreate it before VAO build.
        self._program = self._ctx.program(
            vertex_shader=_VERTEX_SHADER,
            fragment_shader=_FRAGMENT_SHADER,
        )
        self._buffer = self._ctx.buffer(packed.tobytes())
        self._vao = self._ctx.vertex_array(
            self._program,
            [(self._buffer, "2f 1f 1f 1f", "in_uv", "in_luma", "in_seed", "in_eye")],
        )
        self._particle_count = count
        self._image_aspect = image_aspect

    def load_image(self, image_path: str | Path) -> bool:
        path = Path(image_path)
        if not path.is_file():
            return False
        self._source_path = path
        if self._fallback is not None:
            return bool(self._fallback.load_image(path))
        if self._gpu_ready:
            try:
                self._rebuild_gpu_buffer()
            except Exception as exc:
                self._schedule_fallback(exc)
                return False
        return True

    def _schedule_fallback(self, exc: Exception) -> None:
        self._gpu_error = f"{type(exc).__name__}: {exc}"
        self._gpu_ready = False
        self._frame_verified = False
        if self._destroyed or self._fallback_after_id is not None:
            return
        try:
            self._fallback_after_id = self.frame.after_idle(self._activate_fallback)
        except tk.TclError:
            self._fallback_after_id = None

    def _cancel_scheduled_fallback(self) -> None:
        callback = self._fallback_after_id
        self._fallback_after_id = None
        if callback is None:
            return
        try:
            self.frame.after_cancel(callback)
        except (tk.TclError, ValueError):
            pass

    def _activate_fallback(self) -> None:
        self._fallback_after_id = None
        if self._destroyed:
            return
        if self._fallback is not None:
            return
        if self._gl_frame is not None:
            self._stop_gl_animation()
        self._release_gl_renderer(destroy_frame=True)
        from .interactive_logo import InteractiveLogo

        self._fallback = InteractiveLogo(self.frame, size=self.size)
        self._fallback.pack(fill=tk.BOTH, expand=True)
        if self._source_path is not None:
            self._fallback.load_image(self._source_path)
        if self._running:
            self._fallback.start()

    def _bind_pointer(self) -> None:
        if self._motion_binding is not None:
            return
        try:
            top = self.frame.winfo_toplevel()
            self._motion_binding = top.bind("<Motion>", self._on_global_motion, add="+")
        except tk.TclError:
            self._motion_binding = None

    def _on_global_motion(self, event: tk.Event) -> None:
        try:
            width = max(1, self.frame.winfo_width())
            height = max(1, self.frame.winfo_height())
            local_x = float(event.x_root - self.frame.winfo_rootx())
            local_y = float(event.y_root - self.frame.winfo_rooty())
        except (tk.TclError, AttributeError):
            return
        clip_x = local_x / width * 2.0 - 1.0
        clip_y = 1.0 - local_y / height * 2.0
        now = time.perf_counter()
        dt = max(1e-4, now - self._last_mouse_time)
        raw_vx = (clip_x - self._mouse_x) / dt
        raw_vy = (clip_y - self._mouse_y) / dt
        # Bounded low-pass velocity keeps quick pointer flicks expressive but stable.
        self._mouse_vx = self._mouse_vx * 0.55 + max(-4.0, min(4.0, raw_vx)) * 0.45
        self._mouse_vy = self._mouse_vy * 0.55 + max(-4.0, min(4.0, raw_vy)) * 0.45
        self._mouse_x = clip_x
        self._mouse_y = clip_y
        self._last_mouse_time = now
        self._mouse_active = True

    def _pointer_inside_app(self) -> bool:
        try:
            top = self.frame.winfo_toplevel()
            px, py = top.winfo_pointerxy()
            x0, y0 = top.winfo_rootx(), top.winfo_rooty()
            return x0 <= px < x0 + top.winfo_width() and y0 <= py < y0 + top.winfo_height()
        except tk.TclError:
            return False

    def _advance_pointer_state(self, *, pointer_inside: bool) -> None:
        """Ease the rendered pointer field and invalidate samples after leave."""
        sample_active = pointer_inside and self._mouse_active
        target_x = self._mouse_x if sample_active else 0.0
        target_y = self._mouse_y if sample_active else 0.0
        position_ease = (
            GPU_POINTER_POSITION_EASE if sample_active else GPU_POINTER_RETURN_EASE
        )
        target_strength = 1.0 if sample_active else 0.0

        self._render_mouse_x += (target_x - self._render_mouse_x) * position_ease
        self._render_mouse_y += (target_y - self._render_mouse_y) * position_ease
        self._interaction_strength += (
            target_strength - self._interaction_strength
        ) * GPU_POINTER_STRENGTH_EASE
        velocity_decay = 0.86 if sample_active else 0.72
        self._mouse_vx *= velocity_decay
        self._mouse_vy *= velocity_decay

        # Re-entry needs a fresh <Motion> sample; a stale off-window target must
        # never reactivate merely because geometry becomes inside again.
        if not pointer_inside:
            self._mouse_active = False

    def _redraw_gl(self, gl_frame: _ParticleGLFrame) -> None:
        if not self._gpu_ready or self._ctx is None or self._program is None:
            return
        try:
            gl_frame.tkMakeCurrent()
            width = max(1, gl_frame.winfo_width())
            height = max(1, gl_frame.winfo_height())
            self._ctx.viewport = (0, 0, width, height)
            self._ctx.clear(0.0, 0.0, 0.0, 1.0)
            if self._vao is None or self._particle_count <= 0:
                return
            self._advance_pointer_state(pointer_inside=self._pointer_inside_app())
            self._program["u_time"].value = time.perf_counter() - self._started_at
            self._program["u_mouse"].value = (
                self._render_mouse_x,
                self._render_mouse_y,
            )
            self._program["u_mouse_velocity"].value = (self._mouse_vx, self._mouse_vy)
            self._program["u_mouse_active"].value = self._interaction_strength
            self._program["u_image_aspect"].value = float(self._image_aspect)
            self._program["u_view_aspect"].value = width / height
            self._vao.render(mode=moderngl.POINTS, vertices=self._particle_count)
            if not self._frame_verified and width >= 32 and height >= 32:
                self._ctx.finish()
                nonblack = _read_nonblack_back_buffer(width, height)
                minimum_visible = minimum_visible_pixels(width, height)
                if nonblack < minimum_visible:
                    raise RuntimeError("GPU_FRAMEBUFFER_BLANK")
                self._frame_verified = True
        except Exception as exc:
            self._gpu_ready = False
            self._frame_verified = False
            self._schedule_fallback(exc)

    def start(self) -> None:
        self._running = True
        self._bind_pointer()
        if self._fallback is not None:
            self._fallback.start()
        elif self._gl_frame is not None:
            # pyopengltk interprets animate as the redraw delay in milliseconds.
            self._gl_frame.animate = GPU_FRAME_MS

    def _stop_gl_animation(self) -> None:
        if self._gl_frame is None:
            return
        self._gl_frame.animate = 0
        callback = getattr(self._gl_frame, "cb", None)
        if callback is not None:
            try:
                self._gl_frame.after_cancel(callback)
            except (tk.TclError, ValueError):
                pass
            self._gl_frame.cb = None

    def stop(self) -> None:
        self._running = False
        if self._fallback is not None:
            self._fallback.stop()
        self._stop_gl_animation()

    def destroy(self) -> None:
        self._destroyed = True
        self._cancel_scheduled_fallback()
        self.stop()
        try:
            top = self.frame.winfo_toplevel()
            if self._motion_binding is not None:
                top.unbind("<Motion>", self._motion_binding)
        except tk.TclError:
            pass
        self._motion_binding = None
        if self._fallback is not None:
            try:
                self._fallback.destroy()
            except (AttributeError, tk.TclError):
                pass
            self._fallback = None
        self._release_gl_renderer(destroy_frame=True)
        try:
            self.frame.destroy()
        except tk.TclError:
            pass

    def pack(self, **kwargs) -> None:
        self.frame.pack(**kwargs)

    def grid(self, **kwargs) -> None:
        self.frame.grid(**kwargs)
