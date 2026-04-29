"""Behavioural tests for slope_poke.config.generators.

The Unity-side CamerasLoader trusts the JSON schema generated here, so the
contract worth pinning is: count, IDs, and that look-at math points at the target
(within float tolerance).
"""

import math

import pytest

from slope_poke.config import generators


def test_ring_count_and_unique_ids():
    cfg = generators.ring(n=12, radius=5.0)
    assert len(cfg.cameras) == 12
    assert len({c.id for c in cfg.cameras}) == 12


def test_ring_positions_are_on_circle():
    cfg = generators.ring(n=8, radius=4.0, height=2.0, look_at=(1.0, 0.0, -1.0))
    for c in cfg.cameras:
        x, y, z = c.position
        # Project onto the XZ plane around the look_at center.
        d = math.hypot(x - 1.0, z - (-1.0))
        assert d == pytest.approx(4.0, abs=1e-4)
        assert y == pytest.approx(2.0)


def test_grid_count_and_centered():
    cfg = generators.grid(rows=3, cols=4, spacing=2.0, height=5.0)
    assert len(cfg.cameras) == 12
    # Mean position should sit at the look_at xz (origin) with height = 5.
    mx = sum(c.position[0] for c in cfg.cameras) / 12
    mz = sum(c.position[2] for c in cfg.cameras) / 12
    assert mx == pytest.approx(0.0, abs=1e-6)
    assert mz == pytest.approx(0.0, abs=1e-6)
    assert all(c.position[1] == pytest.approx(5.0) for c in cfg.cameras)


def test_random_in_box_is_deterministic_for_same_seed():
    a = generators.random_in_box(n=20, bounds_min=(-1, 0, -1), bounds_max=(1, 2, 1), seed=42)
    b = generators.random_in_box(n=20, bounds_min=(-1, 0, -1), bounds_max=(1, 2, 1), seed=42)
    assert [c.position for c in a.cameras] == [c.position for c in b.cameras]


def test_random_in_box_respects_bounds():
    cfg = generators.random_in_box(n=50, bounds_min=(-3, 0, -3), bounds_max=(3, 4, 3), seed=1)
    for c in cfg.cameras:
        x, y, z = c.position
        assert -3 <= x <= 3
        assert 0 <= y <= 4
        assert -3 <= z <= 3


def test_look_at_yaw_aims_at_target():
    # Camera placed at +X axis looking back at the origin should yaw to -90 deg
    # (Unity yaw is around +Y, +Z is forward → facing -X means yaw = -90).
    cfg = generators.look_at_all(positions=[(5.0, 0.0, 0.0)], target=(0.0, 0.0, 0.0))
    pitch, yaw, roll = cfg.cameras[0].rotation_euler_deg
    assert yaw == pytest.approx(-90.0, abs=1e-4)
    assert pitch == pytest.approx(0.0, abs=1e-4)
    assert roll == pytest.approx(0.0, abs=1e-4)


def test_look_at_pitch_for_overhead_camera():
    # Camera 5m above origin pointing down → pitch +90 deg (looking down).
    cfg = generators.look_at_all(positions=[(0.0, 5.0, 0.0)], target=(0.0, 0.0, 0.0))
    pitch, yaw, _ = cfg.cameras[0].rotation_euler_deg
    assert pitch == pytest.approx(90.0, abs=1e-3)
