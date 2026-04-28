# Fetch NetMQ + AsyncIO DLLs from NuGet into unity-project/Plugins/.
# Run from repo root: powershell -ExecutionPolicy Bypass -File scripts/fetch-netmq.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$plugins = Join-Path $root "unity-project\Assets\Plugins"
$tmp = Join-Path $env:TEMP "slope-poke-nuget"
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
New-Item -ItemType Directory -Path $tmp | Out-Null

$pkgs = @(
    @{ Name = "NetMQ";    Dll = "NetMQ.dll"   },
    @{ Name = "AsyncIO";  Dll = "AsyncIO.dll" },
    @{ Name = "NaCl.Net"; Dll = "NaCl.dll"    }
)
foreach ($entry in $pkgs) {
    $pkg = $entry.Name
    $dllName = $entry.Dll
    $zip = Join-Path $tmp "$pkg.zip"
    Invoke-WebRequest -Uri "https://www.nuget.org/api/v2/package/$pkg" -OutFile $zip
    $extract = Join-Path $tmp $pkg
    Expand-Archive -Path $zip -DestinationPath $extract -Force
    $libRoot = Join-Path $extract "lib"
    $picked = Get-ChildItem $libRoot -Directory `
        | Where-Object { $_.Name -match "^netstandard2\." } `
        | Sort-Object Name -Descending `
        | Select-Object -First 1
    if ($null -eq $picked) {
        $picked = Get-ChildItem $libRoot -Directory | Select-Object -First 1
    }
    $dll = Get-ChildItem $picked.FullName -Filter $dllName -File | Select-Object -First 1
    Copy-Item -Path $dll.FullName -Destination $plugins -Force
    # Write minimal .dll.meta so Unity imports the plugin even if the editor is
    # in safe mode (where new asset import is blocked until compilation succeeds).
    $metaPath = Join-Path $plugins ($dll.Name + ".meta")
    if (-not (Test-Path $metaPath)) {
        $guid = ([guid]::NewGuid().ToString("N"))
        $meta = @"
fileFormatVersion: 2
guid: $guid
PluginImporter:
  externalObjects: {}
  serializedVersion: 2
  iconMap: {}
  executionOrder: {}
  defineConstraints: []
  isPreloaded: 0
  isOverridable: 0
  isExplicitlyReferenced: 0
  validateReferences: 1
  platformData:
  - first:
      Any:
    second:
      enabled: 1
      settings: {}
  - first:
      Editor: Editor
    second:
      enabled: 0
      settings:
        DefaultValueInitialized: true
  userData:
  assetBundleName:
  assetBundleVariant:
"@
        Set-Content -Path $metaPath -Value $meta -Encoding UTF8
    }
    Write-Output ("[$pkg] copied " + $dll.Name + " from " + $picked.Name)
}
Write-Output "---"
Get-ChildItem $plugins -Filter "*.dll" | Format-Table Name, Length -AutoSize
