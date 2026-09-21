import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

import psutil

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = Path.home() / "Jarvis" / "data"
SETTINGS_PATH = DATA_DIR / "health_settings.json"
LOG_PATH = PROJECT_DIR / "logs" / "jarvis.log"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
OLLAMA_MODEL = os.getenv("OLLAMA_ROUTER_MODEL", "qwen3.5:0.8b")

DEFAULT_SETTINGS = {
    "enabled": True,
    "check_interval_seconds": 30,
    "alert_cooldown_seconds": 1800,
    "ram_warning_percent": 90.0,
    "ram_critical_percent": 95.0,
    "disk_warning_percent": 92.0,
    "cpu_warning_percent": 95.0,
    "cpu_consecutive_checks": 4,
    "battery_warning_percent": 15.0,
    "unload_ollama_on_ram_critical": True,
    "remote_monitor_enabled": False,
    "remote_check_interval_seconds": 300,
    "remote_failure_threshold": 2,
}

REQUIRED_PROJECT_FILES = [
    "jarvis.py",
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
    "tray_app.py",
]

REQUIRED_PACKAGES = [
    "openai",
    "dotenv",
    "psutil",
    "pypdf",
    "mss",
    "pyautogui",
    "playwright",
    "faster_whisper",
    "sounddevice",
    "numpy",
    "pyttsx3",
    "openwakeword",
    "pystray",
    "PIL",
    "pycaw",
    "pygetwindow",
    "pyperclip",
    "winotify",
    "send2trash",
]


def _coerce_setting(key, value):
    if key not in DEFAULT_SETTINGS:
        raise KeyError(f"Unknown health setting: {key}")

    template = DEFAULT_SETTINGS[key]

    if isinstance(template, bool):
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on", "enable", "enabled"}:
            return True
        if text in {"0", "false", "no", "off", "disable", "disabled"}:
            return False
        raise ValueError(f"Invalid boolean value for {key}: {value}")

    if isinstance(template, int) and not isinstance(template, bool):
        return int(value)

    if isinstance(template, float):
        return float(value)

    return str(value)


def load_health_settings():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    settings = dict(DEFAULT_SETTINGS)

    if SETTINGS_PATH.exists():
        try:
            stored = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                for key, value in stored.items():
                    if key in DEFAULT_SETTINGS:
                        try:
                            settings[key] = _coerce_setting(key, value)
                        except Exception:
                            pass
        except Exception:
            pass

    return settings


def save_health_settings(settings):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    normalized = dict(DEFAULT_SETTINGS)
    for key in normalized:
        if key in settings:
            normalized[key] = _coerce_setting(key, settings[key])

    SETTINGS_PATH.write_text(
        json.dumps(normalized, indent=2),
        encoding="utf-8",
    )

    return {
        "success": True,
        "path": str(SETTINGS_PATH),
        "settings": normalized,
    }


def set_health_setting(key, value):
    try:
        settings = load_health_settings()
        settings[str(key)] = _coerce_setting(str(key), value)
        return save_health_settings(settings)
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_monitor_enabled(enabled):
    return set_health_setting("enabled", enabled)


def get_health_settings():
    return {
        "success": True,
        "path": str(SETTINGS_PATH),
        "settings": load_health_settings(),
    }


def _battery_snapshot():
    try:
        battery = psutil.sensors_battery()
    except Exception:
        battery = None

    if battery is None:
        return None

    return {
        "percent": round(float(battery.percent), 1),
        "plugged_in": bool(battery.power_plugged),
        "seconds_left": None if battery.secsleft in {psutil.POWER_TIME_UNKNOWN, psutil.POWER_TIME_UNLIMITED} else battery.secsleft,
    }


def get_health_snapshot(sample_cpu=True):
    try:
        cpu = psutil.cpu_percent(interval=0.25 if sample_cpu else None)
        memory = psutil.virtual_memory()
        system_drive = os.environ.get("SystemDrive", "C:") + "\\"
        disk = psutil.disk_usage(system_drive)
        process = psutil.Process(os.getpid())

        child_ram = 0
        child_count = 0
        for child in process.children(recursive=True):
            try:
                child_ram += child.memory_info().rss
                child_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        boot_time = psutil.boot_time()

        return {
            "success": True,
            "cpu_percent": round(float(cpu), 1),
            "ram": {
                "percent": round(float(memory.percent), 1),
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "available_gb": round(memory.available / (1024 ** 3), 2),
                "total_gb": round(memory.total / (1024 ** 3), 2),
            },
            "disk": {
                "drive": system_drive,
                "percent": round(float(disk.percent), 1),
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2),
                "total_gb": round(disk.total / (1024 ** 3), 2),
            },
            "jarvis_process": {
                "pid": process.pid,
                "ram_mb": round(process.memory_info().rss / (1024 ** 2), 1),
                "child_processes": child_count,
                "children_ram_mb": round(child_ram / (1024 ** 2), 1),
            },
            "battery": _battery_snapshot(),
            "system_uptime_hours": round((time.time() - boot_time) / 3600, 1),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def unload_ollama_model(model=None):
    model = str(model or OLLAMA_MODEL).strip()
    executable = shutil.which("ollama")

    if not executable:
        return {
            "success": False,
            "error": "ollama executable was not found.",
        }

    try:
        result = subprocess.run(
            [executable, "stop", model],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=CREATE_NO_WINDOW,
        )

        return {
            "success": result.returncode == 0,
            "model": model,
            "return_code": result.returncode,
            "stdout": (result.stdout or "").strip()[:5000],
            "stderr": (result.stderr or "").strip()[:5000],
        }
    except Exception as e:
        return {"success": False, "error": str(e), "model": model}


def _ollama_status():
    try:
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/tags",
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=1.5) as response:
            payload = json.loads(response.read().decode("utf-8"))

        names = [item.get("name", "") for item in payload.get("models", [])]
        return {
            "running": True,
            "router_model_installed": any(name == OLLAMA_MODEL for name in names),
            "model": OLLAMA_MODEL,
        }
    except Exception as e:
        return {
            "running": False,
            "router_model_installed": False,
            "model": OLLAMA_MODEL,
            "error": str(e),
        }


def _configured_nodes():
    db_path = DATA_DIR / "nodes.db"
    if not db_path.exists():
        return []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT name, host, username, port, identity_file FROM nodes WHERE enabled=1 ORDER BY name LIMIT 5"
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception:
        return []


def _check_node(node):
    ssh = shutil.which("ssh")
    if not ssh:
        return {"success": False, "error": "ssh.exe not found"}

    args = [
        ssh,
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=5",
        "-p", str(node.get("port") or 22),
    ]

    identity = node.get("identity_file")
    if identity:
        identity_path = Path(os.path.expandvars(os.path.expanduser(identity))).resolve(strict=False)
        args.extend(["-o", "IdentitiesOnly=yes", "-i", str(identity_path)])

    args.extend([
        f"{node['username']}@{node['host']}",
        "printf JARVIS_REMOTE_OK",
    ])

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=CREATE_NO_WINDOW,
        )
        return {
            "success": result.returncode == 0 and "JARVIS_REMOTE_OK" in (result.stdout or ""),
            "return_code": result.returncode,
            "stderr": (result.stderr or "").strip()[:3000],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_diagnostics(project_dir=None, check_remote=True):
    project = Path(project_dir or PROJECT_DIR).resolve(strict=False)
    checks = []
    issues = []

    def add(name, ok, detail):
        entry = {"name": name, "ok": bool(ok), "detail": str(detail)}
        checks.append(entry)
        if not ok:
            issues.append(entry)

    for filename in REQUIRED_PROJECT_FILES:
        path = project / filename
        add(f"file:{filename}", path.exists(), path)

    env_path = project / ".env"
    add("file:.env", env_path.exists(), env_path)
    add("env:OPENAI_API_KEY", bool(os.getenv("OPENAI_API_KEY")), "present" if os.getenv("OPENAI_API_KEY") else "missing")

    for module_name in REQUIRED_PACKAGES:
        add(f"python:{module_name}", importlib.util.find_spec(module_name) is not None, "installed" if importlib.util.find_spec(module_name) else "missing")

    for command in ("ssh", "scp", "ollama"):
        location = shutil.which(command)
        add(f"command:{command}", bool(location), location or "not found")

    ollama = _ollama_status()
    add("ollama:server", ollama.get("running"), ollama.get("error") or "online")
    add("ollama:router_model", ollama.get("router_model_installed"), OLLAMA_MODEL)

    snapshot = get_health_snapshot()
    add("health:snapshot", snapshot.get("success"), snapshot.get("error") or "ok")

    for filename in ("memory.db", "scheduler.db", "api_usage.db", "nodes.db", "routines.db"):
        path = DATA_DIR / filename
        add(f"data:{filename}", path.exists(), path)

    if LOG_PATH.exists():
        add("log:jarvis.log", True, f"{LOG_PATH.stat().st_size / (1024 ** 2):.2f} MB")
    else:
        add("log:jarvis.log", False, "log file not created yet")

    remote_results = []
    if check_remote:
        for node in _configured_nodes():
            result = _check_node(node)
            remote_results.append({"name": node["name"], **result})
            add(
                f"remote:{node['name']}",
                result.get("success"),
                "reachable" if result.get("success") else result.get("error") or result.get("stderr") or "unreachable",
            )

    return {
        "success": len(issues) == 0,
        "project_dir": str(project),
        "checks": checks,
        "issues": issues,
        "issue_count": len(issues),
        "health": snapshot,
        "remote": remote_results,
    }


def format_health_summary(snapshot=None):
    snapshot = snapshot or get_health_snapshot()
    if not snapshot.get("success"):
        return "Health check failed: " + snapshot.get("error", "unknown error")

    ram = snapshot["ram"]
    disk = snapshot["disk"]
    battery = snapshot.get("battery")

    parts = [
        f"CPU {snapshot['cpu_percent']:.0f}%",
        f"RAM {ram['percent']:.0f}% ({ram['used_gb']:.1f}/{ram['total_gb']:.1f} GB)",
        f"disk {disk['percent']:.0f}% used ({disk['free_gb']:.1f} GB free)",
        f"Jarvis {snapshot['jarvis_process']['ram_mb']:.0f} MB",
    ]

    if battery:
        power = "plugged in" if battery["plugged_in"] else "on battery"
        parts.append(f"battery {battery['percent']:.0f}% ({power})")

    return ". ".join(parts) + "."


def format_diagnostics_summary(result=None):
    result = result or run_diagnostics()
    if result.get("issue_count", 0) == 0:
        return f"Diagnostics passed: {len(result.get('checks', []))} checks, no issues found."

    problems = result.get("issues", [])[:6]
    summary = "; ".join(f"{item['name']}: {item['detail']}" for item in problems)
    extra = result.get("issue_count", 0) - len(problems)
    if extra > 0:
        summary += f"; plus {extra} more issue(s) in the log."

    return f"Diagnostics found {result.get('issue_count', 0)} issue(s): {summary}"


class ProactiveMonitor:
    def __init__(self, alert_callback=None):
        self.alert_callback = alert_callback
        self._stop_event = threading.Event()
        self._thread = None
        self._last_alert = {}
        self._cpu_high_count = 0
        self._last_remote_check = 0.0
        self._remote_failures = {}

    def start(self):
        if self._thread and self._thread.is_alive():
            return {"success": True, "already_running": True}

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="JarvisHealthMonitor",
        )
        self._thread.start()
        return {"success": True, "running": True}

    def stop(self):
        self._stop_event.set()
        return {"success": True}

    def status(self):
        return {
            "success": True,
            "running": bool(self._thread and self._thread.is_alive()),
            "settings": load_health_settings(),
        }

    def _can_alert(self, key, cooldown):
        now = time.time()
        previous = self._last_alert.get(key, 0.0)
        if now - previous < cooldown:
            return False
        self._last_alert[key] = now
        return True

    def _emit(self, key, level, title, message, snapshot=None):
        settings = load_health_settings()
        cooldown = max(60, int(settings["alert_cooldown_seconds"]))
        if not self._can_alert(key, cooldown):
            return

        alert = {
            "key": key,
            "level": level,
            "title": title,
            "message": message,
            "snapshot": snapshot,
            "timestamp": time.time(),
        }

        print(f"[HEALTH {level.upper()}] {message}")

        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                print("[HEALTH CALLBACK ERROR]", e)

    def _check_remote(self, settings):
        if not settings.get("remote_monitor_enabled"):
            return

        now = time.time()
        interval = max(60, int(settings["remote_check_interval_seconds"]))
        if now - self._last_remote_check < interval:
            return
        self._last_remote_check = now

        threshold = max(1, int(settings["remote_failure_threshold"]))
        for node in _configured_nodes():
            result = _check_node(node)
            name = node["name"]

            if result.get("success"):
                self._remote_failures[name] = 0
                continue

            failures = self._remote_failures.get(name, 0) + 1
            self._remote_failures[name] = failures

            if failures >= threshold:
                self._emit(
                    f"remote:{name}",
                    "warning",
                    "JARVIS remote node",
                    f"Remote node {name} has failed {failures} consecutive health checks.",
                )

    def _run(self):
        # Prime psutil's non-blocking CPU counter.
        psutil.cpu_percent(interval=None)

        while not self._stop_event.is_set():
            settings = load_health_settings()

            if not settings.get("enabled"):
                self._stop_event.wait(5)
                continue

            snapshot = get_health_snapshot(sample_cpu=False)
            if snapshot.get("success"):
                ram_percent = snapshot["ram"]["percent"]
                disk_percent = snapshot["disk"]["percent"]
                cpu_percent = snapshot["cpu_percent"]
                battery = snapshot.get("battery")

                if ram_percent >= float(settings["ram_critical_percent"]):
                    unload_note = ""
                    if settings.get("unload_ollama_on_ram_critical"):
                        result = unload_ollama_model()
                        if result.get("success"):
                            unload_note = " I unloaded the local Ollama router to free RAM."
                    self._emit(
                        "ram_critical",
                        "critical",
                        "JARVIS memory warning",
                        f"System RAM is at {ram_percent:.0f}%.{unload_note}",
                        snapshot,
                    )
                elif ram_percent >= float(settings["ram_warning_percent"]):
                    self._emit(
                        "ram_warning",
                        "warning",
                        "JARVIS memory warning",
                        f"System RAM is at {ram_percent:.0f}%.",
                        snapshot,
                    )

                if disk_percent >= float(settings["disk_warning_percent"]):
                    self._emit(
                        "disk_warning",
                        "warning",
                        "JARVIS disk warning",
                        f"System disk is {disk_percent:.0f}% full with {snapshot['disk']['free_gb']:.1f} GB free.",
                        snapshot,
                    )

                if cpu_percent >= float(settings["cpu_warning_percent"]):
                    self._cpu_high_count += 1
                else:
                    self._cpu_high_count = 0

                if self._cpu_high_count >= int(settings["cpu_consecutive_checks"]):
                    self._emit(
                        "cpu_warning",
                        "warning",
                        "JARVIS CPU warning",
                        f"CPU has remained near {cpu_percent:.0f}% for multiple checks.",
                        snapshot,
                    )
                    self._cpu_high_count = 0

                if battery and not battery["plugged_in"] and battery["percent"] <= float(settings["battery_warning_percent"]):
                    self._emit(
                        "battery_warning",
                        "warning",
                        "JARVIS battery warning",
                        f"Battery is at {battery['percent']:.0f}% and the laptop is not plugged in.",
                        snapshot,
                    )

            self._check_remote(settings)

            interval = max(10, int(settings["check_interval_seconds"]))
            self._stop_event.wait(interval)


# Ensure a settings file exists for discoverability/editing.
if not SETTINGS_PATH.exists():
    try:
        save_health_settings(DEFAULT_SETTINGS)
    except Exception:
        pass
