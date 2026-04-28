"""RunReplayer — iterate a recorded run for deterministic playback."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from .models import (
    ObjectStateEvent,
    PTZCommandEvent,
    Recording,
    RecordingEvent,
)


class RunReplayer:
    def __init__(self, recording: Recording):
        self.recording = recording

    @classmethod
    def from_path(cls, path: Path) -> "RunReplayer":
        return cls(Recording.model_validate_json(Path(path).read_text()))

    def events(self) -> Iterator[RecordingEvent]:
        # Stable timestamp sort: events at the same instant preserve insertion order.
        yield from sorted(self.recording.events, key=lambda e: e.timestamp)

    def ptz_commands(self) -> Iterator[PTZCommandEvent]:
        for e in self.events():
            if isinstance(e, PTZCommandEvent):
                yield e

    def object_states(self) -> Iterator[ObjectStateEvent]:
        for e in self.events():
            if isinstance(e, ObjectStateEvent):
                yield e

    @property
    def duration(self) -> float:
        if not self.recording.events:
            return 0.0
        return max(e.timestamp for e in self.recording.events)
