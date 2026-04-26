from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from ..simulator_client.types import FrameMeta
from .base import BaseAlgorithm


class MOG2BackgroundSubtractor(BaseAlgorithm):
    """OpenCV MOG2 background subtractor — second reference plug-in."""

    name = "mog2"

    def __init__(self, history: int = 500, var_threshold: float = 16.0, detect_shadows: bool = True):
        self._sub = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=detect_shadows,
        )

    def process(self, frame: np.ndarray, meta: FrameMeta) -> dict[str, Any]:
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        mask = self._sub.apply(bgr)
        fg_pixels = int((mask == 255).sum())
        return {
            "fg_pixels": fg_pixels,
            "frame_index": meta.frame_index,
            "camera_id": meta.camera_id,
        }
