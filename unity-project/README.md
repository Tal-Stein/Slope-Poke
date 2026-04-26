# Unity Project

This folder is the Unity 6 LTS HDRP project root. Open it from Unity Hub:

> Hub → Add → select `unity-project/`

On first open, Unity will resolve `Packages/manifest.json` (HDRP, KlakSpout) and
generate `Library/`, `ProjectSettings/`, and `.csproj`/`.sln` files (gitignored).

## One-time setup steps after first open

1. Install NuGetForUnity, then `NuGet → Install NetMQ`. See `Plugins/README.md`.
2. Verify the **HDRP Wizard** is green (`Window → Rendering → HDRP Wizard`).
3. Drop the prefabs from `Assets/Scripts/` onto a new scene:
   - One GameObject with `MetadataPublisher`
   - One Camera GameObject with `VirtualCamera` + `FrameStreamer`
   - (Optional) `SceneLoader` + `Hotkeys`

## Smoke test (M1)

1. Press Play in Unity.
2. In a separate terminal at repo root: `uv run slope-poke smoke --camera cameraA`
3. You should see `frame=N t=… shape=(1080, 1920, 4) fps≈…` printed.

If frames don't show up, check `uv run slope-poke list` to confirm Unity is
publishing the expected Spout sender names.
