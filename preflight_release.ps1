$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "== JARVIS release preflight ==" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required for release preflight."
}

# These paths must never be committed.
$ForbiddenExact = @(
    ".env",
    "data",
    "logs",
    "screenshots",
    "browser_profile"
)

$ForbiddenNamePatterns = @(
    '(^|/)\.env$',
    '(^|/)jarvis_ed25519($|\.)',
    '(^|/)id_ed25519($|\.)',
    '(^|/)id_rsa($|\.)',
    '\.(pem|key)$',
    '\.(db|sqlite|sqlite3)$'
)

$Tracked = @(git ls-files)

$BadTracked = @()
foreach ($File in $Tracked) {
    $Normalized = $File.Replace('\', '/')

    foreach ($Pattern in $ForbiddenNamePatterns) {
        if ($Normalized -match $Pattern) {
            $BadTracked += $File
            break
        }
    }

    foreach ($Exact in $ForbiddenExact) {
        if (
            $Normalized -eq $Exact -or
            $Normalized.StartsWith("$Exact/")
        ) {
            $BadTracked += $File
            break
        }
    }
}

$BadTracked = $BadTracked | Sort-Object -Unique

if ($BadTracked.Count -gt 0) {
    Write-Host ""
    Write-Host "Forbidden sensitive/runtime files are TRACKED by Git:" -ForegroundColor Red
    $BadTracked | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Remove them from Git history/index before releasing." -ForegroundColor Red
    throw "Release preflight failed."
}

# Scan tracked text for obvious live OpenAI secret patterns.
$SecretHits = @()
foreach ($File in $Tracked) {
    if (-not (Test-Path $File -PathType Leaf)) {
        continue
    }

    try {
        $Text = Get-Content $File -Raw -ErrorAction Stop
    } catch {
        continue
    }

    if ($Text -match 'OPENAI_API_KEY\s*=\s*sk-[A-Za-z0-9_\-]{10,}') {
        $SecretHits += $File
    }

    if ($Text -match '-----BEGIN (OPENSSH|RSA|EC|DSA) PRIVATE KEY-----') {
        $SecretHits += $File
    }
}

$SecretHits = $SecretHits | Sort-Object -Unique

if ($SecretHits.Count -gt 0) {
    Write-Host ""
    Write-Host "Possible live secrets found in tracked files:" -ForegroundColor Red
    $SecretHits | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    throw "Release preflight failed."
}

# If a developer .env exists, make sure Git ignores it.
if (Test-Path ".env") {
    git check-ignore -q ".env"
    if ($LASTEXITCODE -ne 0) {
        throw ".env exists but is not ignored by Git."
    }
    Write-Host ".env exists locally and is ignored: OK" -ForegroundColor Green
}

Write-Host "No forbidden tracked secrets/runtime data found." -ForegroundColor Green
Write-Host "Preflight passed." -ForegroundColor Green
