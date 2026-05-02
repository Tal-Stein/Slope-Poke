"""Tests for slope_poke.tools.projection.

The Unity side ships extrinsics in OpenCV convention already, so identity
extrinsics + simple intrinsics give us textbook projection results we can hand-check.
"""

import math

import pytest

from slope_poke.simulator_client.types import CameraExtrinsics, CameraIntrinsics
from slope_poke.tools.projection import (
    BBOX_EDGES,
    project_bbox_3d,
    project_world_to_pixel,
)


def _intrinsics(fx=500.0, fy=500.0, cx=960.0, cy=540.0, w=1920, h=1080) -> CameraIntrinsics:
    return CameraIntrinsics(fx=fx, fy=fy, cx=cx, cy=cy, width=w, height=h)


def _identity_extrinsics() -> CameraExtrinsics:
    return CameraExtrinsics(matrix=[
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ])


def test_identity_pose_projects_to_principal_point():
    # World point on the optical axis at z=5 → projects to (cx, cy).
    u, v = project_world_to_pixel([0, 0, 5], _intrinsics(), _identity_extrinsics())
    assert u == pytest.approx(960.0)
    assert v == pytest.approx(540.0)


def test_off_axis_point_uses_focal_length():
    intr = _intrinsics(fx=500.0, fy=500.0, cx=960.0, cy=540.0)
    # (1, 0, 5) → u offset = fx * 1/5 = 100, so u = 1060.
    u, v = project_world_to_pixel([1, 0, 5], intr, _identity_extrinsics())
    assert u == pytest.approx(1060.0)
    assert v == pytest.approx(540.0)


def test_point_behind_camera_returns_none():
    assert project_world_to_pixel([0, 0, -2], _intrinsics(), _identity_extrinsics()) is None
    assert project_world_to_pixel([0, 0, 0], _intrinsics(), _identity_extrinsics()) is None


def test_translation_in_extrinsics_shifts_point():
    # Translate world by (-1, 0, 0) before projection: world point (1, 0, 5)
    # ends up at camera-frame (0, 0, 5) → projects to principal point.
    extr = CameraExtrinsics(matrix=[
        [1.0, 0.0, 0.0, -1.0],
        [0.0, 1.0, 0.0,  0.0],
        [0.0, 0.0, 1.0,  0.0],
        [0.0, 0.0, 0.0,  1.0],
    ])
    u, v = project_world_to_pixel([1, 0, 5], _intrinsics(), extr)
    assert u == pytest.approx(960.0)
    assert v == pytest.approx(540.0)


def test_bbox_corner_order_matches_edge_indices():
    """The corner order produced by AnnotatedObject.cs must let BBOX_EDGES form
    a cube. We replicate that order here and verify each edge connects corners
    that differ in exactly one axis (the hallmark of a cube wireframe)."""
    # Mirror AnnotatedObject's order for a unit cube min=(0,0,0), max=(1,1,1).
    corners = [
        (0, 0, 0),  # 0
        (1, 0, 0),  # 1
        (1, 1, 0),  # 2
        (0, 1, 0),  # 3
        (0, 0, 1),  # 4
        (1, 0, 1),  # 5
        (1, 1, 1),  # 6
        (0, 1, 1),  # 7
    ]
    for a, b in BBOX_EDGES:
        diff = sum(1 for ax, bx in zip(corners[a], corners[b]) if ax != bx)
        assert diff == 1, f"edge ({a},{b}) connects {corners[a]} and {corners[b]} — not adjacent"
    assert len(BBOX_EDGES) == 12  # exactly 12 edges in a cube


def test_project_bbox_returns_eight_results():
    corners = [(0, 0, 5), (1, 0, 5), (1, 1, 5), (0, 1, 5),
               (0, 0, 6), (1, 0, 6), (1, 1, 6), (0, 1, 6)]
    pts = project_bbox_3d(corners, _intrinsics(), _identity_extrinsics())
    assert len(pts) == 8
    assert all(p is not None for p in pts)


def test_horizontal_fov_recoverable_from_intrinsics():
    """Sanity: render_width=1920, fx=500 → horizontal FOV ≈ 2*atan(960/500) ≈ 124°."""
    intr = _intrinsics()
    fov_rad = 2 * math.atan(intr.width / (2 * intr.fx))
    assert math.degrees(fov_rad) == pytest.approx(125.06, abs=0.5)
