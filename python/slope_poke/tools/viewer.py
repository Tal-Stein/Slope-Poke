"""Live OpenCV tile viewer for all active Spout cameras with optional bbox overlays."""

from __future__ import annotations

import math
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from ..simulator_client import SimulatorClient
from ..simulator_client.exceptions import FrameTimeout
from ..simulator_client.types import FrameMeta
from .projection import BBOX_EDGES, project_bbox_3d


def discover_cameras() -> list[str]:
    """Return camera IDs derived from active Spout senders matching '<id>_rgb'."""
    try:
        import SpoutGL
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("SpoutGL not installed; cannot auto-discover cameras.") from e
    rx = SpoutGL.SpoutReceiver()
    senders = rx.getSenderList() or []
    ids = []
    for s in senders:
        if s.endswith("_rgb"):
            ids.append(s[: -len("_rgb")])
    return sorted(ids)


class TileViewer:
    """Composite live grid of all configured cameras into a single OpenCV window.

    Per-frame loop polls each camera with a short timeout, falls back to the
    most-recent successful frame if the new poll misses, and re-renders the
    grid every iteration. Bbox overlays are projected from the matching
    FrameMeta using the shared projection helper.
    """

    def __init__(
        self,
        camera_ids: list[str],
        tile_size: tuple[int, int] = (480, 270),
        draw_overlays: bool = True,
        snapshot_dir: Path | str = "runs",
        zmq_endpoint: str = "tcp://127.0.0.1:5555",
        per_camera_timeout: float = 0.05,
        border_px: int = 2,
        border_color: tuple[int, int, int] = (40, 40, 40),
    ):
        if not camera_ids:
            raise ValueError("TileViewer requires at least one camera_id.")
        self.camera_ids = camera_ids
        self.tile_w, self.tile_h = tile_size
        self.draw_overlays = draw_overlays
        self.snapshot_dir = Path(snapshot_dir)
        self.zmq_endpoint = zmq_endpoint
        self.per_camera_timeout = per_camera_timeout
        self.border_px = max(0, border_px)
        self.border_color = border_color

        # Per-camera latest (frame_bgr, meta) cache so the grid stays populated
        # even when one camera misses a frame on a particular tick.
        self._latest: dict[str, tuple[np.ndarray, FrameMeta] | None] = {
            cid: None for cid in camera_ids
        }

    def run(self) -> int:
        cols = math.ceil(math.sqrt(len(self.camera_ids)))
        rows = math.ceil(len(self.camera_ids) / cols)
        window = "slope-poke view"
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        # Each tile gets `border_px` on every side, so total seam between tiles
        # is 2*border_px (and the outer frame is border_px). Size the window for
        # the bordered tiles.
        outer_w = (self.tile_w + 2 * self.border_px) * cols
        outer_h = (self.tile_h + 2 * self.border_px) * rows
        cv2.resizeWindow(window, outer_w, outer_h)
        print(f"Opened tile viewer ({len(self.camera_ids)} cameras, {cols}×{rows} grid)."
              " Press 'q' to quit, 's' to snapshot.")

        with SimulatorClient(camera_ids=self.camera_ids,
                             zmq_endpoint=self.zmq_endpoint) as sim:
            while True:
                self._poll_all(sim)
                grid = self._compose_grid(rows, cols)
                cv2.imshow(window, grid)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:
                    break
                if key == ord("s"):
                    self._save_snapshot(grid)

        cv2.destroyAllWindows()
        return 0

    def _poll_all(self, sim: SimulatorClient) -> None:
        for cid in self.camera_ids:
            try:
                frame_rgba, meta = sim.get_frame(cid, timeout=self.per_camera_timeout)
            except FrameTimeout:
                continue
            bgr = cv2.cvtColor(frame_rgba, cv2.COLOR_RGBA2BGR)
            self._latest[cid] = (bgr, meta)

    def _compose_grid(self, rows: int, cols: int) -> np.ndarray:
        tiles: list[np.ndarray] = []
        for cid in self.camera_ids:
            entry = self._latest[cid]
            if entry is None:
                tile = np.zeros((self.tile_h, self.tile_w, 3), dtype=np.uint8)
                cv2.putText(tile, f"{cid} (no frame)", (10, 24),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1, cv2.LINE_AA)
            else:
                frame, meta = entry
                if self.draw_overlays:
                    frame = self._draw_overlays(frame, meta)
                tile = cv2.resize(frame, (self.tile_w, self.tile_h),
                                  interpolation=cv2.INTER_AREA)
                cv2.putText(tile, cid, (8, 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1, cv2.LINE_AA)
            tiles.append(self._with_border(tile))

        # Pad to a full grid with bordered black tiles so np.concatenate doesn't choke.
        blank = self._with_border(np.zeros((self.tile_h, self.tile_w, 3), dtype=np.uint8))
        while len(tiles) < rows * cols:
            tiles.append(blank)

        rows_imgs = [
            np.concatenate(tiles[r * cols:(r + 1) * cols], axis=1)
            for r in range(rows)
        ]
        return np.concatenate(rows_imgs, axis=0)

    def _with_border(self, tile: np.ndarray) -> np.ndarray:
        if self.border_px == 0:
            return tile
        return cv2.copyMakeBorder(
            tile,
            self.border_px, self.border_px, self.border_px, self.border_px,
            cv2.BORDER_CONSTANT, value=self.border_color,
        )

    @staticmethod
    def _draw_overlays(frame_bgr: np.ndarray, meta: FrameMeta) -> np.ndarray:
        if not meta.objects:
            return frame_bgr
        out = frame_bgr.copy()
        h, w = out.shape[:2]
        for obj in meta.objects:
            corners_2d = project_bbox_3d(obj.bbox_3d, meta.intrinsics, meta.extrinsics)
            # Edge pass — only draw segments where both endpoints projected in front.
            for a, b in BBOX_EDGES:
                pa, pb = corners_2d[a], corners_2d[b]
                if pa is None or pb is None:
                    continue
                p1 = (int(round(pa[0])), int(round(pa[1])))
                p2 = (int(round(pb[0])), int(round(pb[1])))
                cv2.line(out, p1, p2, (0, 255, 0), 1, cv2.LINE_AA)
            # Label at the centroid of valid projections.
            valid = [p for p in corners_2d if p is not None]
            if valid:
                cu = sum(p[0] for p in valid) / len(valid)
                cv = sum(p[1] for p in valid) / len(valid)
                if 0 <= cu < w and 0 <= cv < h:
                    label = f"{obj.class_name}#{obj.object_id}"
                    cv2.putText(out, label, (int(cu) + 4, int(cv) - 4),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1, cv2.LINE_AA)
        return out

    def _save_snapshot(self, grid: np.ndarray) -> None:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out_dir = self.snapshot_dir / ts / "snapshot"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "grid.png"
        cv2.imwrite(str(path), grid)
        print(f"Saved snapshot {path}")


def run_viewer(
    camera_ids: list[str] | None = None,
    tile_size: tuple[int, int] = (480, 270),
    draw_overlays: bool = True,
    zmq_endpoint: str = "tcp://127.0.0.1:5555",
    border_px: int = 2,
    border_color: tuple[int, int, int] = (40, 40, 40),
) -> int:
    """Top-level helper used by the CLI. Auto-discovers cameras when none given."""
    if not camera_ids:
        # Brief wait for senders if Unity just started.
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            camera_ids = discover_cameras()
            if camera_ids:
                break
            time.sleep(0.2)
    if not camera_ids:
        print("No active Spout senders found. Is Unity playing?")
        return 1
    viewer = TileViewer(
        camera_ids=camera_ids,
        tile_size=tile_size,
        draw_overlays=draw_overlays,
        zmq_endpoint=zmq_endpoint,
        border_px=border_px,
        border_color=border_color,
    )
    return viewer.run()
