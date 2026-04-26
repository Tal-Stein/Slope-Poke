"""Slope-Poke CLI entrypoint.

Subcommands:
    smoke     Receive frames from a running Unity sim and print FPS / metadata.
    list      List active Spout senders.
"""

from __future__ import annotations

import argparse
import sys
import time

from .simulator_client import SimulatorClient
from .simulator_client.exceptions import FrameTimeout


def cmd_smoke(args: argparse.Namespace) -> int:
    print(f"Connecting to Unity (camera={args.camera}, zmq={args.zmq}) ...")
    with SimulatorClient(camera_ids=[args.camera], zmq_endpoint=args.zmq) as sim:
        t0 = time.monotonic()
        n = 0
        while n < args.frames:
            try:
                frame, meta = sim.get_frame(args.camera, timeout=2.0)
            except FrameTimeout:
                print("No frame within 2s — is Unity running and the Spout sender active?")
                return 1
            n += 1
            if n % 30 == 0:
                fps = n / (time.monotonic() - t0)
                print(
                    f"frame={meta.frame_index} t={meta.timestamp:.3f}s "
                    f"shape={frame.shape} fps≈{fps:.1f}"
                )
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    try:
        import SpoutGL
    except ImportError:
        print("SpoutGL not installed.", file=sys.stderr)
        return 1
    rx = SpoutGL.SpoutReceiver()
    senders = rx.getSenderList() or []
    if not senders:
        print("(no active Spout senders)")
    for s in senders:
        print(s)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="slope-poke")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("smoke", help="Smoke test: receive N frames from one camera.")
    s.add_argument("--camera", default="cameraA")
    s.add_argument("--zmq", default="tcp://127.0.0.1:5555")
    s.add_argument("--frames", type=int, default=120)
    s.set_defaults(func=cmd_smoke)

    l = sub.add_parser("list", help="List active Spout senders.")
    l.set_defaults(func=cmd_list)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
