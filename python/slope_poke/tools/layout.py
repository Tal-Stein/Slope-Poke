"""Top-down rig layout plot — camera positions + horizontal-FOV cones + targets.

The plot uses the XZ plane (Y is up in Unity). Y of each camera is shown as a
small annotation, since horizontal placement is what coverage analysis cares about.
"""

from __future__ import annotations

import math
import time
from pathlib import Path

import matplotlib.pyplot as plt
import zmq
from matplotlib.patches import Wedge

from ..config import load_cameras
from ..config.models import CameraConfig, CamerasConfig
from ..simulator_client.metadata_subscriber import MetadataSubscriber


def _horizontal_fov_deg(cam: CameraConfig) -> float:
    intr = cam.intrinsics
    fx_pix = intr.focal_length_mm * intr.render_width / intr.sensor_size_mm[0]
    return math.degrees(2.0 * math.atan(intr.render_width / (2.0 * fx_pix)))


def _yaw_deg(cam: CameraConfig) -> float:
    """Unity yaw is around +Y (rotation_euler[1]). 0 deg = facing +Z; +90 = facing +X."""
    return cam.rotation_euler_deg[1]


def _collect_target_centroids(
    zmq_endpoint: str,
    duration: float,
) -> list[tuple[float, float, str]]:
    """Subscribe briefly and aggregate unique (object_id, class) centroids in XZ."""
    sub = MetadataSubscriber(endpoint=zmq_endpoint)
    sub.start()
    seen: dict[int, tuple[float, float, str]] = {}
    deadline = time.monotonic() + duration
    try:
        while time.monotonic() < deadline:
            for cid in list(sub._buffers.keys()):  # noqa: SLF001 — read-only snapshot
                meta = sub.latest(cid)
                if meta is None:
                    continue
                for obj in meta.objects:
                    if obj.object_id in seen:
                        continue
                    if not obj.bbox_3d:
                        continue
                    xs = [c[0] for c in obj.bbox_3d]
                    zs = [c[2] for c in obj.bbox_3d]
                    cx = sum(xs) / len(xs)
                    cz = sum(zs) / len(zs)
                    seen[obj.object_id] = (cx, cz, obj.class_name)
            time.sleep(0.05)
    finally:
        sub.stop()
    return list(seen.values())


def plot_layout(
    config: CamerasConfig | str | Path,
    out_path: Path | str | None = None,
    show: bool = False,
    with_targets: bool = False,
    target_subscription_seconds: float = 1.0,
    zmq_endpoint: str = "tcp://127.0.0.1:5555",
) -> Path | None:
    """Draw the top-down layout. Returns the output path if `out_path` was given."""
    if isinstance(config, (str, Path)):
        config = load_cameras(Path(config))

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, alpha=0.3)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Z (m)")
    ax.set_title(f"Rig layout — {len(config.cameras)} cameras (top-down)")

    fov_color = "#4a90e2"
    cam_color = "#222"
    cone_radius = _suggest_cone_radius(config)

    for cam in config.cameras:
        x, _, z = cam.position
        yaw = _yaw_deg(cam)
        hfov = _horizontal_fov_deg(cam)

        # Wedge expects theta1, theta2 measured CCW from the +X axis. Unity yaw
        # is CW from +Z when viewed from above. Convert: matplotlib_theta = 90 - yaw.
        center_theta = 90.0 - yaw
        theta1 = center_theta - hfov / 2
        theta2 = center_theta + hfov / 2
        wedge = Wedge((x, z), cone_radius, theta1, theta2,
                      alpha=0.15, color=fov_color, zorder=1)
        ax.add_patch(wedge)

        ax.scatter([x], [z], c=cam_color, s=40, zorder=3)
        ax.annotate(f"{cam.id} (y={cam.position[1]:.1f})",
                    (x, z), textcoords="offset points", xytext=(6, 6),
                    fontsize=8, color=cam_color)

    if with_targets:
        targets = _collect_target_centroids(zmq_endpoint, target_subscription_seconds)
        if targets:
            tx = [t[0] for t in targets]
            tz = [t[1] for t in targets]
            ax.scatter(tx, tz, c="#e25c5c", s=60, marker="x",
                       label=f"{len(targets)} targets", zorder=4)
            for cx, cz, name in targets:
                ax.annotate(name, (cx, cz), textcoords="offset points",
                            xytext=(5, -10), fontsize=7, color="#a03030")
            ax.legend(loc="lower right", fontsize=9)
        else:
            print("(--with-targets) no annotated objects observed during subscription window.")

    fig.tight_layout()
    if out_path is not None:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=120)
        print(f"Wrote layout to {out}")
    if show:
        plt.show()
    plt.close(fig)
    return Path(out_path) if out_path is not None else None


def _suggest_cone_radius(config: CamerasConfig) -> float:
    """Pick a cone-overlay length that's visually meaningful relative to rig spread."""
    if not config.cameras:
        return 1.0
    xs = [c.position[0] for c in config.cameras]
    zs = [c.position[2] for c in config.cameras]
    spread = max(max(xs) - min(xs), max(zs) - min(zs), 1.0)
    return spread * 0.25
