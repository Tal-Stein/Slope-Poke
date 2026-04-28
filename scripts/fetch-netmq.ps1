# Fetch NetMQ + AsyncIO DLLs from NuGet into unity-project/Plugins/.
# Run from repo root: powershell -ExecutionPolicy Bypass -File scripts/fetch-netmq.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$plugins = Join-Path $root "unity-project\Plugins"
$tmp = Join-Path $env:TEMP "slope-poke-nuget"
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
New-Item -ItemType Directory -Path $tmp | Out-Null

foreach ($pkg in @("NetMQ", "AsyncIO")) {
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
    $dll = Get-ChildItem $picked.FullName -Filter "$pkg.dll" -File | Select-Object -First 1
    Copy-Item -Path $dll.FullName -Destination $plugins -Force
    Write-Output ("[$pkg] copied " + $dll.Name + " from " + $picked.Name)
}
Write-Output "---"
Get-ChildItem $plugins -Filter "*.dll" | Format-Table Name, Length -AutoSize
