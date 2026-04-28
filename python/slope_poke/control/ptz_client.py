"""Client for Unity's PTZController ZMQ REP socket.

Wire format mirrors the ad-hoc parser in PTZController.cs: a JSON object with any
subset of {"pan", "tilt", "zoom"}, all floats. Reply is {"ok": true} or
{"ok": false, "err": "..."}. The Unity side clamps to its configured ranges and
slews toward the target at maxPanRate / maxTiltRate; zoom is applied immediately.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import TracebackType

import zmq


class PTZError(RuntimeError):
    """Raised when the Unity PTZController rejects a command or the socket times out."""


@dataclass(frozen=True)
class PTZCommand:
    pan: float | None = None
    tilt: float | None = None
    zoom: float | None = None

    def to_json(self) -> str:
        body: dict[str, float] = {}
        if self.pan is not None:
            body["pan"] = float(self.pan)
        if self.tilt is not None:
            body["tilt"] = float(self.tilt)
        if self.zoom is not None:
            body["zoom"] = float(self.zoom)
        if not body:
            raise ValueError("PTZCommand requires at least one of pan/tilt/zoom.")
        return json.dumps(body)


class PTZClient:
    """REQ-socket client. One client per PTZ camera (each binds its own endpoint)."""

    def __init__(
        self,
        endpoint: str = "tcp://127.0.0.1:5556",
        recv_timeout_ms: int = 1000,
        send_timeout_ms: int = 1000,
    ):
        self.endpoint = endpoint
        self._ctx: zmq.Context | None = None
        self._sock: zmq.Socket | None = None
        self._recv_timeout_ms = recv_timeout_ms
        self._send_timeout_ms = send_timeout_ms

    def __enter__(self) -> "PTZClient":
        self._ctx = zmq.Context.instance()
        self._sock = self._ctx.socket(zmq.REQ)
        self._sock.RCVTIMEO = self._recv_timeout_ms
        self._sock.SNDTIMEO = self._send_timeout_ms
        self._sock.LINGER = 0
        self._sock.connect(self.endpoint)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def send(self, cmd: PTZCommand) -> None:
        if self._sock is None:
            raise RuntimeError("PTZClient must be used as a context manager.")
        try:
            self._sock.send_string(cmd.to_json())
            reply = self._sock.recv_string()
        except zmq.error.Again as e:
            raise PTZError(f"PTZ command timed out against {self.endpoint}.") from e
        try:
            payload = json.loads(reply)
        except json.JSONDecodeError as e:
            raise PTZError(f"Malformed reply from PTZController: {reply!r}") from e
        if not payload.get("ok", False):
            raise PTZError(f"PTZController rejected command: {payload.get('err', reply)}")

    def goto(
        self,
        pan: float | None = None,
        tilt: float | None = None,
        zoom: float | None = None,
    ) -> None:
        self.send(PTZCommand(pan=pan, tilt=tilt, zoom=zoom))
