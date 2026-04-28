"""Slope-Poke CLI entrypoint.

Subcommands:
    smoke     Receive frames from a running Unity sim and print FPS / metadata.
    list      List active Spout senders.
    ptz       Send a one-shot pan/tilt/zoom command to a Unity PTZController.
"""

from __future__ import annotations

import argparse
import sys
import time

from .control import PTZClient, PTZCommand, PTZError
from .coverage import CoverageReceiver
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


def cmd_coverage(args: argparse.Namespace) -> int:
    from pathlib import Path

    out_path = Path(args.out)
    print(f"Subscribing to coverage stream at {args.endpoint} for {args.duration}s ...")
    with CoverageReceiver(endpoint=args.endpoint) as rx:
        deadline = time.monotonic() + args.duration
        while time.monotonic() < deadline:
            time.sleep(0.1)
        cams = list(rx.known_cameras())
        if not cams:
            print("No coverage grids received.", file=sys.stderr)
            return 1
        print(f"Received grids from {len(cams)} cameras: {cams}")
        rx.analyzer.export_map(out_path)
        print(f"Wrote heatmap to {out_path}")
        for cid in cams:
            pct = rx.analyzer.coverage_percentage(cid)
            print(f"  {cid}: {pct * 100:.1f}% covered")
    return 0


def cmd_ptz(args: argparse.Namespace) -> int:
    cmd = PTZCommand(pan=args.pan, tilt=args.tilt, zoom=args.zoom)
    try:
        with PTZClient(endpoint=args.endpoint) as client:
            client.send(cmd)
    except (PTZError, ValueError) as e:
        print(f"PTZ command failed: {e}", file=sys.stderr)
        return 1
    print(f"sent {cmd.to_json()} to {args.endpoint}")
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

    cv = sub.add_parser("coverage", help="Receive coverage grids and export heatmap PNG.")
    cv.add_argument("--endpoint", default="tcp://127.0.0.1:5557")
    cv.add_argument("--duration", type=float, default=2.0,
                    help="Seconds to listen before exporting (static rigs ship one update).")
    cv.add_argument("--out", default="coverage.png")
    cv.set_defaults(func=cmd_coverage)

    pt = sub.add_parser("ptz", help="Send one-shot PTZ command to Unity PTZController.")
    pt.add_argument("--endpoint", default="tcp://127.0.0.1:5556")
    pt.add_argument("--pan", type=float, default=None, help="Target pan (deg).")
    pt.add_argument("--tilt", type=float, default=None, help="Target tilt (deg).")
    pt.add_argument("--zoom", type=float, default=None, help="Target focal length (mm).")
    pt.set_defaults(func=cmd_ptz)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
