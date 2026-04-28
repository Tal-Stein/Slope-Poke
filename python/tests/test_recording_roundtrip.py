"""Recording → JSON → Recording must preserve event order and discriminate kinds."""

from pathlib import Path

from slope_poke.config import load_cameras, load_scene
from slope_poke.recording import (
    ObjectSnapshot,
    ObjectStateEvent,
    PTZCommandEvent,
    RunRecorder,
    RunReplayer,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_recorder() -> RunRecorder:
    scene = load_scene(REPO_ROOT / "configs" / "scenes" / "example.json")
    cameras = load_cameras(REPO_ROOT / "configs" / "cameras" / "example.json")
    return RunRecorder(scene=scene, cameras=cameras)


def test_recording_roundtrip(tmp_path):
    rec = _make_recorder()
    rec.add_ptz("ptzA", timestamp=0.5, pan=10.0)
    rec.add_ptz("ptzA", timestamp=1.0, tilt=-5.0, zoom=80.0)
    rec.add_object_state(
        timestamp=0.75,
        objects=[
            ObjectSnapshot(
                object_id=1,
                class_name="cube",
                world_pose=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
                bbox_3d=[[0, 0, 0]] * 8,
            )
        ],
    )

    path = rec.write(tmp_path / "recording.json")
    rep = RunReplayer.from_path(path)

    events = list(rep.events())
    assert [e.timestamp for e in events] == [0.5, 0.75, 1.0]

    ptz = list(rep.ptz_commands())
    assert all(isinstance(e, PTZCommandEvent) for e in ptz)
    assert ptz[0].pan == 10.0 and ptz[0].tilt is None
    assert ptz[1].zoom == 80.0

    state = list(rep.object_states())
    assert len(state) == 1
    assert isinstance(state[0], ObjectStateEvent)
    assert state[0].objects[0].class_name == "cube"


def test_replayer_duration_uses_max_timestamp(tmp_path):
    rec = _make_recorder()
    rec.add_ptz("ptzA", timestamp=0.1, pan=0.0)
    rec.add_ptz("ptzA", timestamp=2.5, pan=20.0)
    rec.add_ptz("ptzA", timestamp=1.0, pan=10.0)
    path = rec.write(tmp_path / "rec.json")
    assert RunReplayer.from_path(path).duration == 2.5
