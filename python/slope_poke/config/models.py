"""Pydantic mirrors of configs/*.json — single source of truth on the Python side.

The Unity project parses the same files via JsonUtility. Keep field names in sync.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class Vec3(BaseModel):
    x: float
    y: float
    z: float


class SceneObject(BaseModel):
    prefab: str
    path: list[list[float]] = Field(default_factory=list)
    speed: float = 1.0


class SceneConfig(BaseModel):
    seed: int = 42
    fixedDeltaTime: float = 1.0 / 60.0
    roomMaterial: str = "default"
    roomDimensions: Vec3 = Vec3(x=10.0, y=3.0, z=10.0)
    lighting: Literal["directional", "point", "area", "skybox"] = "directional"
    objects: list[SceneObject] = Field(default_factory=list)


class IntrinsicsCfg(BaseModel):
    focal_length_mm: float = 35.0
    sensor_size_mm: tuple[float, float] = (36.0, 24.0)
    principal_point_px: tuple[float, float] = (0.0, 0.0)
    render_width: int = 1920
    render_height: int = 1080


class DistortionCfg(BaseModel):
    k1: float = 0.0
    k2: float = 0.0
    p1: float = 0.0
    p2: float = 0.0
    k3: float = 0.0


class NoiseCfg(BaseModel):
    gaussian_sigma: float = 0.0
    salt_pepper_rate: float = 0.0


class OpticsCfg(BaseModel):
    shutter_angle_deg: float = 180.0
    aperture_fstop: float = 5.6
    focus_distance_m: float = 5.0
    exposure_compensation_ev: float = 0.0


class PTZCfg(BaseModel):
    pan_range_deg: tuple[float, float] = (-180.0, 180.0)
    tilt_range_deg: tuple[float, float] = (-90.0, 30.0)
    zoom_range_mm: tuple[float, float] = (15.0, 200.0)
    max_pan_rate_deg_s: float = 120.0
    max_tilt_rate_deg_s: float = 90.0


class CameraConfig(BaseModel):
    id: str
    rig: Literal["mono", "multi", "ptz"]
    position: tuple[float, float, float] = (0.0, 1.6, 0.0)
    rotation_euler_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)
    intrinsics: IntrinsicsCfg = Field(default_factory=IntrinsicsCfg)
    distortion: DistortionCfg = Field(default_factory=DistortionCfg)
    noise: NoiseCfg = Field(default_factory=NoiseCfg)
    optics: OpticsCfg = Field(default_factory=OpticsCfg)
    ptz: PTZCfg | None = None


class CamerasConfig(BaseModel):
    cameras: list[CameraConfig]


def load_scene(path: Path) -> SceneConfig:
    return SceneConfig.model_validate_json(Path(path).read_text())


def load_cameras(path: Path) -> CamerasConfig:
    raw = json.loads(Path(path).read_text())
    raw.pop("$schema", None)
    return CamerasConfig.model_validate(raw)
