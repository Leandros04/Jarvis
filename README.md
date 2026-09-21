# JARVIS for Windows

A local-first Windows personal assistant inspired by the idea of JARVIS: always available by voice, able to operate the computer, browse the web, remember useful information, run timers/reminders, control remote Linux/Raspberry Pi nodes, and execute reusable routines.

The project is intentionally designed to keep recurring cost low. Wake-word detection, speech recognition, speech output, timers, reminders, most desktop controls, persistent memory, routines, health monitoring, SSH, and many common commands run locally. OpenAI is used mainly for natural-language reasoning and tool selection.

## Current capabilities

- Always-listening **"Hey Jarvis"** wake word
- Local speech-to-text using Faster-Whisper
- Local Windows text-to-speech
- OpenAI Responses API for reasoning and function/tool calls
- Cost-aware model routing between GPT-5.6 Luna, Terra, and Sol
- Optional local Ollama/Qwen router to choose the cloud model without spending API tokens
- Persistent SQLite memory
- Windows application discovery and launching
- Mouse and keyboard control
- Screenshot analysis / screen vision
- Playwright-controlled Chromium browser
- File search, reading, creation, copying, moving, renaming, and Recycle Bin deletion
- PDF, text, source-code, JSON, and CSV reading
- Volume, mute, media controls, clipboard, and window management
- Windows notifications
- Timers and persistent reminders
- Process and network inspection
- Confirmation-gated PowerShell, process termination, and power/session actions
- Remote SSH nodes, including Raspberry Pi/Linux hosts
- SCP upload/download
- Persistent named multi-step routines
- System-tray background operation and Windows startup
- Crash recovery and log rotation
- Proactive RAM, CPU, disk, and battery monitoring
- API token/cost accounting
- Installation diagnostics

---

## Architecture

```text
Microphone
   |
   v
openWakeWord                 local / free
   |
"Hey Jarvis"
   |
   v
Faster-Whisper               local / free
   |
text
   |
   +--> local fast commands  local / free
   |
   +--> optional Qwen router local / free
   |         |
   |         +--> Luna / Terra / Sol selection
   |
   v
OpenAI Responses API         paid only when AI reasoning is needed
   |
   v
Tool broker
   |
   +--> Windows / files / browser / memory / timers
   +--> Raspberry Pi / SSH
   +--> routines
   +--> confirmation gate for risky actions
   |
   v
Windows SAPI speech          local / free
```

For an 8 GB RAM machine, the recommended Ollama router is `qwen3.5:0.8b`. It is used only as a lightweight routing classifier, not as the main assistant brain.

---

## Recommended system

- Windows 10 or Windows 11
- Python 3.11 recommended
- Microphone
- Internet connection for OpenAI requests
- 8 GB RAM works with the recommended configuration
- Windows OpenSSH Client if remote nodes are used
- Optional: Ollama for local model routing
- Optional: Raspberry Pi or Linux host for remote-node features

The project is primarily Windows-specific. Several modules use Windows APIs, SAPI5, PowerShell, Windows notifications, and Windows window-management libraries.

---

## Project structure

```text
Jarvis/
├── jarvis.py               Main assistant / tool broker
├── tray_app.py             Background tray launcher + crash recovery
├── system_tools.py         Windows status, apps, screen, files, mouse/keyboard
├── browser_tools.py        Persistent Playwright Chromium control
├── memory_tools.py         Persistent local memory
├── voice_tools.py          Local speech recognition + speech output
├── wakeword_tools.py       Local "Hey Jarvis" wake-word detection
├── desktop_tools.py        Audio, media, clipboard, windows, notifications
├── scheduler_tools.py      Persistent timers/reminders
├── admin_tools.py          File admin, processes, networking, PowerShell, power
├── ai_router.py            Luna/Terra/Sol model router + optional Ollama
├── cost_tracker.py         API-token and estimated-cost accounting
├── remote_tools.py         SSH nodes and SCP transfer
├── routine_tools.py        Persistent named routines
├── health_tools.py         Monitoring, diagnostics, RAM management
├── requirements.txt
├── .env                    Local secrets/config; never commit this
├── .env.example            Example configuration
├── browser_profile/        Persistent Chromium profile
├── logs/
│   └── jarvis.log
└── data/                   SQLite/settings data (under %USERPROFILE%\Jarvis\data)
```

---

# Installation

## 1. Install Python

Install Python 3.11 for Windows and ensure `python` works in PowerShell:

```powershell
python --version
```

## 2. Create the project folder

The recommended location is:

```powershell
mkdir "$env:USERPROFILE\Jarvis" -Force
cd "$env:USERPROFILE\Jarvis"
```

Copy all project `.py` files, `requirements.txt`, and `.env.example` into this folder.

## 3. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

## 4. Install Python dependencies

```powershell
python -m pip install -r requirements.txt
```

Install Playwright's Chromium browser:

```powershell
python -m playwright install chromium
```

## 5. Configure OpenAI

Copy the example file:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set:

```text
OPENAI_API_KEY=your_api_key_here
```

Do not put the API key directly in Python source files, Git commits, screenshots, chat messages, or the Jarvis memory database.

Jarvis currently routes requests between:

- `gpt-5.6-luna` — inexpensive default
- `gpt-5.6-terra` — harder work
- `gpt-5.6-sol` — highest-capability work

OpenAI model availability and pricing can change. Check the official OpenAI API model documentation when updating the project.

---

# Optional: Ollama local router

Ollama is optional. Jarvis still works if it is unavailable.

Install Ollama for Windows, then pull the small router model:

```powershell
ollama pull qwen3.5:0.8b
```

`.env` defaults:

```text
OLLAMA_ROUTER_ENABLED=1
OLLAMA_ROUTER_MODEL=qwen3.5:0.8b
OLLAMA_URL=http://127.0.0.1:11434
```

Check it:

```powershell
ollama list
```

For 8 GB systems, do not leave a large local model loaded alongside Chromium, Whisper, and normal Windows applications. Jarvis can unload the router automatically if RAM becomes critically high.

Manual unload:

```powershell
ollama stop qwen3.5:0.8b
```

Or tell Jarvis:

```text
Hey Jarvis
Free some memory
```

---

# Voice setup

Test the microphone and local speech system before running the full assistant:

```powershell
python voice_tools.py
```

The first Faster-Whisper run may download its model. Subsequent transcription runs locally.

Test the wake word:

```powershell
python wakeword_tools.py
```

Say:

```text
Hey Jarvis
```

The wake model should trigger and beep.

---

# Run Jarvis in the foreground

```powershell
python jarvis.py
```

Jarvis starts in wake-word mode by default.

Typical interaction:

```text
You: "Hey Jarvis"
[beep]
You: "Open Calculator"
```

Useful local commands:

```text
/wake
/voice
/text
/mute
/unmute
/new
/auto
/luna
/terra
/sol
/cost
/router
/health
/diagnostics
/monitor on
/monitor off
/nodes
/routines
```

---

# Run Jarvis in the background

Run:

```powershell
python tray_app.py
```

A JARVIS icon appears in the Windows system tray.

The tray provides:

- Start Jarvis
- Stop Jarvis
- Restart Jarvis
- Open Log
- Open Jarvis Folder
- Open Data Folder
- Start with Windows
- Remove Windows Startup
- Exit Jarvis

The tray launcher automatically restarts Jarvis after unexpected crashes. If Jarvis repeatedly crashes in a short period, automatic restart is stopped to avoid a crash loop.

Logs are rotated automatically once `jarvis.log` becomes large.

## Start automatically with Windows

Right-click the tray icon and select:

```text
Start with Windows
```

---

# Raspberry Pi / Linux remote node setup

Remote automation uses SSH public-key authentication. Password authentication can remain enabled on the Pi as a manual fallback, but background Jarvis does **not** store or type the password.

## 1. Create a dedicated Jarvis key

```powershell
mkdir "$env:USERPROFILE\.ssh" -Force
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\jarvis_ed25519" -C "jarvis@$env:COMPUTERNAME"
```

For unattended background operation, leave the Jarvis key passphrase empty. This is a security tradeoff: protect the Windows account and private key carefully.

## 2. Install the public key on the remote host

Example placeholders:

```text
REMOTE_USER
REMOTE_HOST
```

Copy the key using password authentication:

```powershell
scp -o PubkeyAuthentication=no -o PreferredAuthentications=password "$env:USERPROFILE\.ssh\jarvis_ed25519.pub" REMOTE_USER@REMOTE_HOST:/tmp/jarvis_ed25519.pub
```

Then install it:

```powershell
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password REMOTE_USER@REMOTE_HOST 'mkdir -p ~/.ssh; chmod 700 ~/.ssh; touch ~/.ssh/authorized_keys; chmod 600 ~/.ssh/authorized_keys; grep -qxF "$(cat /tmp/jarvis_ed25519.pub)" ~/.ssh/authorized_keys || cat /tmp/jarvis_ed25519.pub >> ~/.ssh/authorized_keys; rm -f /tmp/jarvis_ed25519.pub'
```

## 3. Add an SSH config entry

Edit:

```text
%USERPROFILE%\.ssh\config
```

Example:

```text
Host my-pi
    HostName my-pi
    User myuser
    IdentityFile ~/.ssh/jarvis_ed25519
    IdentitiesOnly yes
    PreferredAuthentications publickey,password
    ConnectTimeout 8
```

Password authentication remains available when the server allows it. Jarvis background commands use `BatchMode=yes`, so they will never hang waiting for a password prompt.

Test unattended authentication:

```powershell
ssh -o BatchMode=yes my-pi "echo JARVIS_SSH_OK && hostname && whoami"
```

## 4. Register the node with Jarvis

You can configure a first node in `.env`:

```text
JARVIS_DEFAULT_NODE_NAME=my-pi
JARVIS_DEFAULT_NODE_HOST=my-pi
JARVIS_DEFAULT_NODE_USER=myuser
JARVIS_DEFAULT_NODE_PORT=22
JARVIS_SSH_IDENTITY=%USERPROFILE%\.ssh\jarvis_ed25519
```

Restart Jarvis afterward.

Or add one conversationally:

```text
Hey Jarvis
Add a remote node called my-pi at myuser@my-pi on port 22 using my Jarvis SSH key
```

Adding/updating a remote node is confirmation-gated.

Example commands:

```text
What's the status of my-pi?
List my home directory on my-pi.
Read /etc/hostname on my-pi.
Upload C:\Users\me\Desktop\file.txt to /home/myuser/file.txt on my-pi.
Download /home/myuser/file.txt to C:\Users\me\Desktop\file-copy.txt.
Run uptime on my-pi.
```

Arbitrary remote shell commands require explicit confirmation.

---

# Routines

Routines are persistent named workflows stored in SQLite.

Example:

```text
Create a routine called Coding Mode that sets volume to 20 percent,
opens Visual Studio Code, and opens C:\Users\me\Projects.
```

Run it later:

```text
Run Coding Mode.
```

List routines:

```text
/routines
```

Routine steps are restricted to a safe allowlist. Dangerous actions such as arbitrary PowerShell, arbitrary SSH commands, raw mouse/keyboard actions, process termination, power controls, and destructive deletion cannot be silently embedded inside routines.

---

# Confirmation broker

Sensitive operations are intentionally two-stage.

Example:

```text
Hey Jarvis
Restart the computer
```

Jarvis queues the operation rather than performing it.

Then say:

```text
Confirm
```

or:

```text
Cancel
```

Protected operations include:

- PowerShell execution
- Process termination
- Windows shutdown/restart/sleep/sign-out/lock operations
- Arbitrary SSH shell commands
- Adding/changing remote-node definitions

Pending confirmations expire automatically.

---

# Proactive monitoring and reliability

Jarvis monitors local resource pressure without using OpenAI.

Default warnings include:

- RAM >= 90%
- RAM critical >= 95%
- System disk >= 92% full
- CPU >= 95% for multiple consecutive checks
- Battery <= 15% while unplugged

On critical memory pressure, Jarvis can unload the local Ollama router model automatically.

Settings are stored in:

```text
%USERPROFILE%\Jarvis\data\health_settings.json
```

Commands:

```text
/health
/diagnostics
/monitor on
/monitor off
```

`/diagnostics` checks project files, Python dependencies, `.env`, OpenAI-key presence, Ollama, SSH/SCP, SQLite databases, log state, system health, and configured remote-node connectivity.

Remote-node proactive polling is disabled by default because laptops frequently leave the home network. It can be enabled by editing `health_settings.json`:

```json
"remote_monitor_enabled": true
```

---

# Cost control

Most of Jarvis does not need a cloud model.

Zero-API or local operations include wake detection, speech recognition, TTS, volume/media commands, common timers, reminders firing, memory storage, local file operations, routines, SSH execution after approval, monitoring, and tray/watchdog behavior.

Normal AI requests default to GPT-5.6 Luna. The router can elevate harder tasks to Terra or Sol.

Check recent estimated API cost:

```text
/cost
```

The cost tracker is an estimate based on recorded token usage and configured model prices. Your OpenAI billing dashboard remains the source of truth for actual charges.

---

# Data and persistence

Persistent data is stored under:

```text
%USERPROFILE%\Jarvis\data
```

Typical files:

```text
memory.db
scheduler.db
api_usage.db
nodes.db
routines.db
health_settings.json
```

The browser profile is stored separately inside the project folder so website sessions can persist.

Do not share the data directory blindly. It can contain personal memory, routine definitions, remote-node metadata, and usage history.

---

# Security notes

This project has broad control over a Windows computer. Treat it like automation software with local user privileges.

Recommended rules:

1. Never put passwords or API keys into Jarvis memory.
2. Keep `.env` out of source control.
3. Never share private SSH keys.
4. Use a dedicated SSH key for Jarvis.
5. Keep password SSH login available only if you intentionally want it as recovery/fallback.
6. Keep high-impact actions behind confirmation.
7. Do not remove the PyAutoGUI fail-safe; moving the mouse to the top-left corner should remain an emergency stop for GUI automation.
8. Test routines before relying on them for important workflows.
9. Keep Windows, Python packages, OpenSSH, Ollama, and browsers updated.
10. Review `logs\jarvis.log` when something behaves unexpectedly.

---

# Troubleshooting

## Jarvis does not hear me

Run:

```powershell
python voice_tools.py
```

Check the Windows default microphone and microphone privacy permissions.

## "Hey Jarvis" does not trigger

Run:

```powershell
python wakeword_tools.py
```

Try saying **"Hey Jarvis"** clearly. The current pretrained wake model is more reliable with the full phrase than with only "Jarvis".

## Browser automation fails

Reinstall Chromium:

```powershell
python -m playwright install chromium
```

If the browser profile becomes corrupted, stop Jarvis, back up `browser_profile`, and test with a fresh profile.

## OpenAI errors

Confirm `.env` contains `OPENAI_API_KEY` and restart Jarvis.

Use:

```text
/diagnostics
```

Also check that your account/API project has access to the configured model IDs.

## Ollama router is offline

Jarvis automatically falls back to its built-in routing logic. This does not prevent normal operation.

Check:

```powershell
ollama list
ollama ps
```

Pull the recommended router if needed:

```powershell
ollama pull qwen3.5:0.8b
```

## SSH says `Permission denied (publickey,password)` in BatchMode

First test the exact key manually:

```powershell
ssh -i "$env:USERPROFILE\.ssh\jarvis_ed25519" -o IdentitiesOnly=yes -o PasswordAuthentication=no REMOTE_USER@REMOTE_HOST "echo OK"
```

If it asks for an SSH-key passphrase, the key cannot be used by unattended `BatchMode=yes` unless the key is unlocked through an agent or its passphrase is removed. A dedicated no-passphrase automation key is the simplest setup for this project.

Manual password login can remain enabled as fallback.

## High RAM usage on an 8 GB machine

Ask:

```text
Free some memory
```

or run:

```powershell
ollama stop qwen3.5:0.8b
```

Avoid using large Ollama models while Chromium and Faster-Whisper are active.

## Background Jarvis keeps restarting

Open:

```text
Tray icon -> Open Log
```

The tray watchdog limits repeated automatic restarts. Fix the logged exception, then use **Restart Jarvis**.

---

# Development workflow

For development/debugging, stop the tray-managed instance and run:

```powershell
python jarvis.py
```

This keeps stdout visible.

Before replacing a module, syntax-check it:

```powershell
python -m py_compile jarvis.py
```

For multiple files:

```powershell
python -m compileall .
```

Then restart the tray version.

---

# Useful example commands

```text
Hey Jarvis, open Calculator.
Hey Jarvis, what is using the most RAM?
Hey Jarvis, set the volume to 25 percent.
Hey Jarvis, pause the music.
Hey Jarvis, remind me in 20 minutes to check the oven.
Hey Jarvis, remind me tomorrow at 6 PM to call John.
Hey Jarvis, what's on my clipboard?
Hey Jarvis, bring Spotify to the front.
Hey Jarvis, find my assignment PDF.
Hey Jarvis, read the first three pages of this PDF.
Hey Jarvis, look at my screen and tell me what I'm looking at.
Hey Jarvis, search the web for Python documentation.
Hey Jarvis, what do you remember about my Raspberry Pi?
Hey Jarvis, what's the status of my-pi?
Hey Jarvis, run Coding Mode.
Hey Jarvis, system health.
Hey Jarvis, run diagnostics.
```

---

# What is intentionally not fully autonomous

Some actions should remain explicit rather than being silently delegated:

- passwords and credentials
- purchases and financial transactions
- account deletion
- arbitrary shell/PowerShell execution
- remote shell execution
- killing processes
- computer shutdown/restart
- other high-consequence irreversible actions

The goal is broad capability without turning one misunderstood voice command into a destructive operation.

---

# Status

The core assistant architecture is complete enough for daily use:

```text
Voice / wake word              complete
Persistent memory              complete
Windows control                complete
Browser agent                  complete
Screen vision                  complete
Files                          complete
Media / clipboard              complete
Timers / reminders             complete
Processes / PowerShell         complete
Confirmation broker            complete
Background tray / autostart    complete
Cost-aware model routing       complete
Local Ollama router            complete
API cost tracking              complete
Remote SSH nodes               complete
Reusable routines              complete
Health monitoring              complete
Crash recovery / log rotation  complete
Diagnostics                    complete
```

Future work can be treated as optional integrations and refinement rather than fundamental architecture.


---

# Windows packages and GitHub Releases

The repository includes a reproducible Windows packaging pipeline.

## Release formats

A release produces:

```text
JARVIS-Setup-X.Y.Z.exe
JARVIS-Portable-X.Y.Z.zip
SHA256SUMS.txt
requirements-lock.txt
BUILD-INFO.txt
```

The **installer `.exe`** is the recommended download for normal users. The
portable ZIP contains a one-folder application with `JARVIS.exe` as its tray
launcher and `JARVIS-Core.exe` as the background core.

Users of these packaged builds do **not** need Python installed.

## Build locally

First run the secret/runtime-data preflight:

```powershell
.\preflight_release.ps1
```

Then, on Windows, install Inno Setup 6 or 7 and run:

```powershell
.\build_release.ps1 -Version 1.0.0
```

The output is written to `release\`.

See [RELEASING.md](RELEASING.md) for the full release procedure.

## Publish automatically with GitHub Actions

Push a semantic version tag:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

The `Build Windows release` workflow builds the application on a Windows GitHub
runner and creates a GitHub Release automatically.

## First run of an installed build

The installer deliberately does **not** contain `.env` or any private key.

On the first launch, the tray app creates `.env` from `.env.example`. Open the
tray menu and choose **Open Configuration**, then add the user's API key and
restart JARVIS.

Optional Ollama and SSH features are configured separately on each user's
machine.

## SmartScreen

Public unsigned Windows executables can trigger Microsoft Defender SmartScreen.
That does not mean the application failed to package correctly. For polished
wide distribution, sign `JARVIS.exe`, `JARVIS-Core.exe`, and the installer with
an Authenticode code-signing certificate.
