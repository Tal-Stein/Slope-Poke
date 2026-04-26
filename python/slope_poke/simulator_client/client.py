"""SimulatorClient — top-level API binding Spout receivers and the metadata stream."""

from __future__ import annotations

import time
from contextlib import ExitStack

import numpy as np

from .exceptions import FrameTimeout, SimulatorDisconnected
from .metadata_subscriber import MetadataSubscriber
from .spout_receiver import SpoutReceiver
from .types import FrameMeta


class SimulatorClient:
    """Receives frames + metadata from a running Unity sim.

    Example:
        with SimulatorClient(camera_ids=["cameraA"]) as sim:
            frame, meta = sim.get_frame("cameraA", timeout=1.0)
    """

    def __init__(
        self,
        camera_ids: list[str],
        zmq_endpoint: str = "tcp://127.0.0.1:5555",
        receive_seg: bool = False,
    ):
        self.camera_ids = camera_ids
        self.zmq_endpoint = zmq_endpoint
        self.receive_seg = receive_seg
        self._stack = ExitStack()
        self._rgb: dict[str, SpoutReceiver] = {}
        self._seg: dict[str, SpoutReceiver] = {}
        self._meta = MetadataSubscriber(zmq_endpoint)

    def __enter__(self) -> "SimulatorClient":
        self._stack.__enter__()
        for cid in self.camera_ids:
            self._rgb[cid] = self._stack.enter_context(SpoutReceiver(f"{cid}_rgb"))
            if self.receive_seg:
                self._seg[cid] = self._stack.enter_context(SpoutReceiver(f"{cid}_seg"))
        self._meta.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._meta.stop()
        self._stack.__exit__(exc_type, exc, tb)

    def get_frame(
        self, camera_id: str, timeout: float = 1.0
    ) -> tuple[np.ndarray, FrameMeta]:
        """Block until a fresh frame + matching metadata arrive, or raise."""
        if camera_id not in self._rgb:
            raise KeyError(f"Unknown camera_id {camera_id!r}; configure it on init.")

        deadline = time.monotonic() + timeout
        rx = self._rgb[camera_id]
        while time.monotonic() < deadline:
            frame = rx.receive()
            if frame is None:
                time.sleep(0.001)
                continue
            meta = self._meta.latest(camera_id)
            if meta is None:
                # Frame arrived before any metadata — keep polling briefly.
                time.sleep(0.001)
                continue
            return frame.pixels, meta
        raise FrameTimeout(f"No frame from {camera_id!r} within {timeout}s.")

    def get_segmentation(self, camera_id: str) -> np.ndarray | None:
        rx = self._seg.get(camera_id)
        if rx is None:
            raise SimulatorDisconnected(
                f"Segmentation receiver for {camera_id!r} not configured."
            )
        f = rx.receive()
        return f.pixels if f else None
