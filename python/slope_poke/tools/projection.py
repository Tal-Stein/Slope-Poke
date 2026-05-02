"""Pinhole projection helpers shared by the tile viewer and any future overlay code.

The Unity side already converts extrinsics to OpenCV convention (Y down, +Z forward
from the camera). See VirtualCamera.GetWorldPoseRowMajor() in
unity-project/Assets/Scripts/Cameras/VirtualCamera.cs — it row-flips Y on the
world-to-camera matrix before shipping. So projection here is the textbook OpenCV
pinhole: P_camera = extrinsics @ P_world; (u, v) = (fx * x/z + cx, fy * y/z + cy).
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from ..simulator_client.types import CameraExtrinsics, CameraIntrinsics

# Edge list for the 8 corners produced by AnnotatedObject.BoundingBoxWorld() in
# unity-project/Assets/Scripts/Scene/AnnotatedObject.cs:43-58. Corners enumerate
# z=min square first (CCW from min XY), then z=max square in the same order.
#   0: (min, min, min)   4: (min, min, max)
#   1: (max, min, min)   5: (max, min, max)
#   2: (max, max, min)   6: (max, max, max)
#   3: (min, max, min)   7: (min, max, max)
BBOX_EDGES: list[tuple[int, int]] = [
    # Bottom square (z = min)
    (0, 1), (1, 2), (2, 3), (3, 0),
    # Top square (z = max)
    (4, 5), (5, 6), (6, 7), (7, 4),
    # Vertical pillars connecting bottom to top
    (0, 4), (1, 5), (2, 6), (3, 7),
]


def project_world_to_pixel(
    point_world: Sequence[float],
    intrinsics: CameraIntrinsics,
    extrinsics: CameraExtrinsics,
) -> tuple[float, float] | None:
    """Project a single world-space point to pixel coords.

    Returns None for points behind the camera (z <= 0 in camera frame).
    Distortion is intentionally ignored in v1 — Brown-Conrady can be layered on
    top by warping (u, v) before returning.
    """
    p_w = np.array([point_world[0], point_world[1], point_world[2], 1.0], dtype=np.float64)
    extr = np.asarray(extrinsics.matrix, dtype=np.float64)
    p_c = extr @ p_w
    z = p_c[2]
    if z <= 1e-6:
        return None
    u = intrinsics.fx * (p_c[0] / z) + intrinsics.cx
    v = intrinsics.fy * (p_c[1] / z) + intrinsics.cy
    return float(u), float(v)


def project_bbox_3d(
    corners_world: Sequence[Sequence[float]],
    intrinsics: CameraIntrinsics,
    extrinsics: CameraExtrinsics,
) -> list[tuple[float, float] | None]:
    """Project the 8 corners of a 3D bounding box. Order must match BBOX_EDGES."""
    return [project_world_to_pixel(c, intrinsics, extrinsics) for c in corners_world]
