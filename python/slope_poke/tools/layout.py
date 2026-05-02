"""3D rig layout plot — camera positions, view frustums, and target centroids.

The plot uses Unity's coordinate convention with Y up. Matplotlib's default 3D
view treats Z as vertical, so we swap on plot: data point (Ux, Uy, Uz) →
matplotlib (Ux, Uz, Uy). That keeps the visual "up" of the plot aligned with
the scene's "up", which matches user intuition when comparing to Unity.
"""

from __future__ import annotations

import math
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: F401  (registers projection)

from ..config import load_cameras
from ..config.models import CameraConfig, CamerasConfig
from ..simulator_client.metadata_subscriber import MetadataSubscriber


def _horizontal_fov_rad(cam: CameraConfig) -> float:
    intr = cam.intrinsics
    fx_pix = intr.focal_length_mm * intr.render_width / intr.sensor_size_mm[0]
    return 2.0 * math.atan(intr.render_width / (2.0 * fx_pix))


def _vertical_fov_rad(cam: CameraConfig) -> float:
    intr = cam.intrinsics
    fy_pix = intr.focal_length_mm * intr.render_height / intr.sensor_size_mm[1]
    return 2.0 * math.atan(intr.render_height / (2.0 * fy_pix))


def _unity_euler_to_matrix(pitch_deg: float, yaw_deg: float, roll_deg: float) -> np.ndarray:
    """Unity applies rotations Z (roll), then X (pitch), then Y (yaw).

    Composed for a column vector: R = Ry @ Rx @ Rz.
    Verified: pitch=90, yaw=0 sends +Z forward to -Y (camera looks down).
              pitch=0, yaw=-90 sends +Z forward to -X (camera looks left).
    """
    p, y, r = map(math.radians, (pitch_deg, yaw_deg, roll_deg))
    cx, sx = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(r), math.sin(r)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def _frustum_corners_world(cam: CameraConfig, length: float) -> np.ndarray:
    """Return the 4 far-plane corners of the camera frustum in world coords.

    Order: top-left, top-right, bottom-right, bottom-left when viewed from
    behind the camera looking through it.
    """
    h = math.tan(_horizontal_fov_rad(cam) / 2.0) * length
    v = math.tan(_vertical_fov_rad(cam) / 2.0) * length
    # Camera-local: +X right, +Y up, +Z forward.
    local = np.array([
        [-h,  v, length],   # top-left
        [ h,  v, length],   # top-right
        [ h, -v, length],   # bottom-right
        [-h, -v, length],   # bottom-left
    ])
    R = _unity_euler_to_matrix(*cam.rotation_euler_deg)
    pos = np.array(cam.position)
    return (local @ R.T) + pos  # shape (4, 3)


def _draw_frustum(ax, cam: CameraConfig, length: float, color: str) -> None:
    corners = _frustum_corners_world(cam, length)
    origin = np.array(cam.position)
    # 4 rays from origin to each far-plane corner.
    for c in corners:
        ax.plot([origin[0], c[0]], [origin[2], c[2]], [origin[1], c[1]],
                color=color, alpha=0.5, linewidth=0.8)
    # Far-plane rectangle.
    rect = np.vstack([corners, corners[0]])
    ax.plot(rect[:, 0], rect[:, 2], rect[:, 1],
            color=color, alpha=0.5, linewidth=0.8)


def _draw_floor(ax, half_size: float, y: float = 0.0) -> None:
    floor = np.array([
        [-half_size, y, -half_size],
        [ half_size, y, -half_size],
        [ half_size, y,  half_size],
        [-half_size, y,  half_size],
    ])
    poly = Poly3DCollection([list(zip(floor[:, 0], floor[:, 2], floor[:, 1]))],
                            alpha=0.08, facecolor="#7f7f7f", edgecolor="#444")
    ax.add_collection3d(poly)


def _collect_target_centroids(
    zmq_endpoint: str,
    duration: float,
) -> list[tuple[float, float, float, str]]:
    """Subscribe briefly and aggregate (x, y, z, class_name) per unique object."""
    sub = MetadataSubscriber(endpoint=zmq_endpoint)
    sub.start()
    seen: dict[int, tuple[float, float, float, str]] = {}
    deadline = time.monotonic() + duration
    try:
        while time.monotonic() < deadline:
            for cid in list(sub._buffers.keys()):  # noqa: SLF001 — read-only snapshot
                meta = sub.latest(cid)
                if meta is None:
                    continue
                for obj in meta.objects:
                    if obj.object_id in seen or not obj.bbox_3d:
                        continue
                    xs = [c[0] for c in obj.bbox_3d]
                    ys = [c[1] for c in obj.bbox_3d]
                    zs = [c[2] for c in obj.bbox_3d]
                    cx = sum(xs) / len(xs)
                    cy = sum(ys) / len(ys)
                    cz = sum(zs) / len(zs)
                    seen[obj.object_id] = (cx, cy, cz, obj.class_name)
            time.sleep(0.05)
    finally:
        sub.stop()
    return list(seen.values())


def _suggest_frustum_length(config: CamerasConfig) -> float:
    if not config.cameras:
        return 1.0
    xs = [c.position[0] for c in config.cameras]
    zs = [c.position[2] for c in config.cameras]
    spread = max(max(xs) - min(xs), max(zs) - min(zs), 1.0)
    return spread * 0.3


def _set_equal_3d_aspect(ax, xs, ys, zs) -> None:
    """matplotlib 3D doesn't support 'equal' directly; emulate via box aspect."""
    spans = [max(np.ptp(a), 1.0) for a in (xs, ys, zs)]
    ax.set_box_aspect(spans)


def plot_layout(
    config: CamerasConfig | str | Path,
    out_path: Path | str | None = None,
    show: bool = False,
    with_targets: bool = False,
    target_subscription_seconds: float = 1.0,
    zmq_endpoint: str = "tcp://127.0.0.1:5555",
    show_floor: bool = True,
    floor_y: float = 0.0,
    frustum_length: float | None = None,
    view_angle: tuple[float, float] = (25.0, -60.0),
) -> Path | None:
    """Render a 3D rig layout. Returns the output path if `out_path` was given."""
    if isinstance(config, (str, Path)):
        config = load_cameras(Path(config))

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    ax.view_init(elev=view_angle[0], azim=view_angle[1])
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Z (m)")
    ax.set_zlabel("Y / up (m)")
    ax.set_title(f"Rig layout — {len(config.cameras)} cameras (3D)")
    ax.grid(True, alpha=0.3)

    flen = frustum_length if frustum_length is not None else _suggest_frustum_length(config)
    cam_color = "#222"
    frustum_color = "#4a90e2"

    cam_xs, cam_ys, cam_zs = [], [], []
    for cam in config.cameras:
        x, y, z = cam.position
        # plot uses (X, Z, Y) so the plot's vertical axis = Unity's up.
        ax.scatter([x], [z], [y], c=cam_color, s=30, zorder=3)
        ax.text(x, z, y + 0.1, cam.id, fontsize=7, color=cam_color)
        _draw_frustum(ax, cam, flen, frustum_color)
        cam_xs.append(x); cam_ys.append(y); cam_zs.append(z)

    floor_half = max(abs(min(cam_xs, default=0)), abs(max(cam_xs, default=0)),
                     abs(min(cam_zs, default=0)), abs(max(cam_zs, default=0)),
                     1.0) * 1.1
    if show_floor:
        _draw_floor(ax, floor_half, floor_y)

    if with_targets:
        targets = _collect_target_centroids(zmq_endpoint, target_subscription_seconds)
        if targets:
            tx = [t[0] for t in targets]
            ty = [t[1] for t in targets]
            tz = [t[2] for t in targets]
            ax.scatter(tx, tz, ty, c="#e25c5c", s=50, marker="x",
                       label=f"{len(targets)} targets", zorder=4)
            for cx, cy, cz, name in targets:
                ax.text(cx, cz, cy + 0.1, name, fontsize=6, color="#a03030")
            ax.legend(loc="upper right", fontsize=9)
        else:
            print("(--with-targets) no annotated objects observed during subscription window.")

    # Equal-ish aspect so geometry doesn't get squashed in any axis.
    all_x = cam_xs + ([floor_half, -floor_half] if show_floor else [])
    all_y = cam_ys + ([floor_y] if show_floor else [])
    all_z = cam_zs + ([floor_half, -floor_half] if show_floor else [])
    _set_equal_3d_aspect(ax, all_x, all_z, all_y)

    fig.tight_layout()
    if out_path is not None:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=120)
        print(f"Wrote 3D layout to {out}")
    if show:
        plt.show()
    plt.close(fig)
    return Path(out_path) if out_path is not None else None
