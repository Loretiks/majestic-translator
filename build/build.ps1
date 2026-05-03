# Build helper for Majestic Translator.
#
# Usage (from repo root):
#     .\build\build.ps1
#
# Produces:
#   dist\MajesticTranslator\         — runnable folder
#   installer\output\…-Setup.exe     — only if Inno Setup is installed
#
# Requires: an activated Python venv with the project deps + pyinstaller.

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $RepoRoot

Write-Host "==> Cleaning previous build/dist…" -ForegroundColor Cyan
Remove-Item -Recurse -Force "$RepoRoot\build\MajesticTranslator", "$RepoRoot\dist\MajesticTranslator" -ErrorAction SilentlyContinue

Write-Host "==> Running PyInstaller…" -ForegroundColor Cyan
pyinstaller "build\MajesticTranslator.spec" --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller failed." -ForegroundColor Red
    exit 1
}

$Out = "$RepoRoot\dist\MajesticTranslator"
if (Test-Path $Out) {
    $size = "{0:N0}" -f ((Get-ChildItem $Out -Recurse | Measure-Object Length -Sum).Sum / 1MB)
    Write-Host "==> dist/MajesticTranslator/ ready ($size MB)" -ForegroundColor Green
}

# Optional: build the Inno Setup installer if ISCC is available.
$ISCC_CANDIDATES = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
)
$ISCC = $ISCC_CANDIDATES | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($ISCC) {
    Write-Host "==> Compiling installer with Inno Setup…" -ForegroundColor Cyan
    & $ISCC "$RepoRoot\installer\installer.iss"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "==> Installer ready: installer\output\" -ForegroundColor Green
    }
} else {
    Write-Host "==> Inno Setup not found — skipping installer step." -ForegroundColor Yellow
    Write-Host "    Install from https://jrsoftware.org/isdl.php to enable it." -ForegroundColor Yellow
}
