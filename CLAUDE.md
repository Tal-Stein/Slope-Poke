# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Slope-Poke

A Unity (HDRP) + Python prototyping environment for computer-vision algorithm development. Unity simulates configurable 3D scenes with virtual cameras (mono / multi / PTZ); a Python runtime consumes the camera streams via shared memory and runs CV algorithms against them; a coverage/overlap engine analyzes how multi-camera layouts mesh together.

**Status:** Pre-implementation. The only existing artifact is `project_context.txt` — the full execution plan, stack rationale, and milestones M1–M7. Read it before making architectural decisions.

## Architectural Commitments

Load-bearing decisions from the plan. Do not drift from them without an explicit conversation with the user.

- **Frame transport:** Unity → Python via named shared memory (mmap), ring buffer with 2–3 slots per camera, plus a small per-frame metadata block (`camera_id`, `timestamp`, `frame_index`, intrinsics, extrinsics). Latency target: <5 ms at 1080p on a single machine.
- **Config-driven experiments:** every run is a pair of `scene_config.json` + `camera_config.json`. Outputs land in `runs/YYYY-MM-DD_HH-MM/` (gitignored).
- **Plugin contract:** all CV algorithms subclass `BaseAlgorithm` with `process(frame, meta) -> dict`. `PipelineRunner` wires them to camera streams.
- **Camera parameters** are JSON-serializable per instance: intrinsics (focal length, sensor size, FOV, principal point), Brown-Conrady distortion (k1,k2,k3,p1,p2), Gaussian + salt-and-pepper noise, motion blur, DoF, exposure.
- **Rig types:** Mono, Multi (stereo as N=2 special case with baseline + vergence controls), PTZ.

## Repository Layout (planned)

```
unity-project/        Unity HDRP scene, C# scripts, prefabs
python/
  simulator_client/   shared-memory client, coverage analyzer
  algorithms/         BaseAlgorithm + reference implementations
  tools/              visualization, export utilities
configs/
  scenes/             scene_config.json examples
  cameras/            camera preset JSONs
runs/                 per-experiment output (gitignored)
environment.yml       conda spec (Python 3.10)
setup.sh / setup.bat  one-command setup
```

## Conventions

- **Git LFS** for Unity asset types (`.fbx`, `.png`, `.mat`, `.asset`) — set up `.gitattributes` when the Unity project is first added.
- **Python env:** conda, Python 3.10, deps pinned in `environment.yml`.
- **Commits:** push to `origin` (`https://github.com/Tal-Stein/Slope-Poke.git`) at every meaningful checkpoint. The user has a standing instruction for regular commits + pushes.

## Open Architectural Questions

These have been raised but not yet resolved with the user. Confirm before assuming a direction:

- **Unity version:** plan says 2022.3 LTS, but Unity 6 LTS (released Oct 2024) is now the current LTS and may be preferred.
- **`com.unity.perception` viability:** package status / maintenance is uncertain — lens distortion and labels may need a different path (custom HDRP shader, Unity Sentis, etc.).
- **Frame transport choice:** named shared memory is the lowest-latency option but cross-platform behavior on Windows can be finicky. Alternatives: ZeroMQ over loopback, Spout (Windows GPU-shared textures), NDI.
- **Cinemachine for PTZ:** likely overkill — a custom transform + FOV controller may be simpler.
- **Specific CV use case** driving the prototype (detection / tracking / coverage planning / SLAM / multi-view geometry?) — shapes priorities.
- **Frame sync** across cameras (needed for stereo / multi-view, not for coverage).
- **Ground-truth labels** required (depth maps, segmentation masks, 2D/3D bboxes?).
- **Determinism / record-and-replay** for reproducible experiments — not addressed in the plan.

## Reference

- `project_context.txt` — full execution plan, milestones M1–M7, decisions and rationale.
