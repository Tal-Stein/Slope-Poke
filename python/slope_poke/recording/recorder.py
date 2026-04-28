"""RunRecorder — append-only log of a single sim run."""

from __future__ import annotations

from pathlib import Path

from ..config.models import CamerasConfig, SceneConfig
from .models import (
    ObjectSnapshot,
    ObjectStateEvent,
    PTZCommandEvent,
    Recording,
    RecordingEvent,
)


class RunRecorder:
    def __init__(self, scene: SceneConfig, cameras: CamerasConfig):
        self._recording = Recording(scene=scene, cameras=cameras)

    def add_ptz(
        self,
        camera_id: str,
        timestamp: float,
        pan: float | None = None,
        tilt: float | None = None,
        zoom: float | None = None,
    ) -> None:
        self._recording.events.append(
            PTZCommandEvent(
                timestamp=timestamp,
                camera_id=camera_id,
                pan=pan,
                tilt=tilt,
                zoom=zoom,
            )
        )

    def add_object_state(self, timestamp: float, objects: list[ObjectSnapshot]) -> None:
        self._recording.events.append(
            ObjectStateEvent(timestamp=timestamp, objects=list(objects))
        )

    def add_event(self, event: RecordingEvent) -> None:
        self._recording.events.append(event)

    @property
    def recording(self) -> Recording:
        return self._recording

    def write(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._recording.model_dump_json(indent=2))
        return path
