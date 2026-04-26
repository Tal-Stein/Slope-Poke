from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CameraIntrinsics(BaseModel):
    fx: float
    fy: float
    cx: float
    cy: float
    width: int
    height: int
    distortion: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0, 0.0])
    """Brown-Conrady [k1, k2, p1, p2, k3] in OpenCV order."""

    def as_opencv_matrix(self) -> list[list[float]]:
        return [[self.fx, 0.0, self.cx], [0.0, self.fy, self.cy], [0.0, 0.0, 1.0]]


class CameraExtrinsics(BaseModel):
    """4x4 row-major world->camera (OpenCV convention: +Z forward, +Y down)."""

    matrix: list[list[float]]


class ObjectAnnotation(BaseModel):
    object_id: int
    class_name: str
    world_pose: list[list[float]]  # 4x4
    bbox_3d: list[list[float]]  # 8x3 corner points in world space


class FrameMeta(BaseModel):
    camera_id: str
    frame_index: int
    timestamp: float  # Unity sim time, seconds
    sender: Literal["rgb", "seg"] = "rgb"
    intrinsics: CameraIntrinsics
    extrinsics: CameraExtrinsics
    objects: list[ObjectAnnotation] = Field(default_factory=list)
