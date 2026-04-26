from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from ..simulator_client.types import FrameMeta


class BaseAlgorithm(ABC):
    """All CV plug-ins subclass this. PipelineRunner calls `process()` per frame."""

    name: str = "base"

    @abstractmethod
    def process(self, frame: np.ndarray, meta: FrameMeta) -> dict[str, Any]:
        """Consume one (frame, meta) pair and return a JSON-serializable result."""
