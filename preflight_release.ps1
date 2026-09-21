$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "== JARVIS release preflight ==" -ForegroundColor Cyan


# ============================================================
# REQUIRE GIT
# ============================================================

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required for release preflight."
}


# ============================================================
# TRACKED FILES
# ============================================================

$Tracked = @(
    git ls-files
)

if ($LASTEXITCODE -ne 0) {
    throw "Could not read tracked files from Git."
}


# ============================================================
# FORBIDDEN FILES / PATHS
# ============================================================

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

$BadTracked = @()


foreach ($File in $Tracked) {

    $Normalized = $File.Replace(
        '\',
        '/'
    )

    $Matched = $false


    foreach ($Pattern in $ForbiddenNamePatterns) {

        if ($Normalized -match $Pattern) {

            $BadTracked += $File
            $Matched = $true

            break
        }
    }


    if ($Matched) {
        continue
    }


    foreach ($Exact in $ForbiddenExact) {

        if (
            ($Normalized -eq $Exact) -or
            ($Normalized.StartsWith("$Exact/"))
        ) {

            $BadTracked += $File

            break
        }
    }
}


$BadTracked = @(
    $BadTracked |
    Sort-Object -Unique
)


if ($BadTracked.Count -gt 0) {

    Write-Host ""

    Write-Host `
        "Forbidden sensitive/runtime files are TRACKED by Git:" `
        -ForegroundColor Red


    foreach ($File in $BadTracked) {

        Write-Host `
            "  $File" `
            -ForegroundColor Red
    }


    Write-Host ""

    Write-Host `
        "Remove these files from Git before releasing." `
        -ForegroundColor Red


    throw "Release preflight failed."
}


# ============================================================
# BASIC SECRET SCAN
# ============================================================

$SecretHits = @()


foreach ($File in $Tracked) {

    if (-not (Test-Path $File -PathType Leaf)) {
        continue
    }


    try {

        $Text = Get-Content `
            $File `
            -Raw `
            -ErrorAction Stop

    }
    catch {

        continue
    }


    if (
        $Text -match
        'OPENAI_API_KEY\s*=\s*sk-[A-Za-z0-9_\-]{10,}'
    ) {

        $SecretHits += $File

        continue
    }


    if (
        $Text -match
        '-----BEGIN (OPENSSH|RSA|EC|DSA) PRIVATE KEY-----'
    ) {

        $SecretHits += $File

        continue
    }
}


$SecretHits = @(
    $SecretHits |
    Sort-Object -Unique
)


if ($SecretHits.Count -gt 0) {

    Write-Host ""

    Write-Host `
        "Possible live secrets found inside tracked files:" `
        -ForegroundColor Red


    foreach ($File in $SecretHits) {

        Write-Host `
            "  $File" `
            -ForegroundColor Red
    }


    Write-Host ""

    throw "Release preflight failed."
}


# ============================================================
# VERIFY LOCAL .ENV IS IGNORED
# ============================================================

if (Test-Path ".env") {

    git check-ignore -q ".env"

    if ($LASTEXITCODE -ne 0) {

        throw ".env exists but Git is not ignoring it."
    }


    Write-Host `
        ".env exists locally and is ignored: OK" `
        -ForegroundColor Green
}


# ============================================================
# SSH PRIVATE KEY CHECK
# ============================================================

$PossibleKeys = @(
    "$env:USERPROFILE\.ssh\jarvis_ed25519",
    "$env:USERPROFILE\.ssh\id_ed25519",
    "$env:USERPROFILE\.ssh\id_rsa"
)


foreach ($Key in $PossibleKeys) {

    if (Test-Path $Key) {

        Write-Host `
            "Private SSH key exists outside repository: OK" `
            -ForegroundColor Green

        break
    }
}


# ============================================================
# REQUIRED RELEASE FILES
# ============================================================

$RequiredFiles = @(
    ".gitignore",
    ".env.example",
    "README.md",
    "requirements.txt"
)

$MissingRequired = @()


foreach ($File in $RequiredFiles) {

    if (-not (Test-Path $File)) {

        $MissingRequired += $File
    }
}


if ($MissingRequired.Count -gt 0) {

    Write-Host ""

    Write-Host `
        "Missing required release files:" `
        -ForegroundColor Red


    foreach ($File in $MissingRequired) {

        Write-Host `
            "  $File" `
            -ForegroundColor Red
    }


    throw "Release preflight failed."
}


# ============================================================
# SUCCESS
# ============================================================

Write-Host ""

Write-Host `
    "No forbidden tracked secrets or runtime data found." `
    -ForegroundColor Green

Write-Host `
    "Required release files present." `
    -ForegroundColor Green

Write-Host ""

Write-Host `
    "Preflight passed." `
    -ForegroundColor Green