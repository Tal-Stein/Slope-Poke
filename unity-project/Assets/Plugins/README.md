# Unity Assets/Plugins/

Drop the following DLLs in this folder so the `SlopePoke.Runtime` assembly can
reference NetMQ:

- `NetMQ.dll`
- `AsyncIO.dll`

**Important:** this folder must live at `unity-project/Assets/Plugins/`, not at
`unity-project/Plugins/`. Unity only scans for assets inside `Assets/` and
`Packages/` — DLLs at the project root are silently ignored.

The cleanest way to fetch them: from the repo root, run
`powershell -ExecutionPolicy Bypass -File scripts/fetch-netmq.ps1`. The script
pulls the latest NetMQ + AsyncIO straight from NuGet into this folder.

Alternative: install [NuGetForUnity](https://github.com/GlitchEnzo/NuGetForUnity)
into the project, then `NuGet → Install NetMQ`. NuGetForUnity will populate this
folder automatically.

These DLLs are intentionally **not** committed — they are toolchain output, and
NetMQ is LGPL. Each developer fetches them locally on first setup.
