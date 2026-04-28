"""Subscribes to Unity's CoverageStreamer and feeds CoverageAnalyzer."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from types import TracebackType

import msgpack
import numpy as np
import zmq

from .analyzer import CoverageAnalyzer, CoverageGrid


class CoverageReceiver:
    """One subscriber, all cameras. Background thread fills an internal dict."""

    def __init__(
        self,
        endpoint: str = "tcp://127.0.0.1:5557",
        analyzer: CoverageAnalyzer | None = None,
    ):
        self.endpoint = endpoint
        self.analyzer = analyzer or CoverageAnalyzer()
        self._ctx: zmq.Context | None = None
        self._sock: zmq.Socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._latest_gen: dict[str, int] = {}

    def __enter__(self) -> "CoverageReceiver":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.stop()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._ctx = zmq.Context.instance()
        self._sock = self._ctx.socket(zmq.SUB)
        self._sock.setsockopt(zmq.SUBSCRIBE, b"")
        self._sock.RCVTIMEO = 100
        self._sock.LINGER = 0
        self._sock.connect(self.endpoint)
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="coverage-rx", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def _run(self) -> None:
        assert self._sock is not None
        while not self._stop.is_set():
            try:
                topic, body = self._sock.recv_multipart()
            except zmq.error.Again:
                continue
            except zmq.error.ZMQError:
                break
            grid = self._decode(body)
            if grid is None:
                continue
            with self._lock:
                self.analyzer.update(grid)

    @staticmethod
    def _decode(body: bytes) -> CoverageGrid | None:
        msg = msgpack.unpackb(body, raw=False)
        if not isinstance(msg, dict):
            return None
        try:
            cam_id = str(msg["camera_id"])
            w = int(msg["width"])
            h = int(msg["height"])
            flat = msg["grid"]
            world_min = msg["world_min"]
            world_max = msg["world_max"]
        except (KeyError, TypeError, ValueError):
            return None
        arr = np.asarray(flat, dtype=np.float32).reshape(h, w)
        return CoverageGrid(
            camera_id=cam_id,
            grid=arr,
            extent=(
                float(world_min[0]),
                float(world_max[0]),
                float(world_min[1]),
                float(world_max[1]),
            ),
        )

    def known_cameras(self) -> Iterator[str]:
        with self._lock:
            yield from list(self.analyzer._grids.keys())  # noqa: SLF001
