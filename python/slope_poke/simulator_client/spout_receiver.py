"""Spout receiver wrapping SpoutGL into a numpy-returning API.

Each Unity camera publishes one or two Spout senders:
  - "<camera_id>_rgb"  RGBA8 color frame
  - "<camera_id>_seg"  RGBA8 instance-segmentation IDs (R*256+G = id, optional)

This receiver pulls the latest frame for a named sender into a numpy array.
A hidden GLFW window provides the GL context SpoutGL requires.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np

try:
    import SpoutGL
    from OpenGL import GL
    import glfw
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "SpoutGL / PyOpenGL / glfw are required. `uv sync` should install them."
    ) from e


@dataclass
class SpoutFrame:
    pixels: np.ndarray  # (H, W, 4) uint8 RGBA
    width: int
    height: int


class SpoutReceiver:
    """Thread-safe receiver for one named Spout sender.

    Usage:
        with SpoutReceiver("cameraA_rgb") as rx:
            frame = rx.receive()
    """

    _gl_lock = threading.Lock()
    _gl_initialized = False
    _gl_window = None

    def __init__(self, sender_name: str):
        self.sender_name = sender_name
        self._receiver: SpoutGL.SpoutReceiver | None = None
        self._buffer: np.ndarray | None = None
        self._width = 0
        self._height = 0

    @classmethod
    def _ensure_gl_context(cls) -> None:
        with cls._gl_lock:
            if cls._gl_initialized:
                return
            if not glfw.init():
                raise RuntimeError("glfw.init() failed")
            glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
            cls._gl_window = glfw.create_window(64, 64, "slope-poke-spout", None, None)
            if not cls._gl_window:
                glfw.terminate()
                raise RuntimeError("Failed to create hidden GL window for Spout.")
            glfw.make_context_current(cls._gl_window)
            cls._gl_initialized = True

    def __enter__(self) -> "SpoutReceiver":
        self._ensure_gl_context()
        self._receiver = SpoutGL.SpoutReceiver()
        self._receiver.setReceiverName(self.sender_name)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._receiver is not None:
            self._receiver.releaseReceiver()
            self._receiver = None

    def receive(self) -> SpoutFrame | None:
        """Pull the latest frame. Returns None if no new frame is available yet."""
        if self._receiver is None:
            raise RuntimeError("SpoutReceiver used outside of `with` block.")

        # SpoutGL needs a GL context current on this thread for receiveImage.
        glfw.make_context_current(self._gl_window)

        # Probe sender size; allocate / resize buffer as needed.
        w = self._receiver.getSenderWidth()
        h = self._receiver.getSenderHeight()
        if w == 0 or h == 0:
            # No active sender yet.
            self._receiver.receiveImage(None, GL.GL_RGBA, False, 0)
            return None

        if self._buffer is None or self._width != w or self._height != h:
            self._buffer = np.empty((h, w, 4), dtype=np.uint8)
            self._width, self._height = w, h

        ok = self._receiver.receiveImage(self._buffer, GL.GL_RGBA, False, 0)
        if not ok or not self._receiver.isFrameNew():
            return None

        return SpoutFrame(pixels=self._buffer.copy(), width=w, height=h)
