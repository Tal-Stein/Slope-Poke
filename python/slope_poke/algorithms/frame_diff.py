from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from ..simulator_client.types import FrameMeta
from .base import BaseAlgorithm


class FrameDiff(BaseAlgorithm):
    """Trivial reference algorithm: absolute difference vs. previous frame."""

    name = "frame_diff"

    def __init__(self, threshold: int = 25):
        self.threshold = threshold
        self._prev: np.ndarray | None = None

    def process(self, frame: np.ndarray, meta: FrameMeta) -> dict[str, Any]:
        gray = cv2.cvtColor(frame, cv2.COLOR_RGBA2GRAY)
        if self._prev is None:
            self._prev = gray
            return {"motion_pixels": 0, "frame_index": meta.frame_index}
        diff = cv2.absdiff(gray, self._prev)
        self._prev = gray
        motion_mask = diff > self.threshold
        return {
            "motion_pixels": int(motion_mask.sum()),
            "frame_index": meta.frame_index,
            "camera_id": meta.camera_id,
        }
