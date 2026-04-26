# Unity Plugins/

Drop the following DLLs in this folder so the `SlopePoke.Runtime` assembly can
reference NetMQ:

- `NetMQ.dll`
- `AsyncIO.dll`
- `NaCl.dll`

The cleanest way to fetch them: install [NuGetForUnity](https://github.com/GlitchEnzo/NuGetForUnity)
into the project, then `NuGet → Install NetMQ`. NuGetForUnity will populate this
folder automatically with the right .NET Standard 2.1 builds.

Alternative: run `nuget install NetMQ` from any command line and copy the DLLs
out of `NetMQ.<version>/lib/netstandard2.0/` and `AsyncIO.<version>/lib/netstandard2.0/`.

These DLLs are intentionally **not** committed — they are toolchain output, and
NetMQ is LGPL. Each developer fetches them locally via NuGet on first setup.
