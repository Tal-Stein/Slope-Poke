"""Smoke-level test: example configs parse cleanly into Pydantic models."""

from pathlib import Path

from slope_poke.config import load_cameras, load_scene

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_scene_example_loads():
    cfg = load_scene(REPO_ROOT / "configs" / "scenes" / "example.json")
    assert cfg.seed == 42
    assert cfg.fixedDeltaTime > 0
    assert cfg.lighting == "directional"


def test_cameras_example_loads():
    cfg = load_cameras(REPO_ROOT / "configs" / "cameras" / "example.json")
    ids = {c.id for c in cfg.cameras}
    assert ids == {"cameraA", "ptzA"}
    ptz = next(c for c in cfg.cameras if c.rig == "ptz")
    assert ptz.ptz is not None
    assert ptz.ptz.zoom_range_mm == (15.0, 200.0)
