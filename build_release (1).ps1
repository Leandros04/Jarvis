param(
    [Parameter(Mandatory = $false)]
    [string]$Version = "1.0.0",

    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Version = $Version.Trim().TrimStart("v", "V")
if ($Version -notmatch '^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$') {
    throw "Version must look like 1.0.0 or 1.2.3-beta.1. Got: $Version"
}

$RequiredFiles = @(
    "jarvis.py",
    "tray_app.py",
    "system_tools.py",
    "browser_tools.py",
    "memory_tools.py",
    "voice_tools.py",
    "wakeword_tools.py",
    "desktop_tools.py",
    "scheduler_tools.py",
    "admin_tools.py",
    "ai_router.py",
    "cost_tracker.py",
    "remote_tools.py",
    "routine_tools.py",
    "health_tools.py",
    "requirements.txt",
    "requirements-build.txt",
    ".env.example",
    "README.md",
    "packaging\JARVIS.spec",
    "packaging\JARVIS.iss",
    "packaging\JARVIS-Core.entry.py",
    "packaging\JARVIS-Tray.entry.py",
    "packaging\make_version_info.py",
    "hooks\runtime_playwright.py",
    "assets\jarvis.ico"
)

$Missing = @()
foreach ($File in $RequiredFiles) {
    if (-not (Test-Path (Join-Path $Root $File))) {
        $Missing += $File
    }
}
if ($Missing.Count -gt 0) {
    throw "Missing required project files:`n - $($Missing -join "`n - ")"
}

Write-Host "== JARVIS release build v$Version ==" -ForegroundColor Cyan

if (Test-Path ".\preflight_release.ps1") {
    & ".\preflight_release.ps1"
}

python --version
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt

# Catch source syntax errors before spending time freezing the application.
python -m compileall -q `
    jarvis.py tray_app.py system_tools.py browser_tools.py memory_tools.py `
    voice_tools.py wakeword_tools.py desktop_tools.py scheduler_tools.py `
    admin_tools.py ai_router.py cost_tracker.py remote_tools.py `
    routine_tools.py health_tools.py

# Playwright's PyInstaller guidance uses PLAYWRIGHT_BROWSERS_PATH=0 so the
# browser lives beside the Playwright package and can be collected.
$env:PLAYWRIGHT_BROWSERS_PATH = "0"
python -m playwright install chromium

python packaging\make_version_info.py $Version packaging\version_info.txt

$BuildDir = Join-Path $Root "build"
$DistDir = Join-Path $Root "dist"
$ReleaseDir = Join-Path $Root "release"

foreach ($Dir in @($BuildDir, $DistDir, $ReleaseDir)) {
    if (Test-Path $Dir) {
        Remove-Item $Dir -Recurse -Force
    }
}
New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null

python -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath "$DistDir" `
    --workpath "$BuildDir" `
    packaging\JARVIS.spec

$BuiltApp = Join-Path $DistDir "JARVIS"
foreach ($Exe in @("JARVIS.exe", "JARVIS-Core.exe")) {
    if (-not (Test-Path (Join-Path $BuiltApp $Exe))) {
        throw "PyInstaller build did not produce $Exe"
    }
}

$Stage = Join-Path $ReleaseDir "JARVIS"
Copy-Item $BuiltApp $Stage -Recurse
Copy-Item README.md (Join-Path $Stage "README.md")
Copy-Item .env.example (Join-Path $Stage ".env.example")
if (Test-Path "assets\jarvis.png") {
    Copy-Item assets\jarvis.png (Join-Path $Stage "jarvis.png")
}

# Never distribute local credentials/configuration.
$AccidentalEnv = Join-Path $Stage ".env"
if (Test-Path $AccidentalEnv) {
    Remove-Item $AccidentalEnv -Force
}

$PortableZip = Join-Path $ReleaseDir "JARVIS-Portable-$Version.zip"
Compress-Archive -Path "$Stage\*" -DestinationPath $PortableZip -CompressionLevel Optimal

$Installer = $null
if (-not $SkipInstaller) {
    $Candidates = @(
        (Get-Command ISCC.exe -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles(x86)\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { $_ -and (Test-Path $_) }

    $ISCC = $Candidates | Select-Object -First 1
    if (-not $ISCC) {
        throw "Inno Setup 6/7 was not found. Install Inno Setup or use -SkipInstaller."
    }

    & $ISCC "/DMyAppVersion=$Version" "packaging\JARVIS.iss"

    $Installer = Join-Path $ReleaseDir "JARVIS-Setup-$Version.exe"
    if (-not (Test-Path $Installer)) {
        throw "Inno Setup did not produce $Installer"
    }
}

# Record exact dependency versions resolved by this build.
python -m pip freeze | Set-Content `
    (Join-Path $ReleaseDir "requirements-lock.txt") `
    -Encoding ascii

$BuildInfo = @(
    "JARVIS version: $Version",
    "Build time UTC: $([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))",
    "Python: $(python --version 2>&1)",
    "PyInstaller: $(python -m PyInstaller --version 2>&1)",
    "Git commit: $($env:GITHUB_SHA)",
    "Git ref: $($env:GITHUB_REF)"
)
$BuildInfo | Set-Content (Join-Path $ReleaseDir "BUILD-INFO.txt") -Encoding utf8

$ChecksumFile = Join-Path $ReleaseDir "SHA256SUMS.txt"
$Artifacts = @($PortableZip)
if ($Installer) {
    $Artifacts += $Installer
}

$Lines = foreach ($Artifact in $Artifacts) {
    $Hash = Get-FileHash $Artifact -Algorithm SHA256
    "{0}  {1}" -f $Hash.Hash.ToLowerInvariant(), (Split-Path $Artifact -Leaf)
}
$Lines | Set-Content $ChecksumFile -Encoding ascii

Write-Host ""
Write-Host "Release artifacts:" -ForegroundColor Green
Get-ChildItem $ReleaseDir -File |
    Select-Object Name, Length |
    Format-Table -AutoSize
Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
