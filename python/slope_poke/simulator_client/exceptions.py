class SimulatorDisconnected(RuntimeError):
    """Raised when the Unity simulator stops publishing frames or metadata."""


class FrameTimeout(TimeoutError):
    """Raised when no frame arrives within the configured deadline."""
