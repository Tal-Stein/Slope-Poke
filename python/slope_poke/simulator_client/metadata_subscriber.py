"""ZMQ SUB socket pulling per-frame metadata published by Unity.

Topic format: b"<camera_id>" — frame body is msgpack-encoded FrameMeta JSON.
Subscriber filters by camera_id (empty filter = all cameras).
"""

from __future__ import annotations

from collections import defaultdict, deque
from threading import Event, Lock, Thread

import msgpack
import zmq

from .types import FrameMeta


class MetadataSubscriber:
    def __init__(self, endpoint: str = "tcp://127.0.0.1:5555", buffer_per_camera: int = 8):
        self.endpoint = endpoint
        self._ctx = zmq.Context.instance()
        self._sock = self._ctx.socket(zmq.SUB)
        self._sock.setsockopt(zmq.RCVHWM, 32)
        self._sock.setsockopt(zmq.LINGER, 0)
        self._sock.setsockopt(zmq.SUBSCRIBE, b"")  # all cameras
        self._sock.connect(endpoint)

        self._buffers: dict[str, deque[FrameMeta]] = defaultdict(
            lambda: deque(maxlen=buffer_per_camera)
        )
        self._lock = Lock()
        self._stop = Event()
        self._thread = Thread(target=self._run, name="meta-sub", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)
        self._sock.close()

    def latest(self, camera_id: str) -> FrameMeta | None:
        with self._lock:
            buf = self._buffers.get(camera_id)
            return buf[-1] if buf else None

    def _run(self) -> None:
        poller = zmq.Poller()
        poller.register(self._sock, zmq.POLLIN)
        while not self._stop.is_set():
            events = dict(poller.poll(timeout=100))
            if self._sock not in events:
                continue
            topic, payload = self._sock.recv_multipart()
            try:
                data = msgpack.unpackb(payload, raw=False)
                meta = FrameMeta.model_validate(data)
            except Exception:
                continue
            with self._lock:
                self._buffers[meta.camera_id].append(meta)
