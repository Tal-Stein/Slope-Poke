"""Coverage / overlap analysis over per-camera coverage grids from Unity.

Unity computes per-camera coverage by dense raycasting (one-shot for static rigs,
recomputed on PTZ events) and ships float32 grids to Python. This module stacks
them and produces overlap heatmaps, blind-spot reports, and coverage percentages.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class CoverageGrid:
    camera_id: str
    grid: np.ndarray  # (H, W) float32, 0..1 visibility
    extent: tuple[float, float, float, float]  # xmin, xmax, ymin, ymax (world units)


class CoverageAnalyzer:
    def __init__(self) -> None:
        self._grids: dict[str, CoverageGrid] = {}

    def update(self, grid: CoverageGrid) -> None:
        self._grids[grid.camera_id] = grid

    def overlap_map(self) -> np.ndarray:
        if not self._grids:
            raise ValueError("No coverage grids registered.")
        stack = np.stack([g.grid > 0 for g in self._grids.values()], axis=0)
        return stack.sum(axis=0).astype(np.uint16)

    def coverage_percentage(self, camera_id: str) -> float:
        g = self._grids[camera_id].grid
        return float((g > 0).mean())

    def blind_spots(self) -> np.ndarray:
        """Boolean mask of cells unseen by any camera."""
        return self.overlap_map() == 0

    def export_map(self, path: Path) -> None:
        try:
            import matplotlib.pyplot as plt
        except ImportError as e:  # pragma: no cover
            raise ImportError("matplotlib is required to export coverage PNGs.") from e
        ov = self.overlap_map()
        plt.imsave(path, ov, cmap="viridis")
