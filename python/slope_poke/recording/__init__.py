"""Record/replay support — every run writes a recording.json that fully determines
playback. Captures scene init state, every PTZ command with its timestamp, and
object trajectory snapshots so replays don't need to re-run the RNG.
"""

from .models import (
    ObjectSnapshot,
    ObjectStateEvent,
    PTZCommandEvent,
    Recording,
    RecordingEvent,
)
from .recorder import RunRecorder
from .replayer import RunReplayer

__all__ = [
    "ObjectSnapshot",
    "ObjectStateEvent",
    "PTZCommandEvent",
    "Recording",
    "RecordingEvent",
    "RunRecorder",
    "RunReplayer",
]
