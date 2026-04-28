"""Pydantic schema for recording.json.

Two-tier philosophy: the seed + scene_config + camera_config plus all PTZ commands
are sufficient to deterministically rerun the sim. The object snapshots are
recorded on top so consumers that don't want to spin Unity (e.g. an algorithm
benchmark harness) can replay ground-truth trajectories straight from JSON.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from ..config.models import CamerasConfig, SceneConfig


class PTZCommandEvent(BaseModel):
    kind: Literal["ptz"] = "ptz"
    timestamp: float
    camera_id: str
    pan: float | None = None
    tilt: float | None = None
    zoom: float | None = None


class ObjectSnapshot(BaseModel):
    object_id: int
    class_name: str
    world_pose: list[list[float]]
    bbox_3d: list[list[float]]


class ObjectStateEvent(BaseModel):
    kind: Literal["object_state"] = "object_state"
    timestamp: float
    objects: list[ObjectSnapshot] = Field(default_factory=list)


RecordingEvent = Annotated[
    Union[PTZCommandEvent, ObjectStateEvent],
    Field(discriminator="kind"),
]


class Recording(BaseModel):
    version: int = 1
    scene: SceneConfig
    cameras: CamerasConfig
    events: list[RecordingEvent] = Field(default_factory=list)
