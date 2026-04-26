"""PipelineRunner: glue between SimulatorClient and one or more BaseAlgorithm instances."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ..algorithms.base import BaseAlgorithm
from ..simulator_client import SimulatorClient
from ..simulator_client.exceptions import FrameTimeout


class PipelineRunner:
    def __init__(
        self,
        client: SimulatorClient,
        algorithms: Iterable[BaseAlgorithm],
        results_path: Path | None = None,
    ):
        self.client = client
        self.algorithms = list(algorithms)
        self.results_path = results_path
        self._results: list[dict[str, Any]] = []

    def run(self, camera_id: str, max_frames: int | None = None, timeout: float = 1.0) -> None:
        i = 0
        try:
            while max_frames is None or i < max_frames:
                try:
                    frame, meta = self.client.get_frame(camera_id, timeout=timeout)
                except FrameTimeout:
                    break
                wall = time.monotonic()
                for algo in self.algorithms:
                    out = algo.process(frame, meta)
                    self._results.append(
                        {
                            "algo": algo.name,
                            "wall_time": wall,
                            "sim_time": meta.timestamp,
                            "camera_id": meta.camera_id,
                            "frame_index": meta.frame_index,
                            "result": out,
                        }
                    )
                i += 1
        finally:
            if self.results_path is not None:
                self.results_path.parent.mkdir(parents=True, exist_ok=True)
                self.results_path.write_text(json.dumps(self._results, indent=2))

    @property
    def results(self) -> list[dict[str, Any]]:
        return list(self._results)
