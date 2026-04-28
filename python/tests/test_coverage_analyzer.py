"""Overlap math for CoverageAnalyzer. The receiver wraps these calls behind a
thread, so testing the pure analyzer is enough to guard the algorithm.
"""

import numpy as np

from slope_poke.coverage import CoverageAnalyzer, CoverageGrid


def _grid(camera_id: str, mask: np.ndarray) -> CoverageGrid:
    return CoverageGrid(camera_id=camera_id, grid=mask.astype(np.float32),
                        extent=(0.0, 1.0, 0.0, 1.0))


def test_overlap_counts_overlapping_cameras():
    a = np.array([[1, 1, 0], [1, 0, 0]])
    b = np.array([[1, 0, 0], [0, 0, 0]])
    c = np.array([[0, 0, 1], [0, 1, 1]])
    an = CoverageAnalyzer()
    for cid, m in zip(["a", "b", "c"], [a, b, c]):
        an.update(_grid(cid, m))

    overlap = an.overlap_map()
    assert overlap.shape == (2, 3)
    # cell (0,0): seen by a and b → 2; (0,2): only c → 1; (1,1): only c → 1
    assert overlap[0, 0] == 2
    assert overlap[0, 2] == 1
    assert overlap[1, 1] == 1


def test_blind_spots_marks_uncovered_cells():
    a = np.array([[1, 0], [0, 0]])
    b = np.array([[0, 0], [0, 1]])
    an = CoverageAnalyzer()
    an.update(_grid("a", a))
    an.update(_grid("b", b))
    blind = an.blind_spots()
    assert blind[0, 1] and blind[1, 0]
    assert not blind[0, 0] and not blind[1, 1]


def test_coverage_percentage_per_camera():
    a = np.array([[1, 1], [0, 0]])
    an = CoverageAnalyzer()
    an.update(_grid("a", a))
    assert an.coverage_percentage("a") == 0.5
