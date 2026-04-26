# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Slope-Poke

A Unity (HDRP) + Python prototyping environment for computer-vision algorithm development. Unity simulates configurable 3D scenes with virtual cameras (mono / multi / PTZ); a Python runtime consumes the camera streams and runs CV algorithms against them; a coverage/overlap engine analyzes how multi-camera layouts mesh together.

**Status:** Pre-implementation. The original execution plan lives in `project_context.txt`; the load-bearing decisions captured below supersede it where they differ.

## Target CV Use Cases

The prototype must serve three workloads (confirmed with user 2026-04-26):

1. **Multi-camera coverage / placement planning** — where to put N cameras to maximize coverage and hit a target overlap. The coverage/overlap engine is central.
2. **Object detection / tracking** — single- and multi-view object detection. Needs instance-segmentation ground truth for evaluation.
3. **PTZ control loop / active vision** — Python algorithms drive PTZ cameras in response to scene content. Requires a low-latency Python → Unity control channel; PTZ rigs are first-class.

**Explicitly out of scope:** stereo matching / multi-view geometry / depth estimation. This relaxes frame-sync requirements (free-running cameras with timestamp metadata are sufficient — lockstep render is *not* required) and removes depth maps from the required ground-truth output.

## Architectural Commitments

Load-bearing decisions. Do not drift without an explicit conversation with the user.

### Stack
- **Unity 6 LTS** (HDRP) — current LTS as of late 2024.
- **Python 3.10** — env tooling TBD (see Open Questions).
- **Windows-first** — driven by Spout choice. Linux/macOS are not targets.

### Frame transport (Unity → Python)
- **Spout** (via KlakSpout) for per-camera RGB frames — GPU-shared textures, zero CPU readback, sub-ms latency. Trivially meets the <5 ms / 1080p target even with multiple cameras.
- **ZMQ side-channel** for per-frame metadata: `{ camera_id, timestamp, frame_index, intrinsics, extrinsics }`. One PUB topic per camera; Python subscribes.

### Control channel (Python → Unity)
- **ZMQ** (REQ/REP or PUB/SUB) for PTZ commands and any other Python-driven Unity actions. Frames out via Spout, commands in via ZMQ — clean separation.

### Ground-truth pipeline (per frame, alongside RGB)
- **Per-camera calibration** in OpenCV format: 3×3 camera matrix + distortion coefficients + 4×4 world pose. Exported in the metadata stream.
- **Instance segmentation masks** — custom HDRP render pass outputting per-pixel instance IDs, sent via a second Spout sender per camera (e.g. `cameraA_rgb` and `cameraA_seg`).
- **3D bounding boxes / 6DoF object poses** — per frame in the metadata stream as a list of `{ object_id, class, world_pose, bbox_3d }`.
- **No depth maps** (per user decision 2026-04-26).

### Configuration model
- Every experiment run = a pair of `scene_config.json` + `camera_config.json`. Outputs land in `runs/YYYY-MM-DD_HH-MM/` (gitignored).
- Camera params are JSON-serializable per instance: intrinsics (focal length, sensor size, FOV, principal point), Brown-Conrady distortion (k1,k2,k3,p1,p2), Gaussian + salt-and-pepper noise, motion blur, DoF, exposure.

### Plugin contract
- All CV algorithms subclass `BaseAlgorithm` with `process(frame, meta) -> dict`. `PipelineRunner` wires them to camera streams.

### Coverage engine
- Unity computes per-camera coverage via dense raycasting; recomputes only on camera movement events (PTZ tilt/pan/zoom or pose change), not on a polling timer. For static rigs this is a one-shot computation.
- Python `CoverageAnalyzer` consumes per-camera grids and produces overlap heatmaps, blind-spot reports, coverage percentages.

## Repository Layout (planned)

```
unity-project/        Unity 6 HDRP scene, C# scripts, prefabs
python/
  simulator_client/   Spout receiver, ZMQ subscribers, coverage analyzer
  algorithms/         BaseAlgorithm + reference implementations
  tools/              visualization, export utilities
configs/
  scenes/             scene_config.json examples
  cameras/            camera preset JSONs
runs/                 per-experiment output (gitignored)
setup.sh / setup.bat  one-command setup
```

## Conventions

- **Git LFS** for Unity asset types (`.fbx`, `.png`, `.mat`, `.asset`) — set up `.gitattributes` when the Unity project is first added.
- **Commits:** push to `origin` (`https://github.com/Tal-Stein/Slope-Poke.git`) at every meaningful checkpoint — the user has a standing instruction for regular commits + pushes.
- Git identity is unset globally; use per-command env vars (`GIT_AUTHOR_NAME="Tal Stein"`, `GIT_AUTHOR_EMAIL="tal.stein@gmail.com"`, same for committer) until the user sets it.

## Open Questions

Still unresolved — confirm with the user before committing to a direction:

- **PTZ implementation:** Cinemachine 3.x vs a small custom `PTZController`. With PTZ as a closed-loop target, Cinemachine's blending/damping likely fights programmatic control.
- **Python env tooling:** conda + `environment.yml` (per original plan) vs `uv` + `pyproject.toml` (much faster onboarding).
- **Determinism / record-and-replay:** lock sim to fixed RNG seed + fixed timestep, and add a record/replay mechanism for reproducible bug repros?
- **Camera-count target / dev hardware:** typical N cameras per experiment, and dev GPU spec — drives perf budgets.

## Reference

- `project_context.txt` — original execution plan, milestones M1–M7, decisions and rationale (some now superseded by this doc).
