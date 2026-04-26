#!/usr/bin/env bash
# Slope-Poke one-command setup (Git Bash / WSL).
# Note: The full project targets Windows (Spout). This script gets the Python
# side running anywhere; the Unity side still needs Windows.

set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    echo "[setup] Installing uv ..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "[setup] Syncing Python environment ..."
uv sync

cat <<'EOF'

[setup] Python ready. Next steps:
  1. Install Unity Hub and Unity 6 LTS (HDRP) on a Windows machine.
  2. Open unity-project/ from Unity Hub.
  3. In Unity: install NuGetForUnity, then NuGet -> Install NetMQ.
  4. Press Play in Unity, then run:  uv run slope-poke smoke --camera cameraA

EOF
