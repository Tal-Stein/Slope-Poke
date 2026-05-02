"""Diagnostic: which half of the smoke pipeline is failing?

Run while Unity is in Play mode:
    uv run python scripts/diag.py
"""

from __future__ import annotations

import json
import time

import msgpack
import zmq

from slope_poke.simulator_client.spout_receiver import SpoutReceiver

print("--- 1. Metadata channel (ZMQ tcp://127.0.0.1:5555) ---")
ctx = zmq.Context.instance()
sub = ctx.socket(zmq.SUB)
sub.setsockopt(zmq.SUBSCRIBE, b"")
sub.RCVTIMEO = 2000
sub.connect("tcp://127.0.0.1:5555")
got_meta = False
deadline = time.monotonic() + 3.0
while time.monotonic() < deadline:
    try:
        topic, body = sub.recv_multipart()
        print(f"  got metadata topic={topic!r} bytes={len(body)}")
        decoded = msgpack.unpackb(body, raw=False)
        # Trim numeric arrays so the dump stays readable.
        if isinstance(decoded, dict):
            for key in ("intrinsics", "extrinsics"):
                if key in decoded:
                    print(f"  {key}: {decoded[key]}")
            objs = decoded.get("objects", [])
            print(f"  objects ({len(objs)}):")
            for o in objs:
                print(f"    - id={o.get('object_id')} class={o.get('class_name')!r}")
        got_meta = True
        break
    except zmq.error.Again:
        continue
if not got_meta:
    print("  NO METADATA RECEIVED in 3s — MetadataPublisher is silent.")
sub.close()

print()
print("--- 2. Spout sender (first '<id>_rgb' discovered) ---")
from slope_poke.tools import discover_cameras
cam_ids = discover_cameras()
if not cam_ids:
    print("  NO Spout senders discovered — nothing to test.")
    got_frame = False
else:
    target = cam_ids[0] + "_rgb"
    print(f"  testing sender {target!r} (of {len(cam_ids)} discovered: {cam_ids})")
    with SpoutReceiver(target) as rx:
        deadline = time.monotonic() + 3.0
        got_frame = False
        while time.monotonic() < deadline:
            f = rx.receive()
            if f is not None:
                print(f"  got frame {f.width}x{f.height}, {f.pixels.dtype}")
                got_frame = True
                break
            time.sleep(0.01)
        if not got_frame:
            print("  NO FRAME RECEIVED in 3s — SpoutReceiver isn't getting pixels.")

print()
print("Summary:")
print(f"  metadata: {'OK' if got_meta else 'FAIL'}")
print(f"  frames:   {'OK' if got_frame else 'FAIL'}")
