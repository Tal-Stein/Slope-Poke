"""Programmatic camera-array generators.

Each generator returns a :class:`~slope_poke.config.models.CamerasConfig` you
can either pass to Python algorithms directly or write to JSON for the Unity
CamerasLoader to pick up.

All generators share resolution and sensor kwargs so a single experiment can
be replicated at multiple render budgets without rewriting placement logic.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable

from .models import (
    CameraConfig,
    CamerasConfig,
    DistortionCfg,
    IntrinsicsCfg,
    NoiseCfg,
    OpticsCfg,
)


def _intrinsics(
    width: int,
    height: int,
    focal_length_mm: float,
    sensor_size_mm: tuple[float, float],
) -> IntrinsicsCfg:
    return IntrinsicsCfg(
        focal_length_mm=focal_length_mm,
        sensor_size_mm=sensor_size_mm,
        render_width=width,
        render_height=height,
    )


def _camera(
    id: str,
    position: tuple[float, float, float],
    rotation_euler_deg: tuple[float, float, float],
    width: int,
    height: int,
    focal_length_mm: float,
    sensor_size_mm: tuple[float, float],
) -> CameraConfig:
    return CameraConfig(
        id=id,
        rig="mono",
        position=position,
        rotation_euler_deg=rotation_euler_deg,
        intrinsics=_intrinsics(width, height, focal_length_mm, sensor_size_mm),
        distortion=DistortionCfg(),
        noise=NoiseCfg(),
        optics=OpticsCfg(),
    )


def _euler_look_at(
    position: tuple[float, float, float],
    target: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Unity-convention pitch/yaw/roll (deg) for a camera at `position` looking at `target`.

    Unity uses left-handed +Y-up, +Z-forward. Yaw rotates around Y, pitch around X
    (screen-up axis is +Y), roll around Z (zero by convention). The PTZController
    uses the same convention.
    """
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    dz = target[2] - position[2]
    yaw_rad = math.atan2(dx, dz)
    horizontal = math.hypot(dx, dz)
    pitch_rad = -math.atan2(dy, horizontal)
    return (math.degrees(pitch_rad), math.degrees(yaw_rad), 0.0)


def ring(
    n: int,
    radius: float,
    height: float = 1.6,
    look_at: tuple[float, float, float] = (0.0, 1.0, 0.0),
    *,
    width: int = 1920,
    image_height: int = 1080,
    focal_length_mm: float = 35.0,
    sensor_size_mm: tuple[float, float] = (36.0, 24.0),
    id_prefix: str = "ring",
) -> CamerasConfig:
    """`n` cameras evenly spaced on a circle of radius `radius` at altitude `height`,
    each looking at `look_at`."""
    if n <= 0:
        raise ValueError("ring(n) requires n > 0")
    cx, _, cz = look_at[0], 0.0, look_at[2]
    cams: list[CameraConfig] = []
    for i in range(n):
        theta = 2.0 * math.pi * i / n
        pos = (cx + radius * math.cos(theta), height, cz + radius * math.sin(theta))
        cams.append(
            _camera(
                id=f"{id_prefix}{i:02d}",
                position=pos,
                rotation_euler_deg=_euler_look_at(pos, look_at),
                width=width,
                height=image_height,
                focal_length_mm=focal_length_mm,
                sensor_size_mm=sensor_size_mm,
            )
        )
    return CamerasConfig(cameras=cams)


def grid(
    rows: int,
    cols: int,
    spacing: float,
    height: float = 3.0,
    look_at: tuple[float, float, float] = (0.0, 0.0, 0.0),
    *,
    width: int = 1920,
    image_height: int = 1080,
    focal_length_mm: float = 35.0,
    sensor_size_mm: tuple[float, float] = (36.0, 24.0),
    id_prefix: str = "grid",
) -> CamerasConfig:
    """`rows × cols` cameras on a horizontal grid centered at the origin, all pointing
    down toward `look_at`."""
    if rows <= 0 or cols <= 0:
        raise ValueError("grid(rows, cols) requires both > 0")
    cams: list[CameraConfig] = []
    x0 = -spacing * (cols - 1) / 2
    z0 = -spacing * (rows - 1) / 2
    for r in range(rows):
        for c in range(cols):
            pos = (x0 + c * spacing, height, z0 + r * spacing)
            cams.append(
                _camera(
                    id=f"{id_prefix}_{r:02d}_{c:02d}",
                    position=pos,
                    rotation_euler_deg=_euler_look_at(pos, look_at),
                    width=width,
                    height=image_height,
                    focal_length_mm=focal_length_mm,
                    sensor_size_mm=sensor_size_mm,
                )
            )
    return CamerasConfig(cameras=cams)


def random_in_box(
    n: int,
    bounds_min: tuple[float, float, float],
    bounds_max: tuple[float, float, float],
    look_at: tuple[float, float, float] = (0.0, 0.0, 0.0),
    seed: int = 0,
    *,
    width: int = 1920,
    image_height: int = 1080,
    focal_length_mm: float = 35.0,
    sensor_size_mm: tuple[float, float] = (36.0, 24.0),
    id_prefix: str = "rand",
) -> CamerasConfig:
    """`n` cameras placed uniformly at random inside an axis-aligned box."""
    if n <= 0:
        raise ValueError("random_in_box(n) requires n > 0")
    rng = random.Random(seed)
    cams: list[CameraConfig] = []
    for i in range(n):
        pos = (
            rng.uniform(bounds_min[0], bounds_max[0]),
            rng.uniform(bounds_min[1], bounds_max[1]),
            rng.uniform(bounds_min[2], bounds_max[2]),
        )
        cams.append(
            _camera(
                id=f"{id_prefix}{i:03d}",
                position=pos,
                rotation_euler_deg=_euler_look_at(pos, look_at),
                width=width,
                height=image_height,
                focal_length_mm=focal_length_mm,
                sensor_size_mm=sensor_size_mm,
            )
        )
    return CamerasConfig(cameras=cams)


def look_at_all(
    positions: Iterable[tuple[float, float, float]],
    target: tuple[float, float, float],
    *,
    width: int = 1920,
    image_height: int = 1080,
    focal_length_mm: float = 35.0,
    sensor_size_mm: tuple[float, float] = (36.0, 24.0),
    id_prefix: str = "cam",
) -> CamerasConfig:
    """Construct cameras from an explicit list of positions, all aimed at `target`."""
    cams: list[CameraConfig] = []
    for i, pos in enumerate(positions):
        cams.append(
            _camera(
                id=f"{id_prefix}{i:03d}",
                position=tuple(pos),
                rotation_euler_deg=_euler_look_at(tuple(pos), target),
                width=width,
                height=image_height,
                focal_length_mm=focal_length_mm,
                sensor_size_mm=sensor_size_mm,
            )
        )
    if not cams:
        raise ValueError("look_at_all() requires at least one position")
    return CamerasConfig(cameras=cams)
