# Releasing JARVIS

JARVIS ships in two Windows formats:

1. `JARVIS-Setup-X.Y.Z.exe` — recommended installer.
2. `JARVIS-Portable-X.Y.Z.zip` — portable one-folder build.

The installer is a single `.exe`. The installed application itself uses a
PyInstaller one-folder layout because JARVIS contains Playwright, native speech
libraries, ONNX Runtime, CTranslate2, and other native dependencies.

## Important security rule

Never commit or package:

- `.env`
- OpenAI API keys
- SSH private keys
- `data/`
- `browser_profile/`
- runtime databases
- personal logs

Only `.env.example` belongs in Git.

## First repository setup

From the project folder:

```powershell
git init
git add .
git commit -m "Initial JARVIS release"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

## Release preflight

Before committing a public release, run:

```powershell
.\preflight_release.ps1
```

It fails if Git is tracking `.env`, SSH private keys, runtime databases,
browser-profile data, or obvious live OpenAI/private-key material.

If `.env` was accidentally committed before adding `.gitignore`, simply adding
it to `.gitignore` is not enough. Remove it from the index and rotate any
exposed API key.

## Local Windows build

Install Inno Setup 6 or 7 once, then:

```powershell
.\build_release.ps1 -Version 1.0.0
```

Artifacts appear in:

```text
release\
```

A portable-only build is:

```powershell
.\build_release.ps1 -Version 1.0.0 -SkipInstaller
```

## GitHub automatic release

The repository includes `.github/workflows/release.yml`.

Commit and push the project, then tag a release:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions will build on `windows-latest`, create:

- `JARVIS-Setup-1.0.0.exe`
- `JARVIS-Portable-1.0.0.zip`
- `SHA256SUMS.txt`
- `requirements-lock.txt`
- `BUILD-INFO.txt`

and attach them to a GitHub Release.

You can also run the workflow manually from GitHub's Actions tab. A manual run
builds downloadable workflow artifacts but does not create a GitHub Release
unless it was triggered by a `v*` tag.

## Updating a release

1. Make and test changes.
2. Update README/changelog as appropriate.
3. Commit and push.
4. Create a new semantic version tag, e.g.:

```powershell
git tag v1.1.0
git push origin v1.1.0
```

Do not reuse a published version tag.

## Windows SmartScreen

Unsigned applications downloaded from the internet may trigger Microsoft
Defender SmartScreen warnings. A normal open-source GitHub release can still be
distributed unsigned, but broad public distribution is cleaner with an
Authenticode code-signing certificate.

Code signing is optional and is intentionally not automated by this repository,
because signing keys/certificates must be handled as secrets.

## What users need after installation

The packaged app includes Python and its Python libraries; users do not need to
install Python.

On first run:

1. Open the tray icon.
2. Choose **Open Configuration**.
3. Put the user's OpenAI API key in `.env`.
4. Restart/start JARVIS from the tray.

Optional features have external requirements:

- Ollama must be installed separately if local model routing is desired.
- SSH/OpenSSH must be available for remote-node features.
- Each user's SSH keys are generated on their own machine and are never shipped
  inside a release.
- Faster-Whisper/openWakeWord model assets may download on first use if not
  already cached.
