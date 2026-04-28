"""Wire-format tests for PTZCommand. The Unity-side parser in PTZController.cs
expects keys to be one of pan/tilt/zoom and values to be plain floats — these
tests pin the JSON shape so it stays compatible if PTZCommand ever evolves.
"""

import json

import pytest

from slope_poke.control import PTZCommand


def test_ptz_full_command_serializes():
    cmd = PTZCommand(pan=10.0, tilt=-5.0, zoom=50.0)
    parsed = json.loads(cmd.to_json())
    assert parsed == {"pan": 10.0, "tilt": -5.0, "zoom": 50.0}


def test_ptz_partial_command_omits_unset_fields():
    cmd = PTZCommand(pan=42.0)
    parsed = json.loads(cmd.to_json())
    assert parsed == {"pan": 42.0}


def test_ptz_empty_command_is_rejected():
    with pytest.raises(ValueError):
        PTZCommand().to_json()
