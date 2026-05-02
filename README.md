# Slope-Poke

A Unity (HDRP) + Python prototyping environment for computer-vision algorithm
development. Unity simulates configurable 3D scenes with virtual cameras
(mono / multi / PTZ); a Python runtime consumes the camera streams and runs CV
algorithms; a coverage/overlap engine analyzes how multi-camera layouts mesh.

See `CLAUDE.md` for load-bearing architectural decisions (frame transport,
control channel, ground-truth pipeline, determinism).

## Repository layout

```
unity-project/        Unity 6 HDRP project (open from Unity Hub)
  Assets/Scripts/     C# runtime: cameras, streaming, PTZ control, coverage
  Packages/           manifest.json (HDRP, KlakSpout via Keijiro registry)
  Plugins/            NetMQ DLLs — fetched per-developer via NuGetForUnity
python/slope_poke/    Python package
  simulator_client/   Spout receiver, ZMQ subscriber, SimulatorClient API
  algorithms/         BaseAlgorithm + frame_diff + MOG2 reference impls
  pipeline/           PipelineRunner
  coverage/           CoverageAnalyzer (overlap maps, blind spots)
  config/             Pydantic models mirroring configs/*.json
  cli.py              `slope-poke smoke` / `slope-poke list`
configs/
  scenes/             scene_config.json examples
  cameras/            camera_config.json examples
  schema/             JSON Schema for both
runs/                 per-experiment output (gitignored)
pyproject.toml        Python deps (uv-managed)
setup.bat / setup.sh  one-command Python setup
```

## First-time setup

### 1. Python side

```cmd
.\setup.bat
```

This installs [`uv`](https://docs.astral.sh/uv/) if needed and runs `uv sync` to
build a locked `.venv` from `pyproject.toml`.

### 2. Unity side

1. Install **Unity Hub** and **Unity 6 LTS** with the **HDRP** template.
2. From Hub: **Add → select `unity-project/`** in this repo. First open will
   resolve packages and generate `Library/`, `ProjectSettings/`, etc.
3. Install [NuGetForUnity](https://github.com/GlitchEnzo/NuGetForUnity), then
   **NuGet → Install NetMQ**. This populates `Plugins/` with the DLLs the
   `SlopePoke.Runtime` assembly references.

## Smoke test (M1)

1. In Unity, build a scene with one Camera GameObject carrying:
   `VirtualCamera` + `FrameStreamer` (cameraId = `cameraA`),
   plus an empty GameObject with `MetadataPublisher`.
2. Press **Play** in Unity.
3. From the repo root:

   ```cmd
   uv run slope-poke smoke --camera cameraA
   ```

   You should see ~60 fps frame metadata printed.

If `slope-poke list` returns no senders, KlakSpout isn't initialized yet — make
sure the camera is enabled and the scene is in Play mode.

## Visualization

When Unity is in Play and senders are live:

```cmd
uv run slope-poke view                 # OpenCV tile viewer with bbox overlays
uv run slope-poke view --no-overlays   # raw frames only
uv run slope-poke layout --config configs/cameras/ring8.json --out layout.png --with-targets
```

In-editor preview: add a `Camera` GameObject to the scene **without**
`VirtualCamera` / `FrameStreamer` — call it `PreviewCamera`. Unity's Game view
auto-picks any camera with `targetTexture == null`, so it renders the scene
without disturbing the Spout pipeline.

External tools worth installing:

- **SpoutSettings** (free, https://spout.zeal.co/) — system-tray utility with
  thumbnails of every active Spout sender. Fastest "is anything coming out?" check.
- **OBS Studio** + the `obs-spout2-plugin` — capture session video for review.

## Conventions

- **Commits + push** at every meaningful checkpoint. Remote: `origin`
  (`https://github.com/Tal-Stein/Slope-Poke.git`).
- **Git LFS** governs `.fbx`, `.png`, `.mat`, `.asset`, etc. — see
  `.gitattributes`.
- **Run outputs** land in `runs/YYYY-MM-DD_HH-MM/` and are gitignored.

## Status

M1 scaffold (this commit). Next milestones:

- **M2** Camera-parameter UI in Unity, full `camera_config.json` round-trip.
- **M3** Multi-camera + PTZ rigs end-to-end.
- **M4** Moving objects, dynamic scene loader.
- **M5** Coverage / overlap engine producing live heatmaps.
- **M6** `BaseAlgorithm` + 2 reference impls running on real streams.
- **M7** Team onboarding doc + record/replay polish.
