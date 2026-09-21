import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import pystray
from PIL import Image, ImageDraw


IS_FROZEN = bool(getattr(sys, "frozen", False))
PROJECT_DIR = (
    Path(sys.executable).resolve().parent
    if IS_FROZEN
    else Path(__file__).resolve().parent
)

CORE_EXE = PROJECT_DIR / "JARVIS-Core.exe"
JARVIS_SCRIPT = PROJECT_DIR / "jarvis.py"
ENV_FILE = PROJECT_DIR / ".env"
ENV_EXAMPLE = PROJECT_DIR / ".env.example"

LOG_DIR = PROJECT_DIR / "logs"
LOG_FILE = LOG_DIR / "jarvis.log"
MAX_LOG_BYTES = 3 * 1024 * 1024
LOG_BACKUPS = 3

STARTUP_DIR = (
    Path(os.environ["APPDATA"])
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs"
    / "Startup"
)
STARTUP_FILE = STARTUP_DIR / "JarvisAssistant.vbs"

CURRENT_PYTHON = Path(sys.executable)
PYTHONW = CURRENT_PYTHON.with_name("pythonw.exe")
if not PYTHONW.exists():
    PYTHONW = CURRENT_PYTHON

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

jarvis_process = None
jarvis_log_handle = None
process_lock = threading.RLock()
desired_running = True
shutting_down = False
restart_history = []
RESTART_WINDOW_SECONDS = 600
MAX_AUTOMATIC_RESTARTS = 5


def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def rotate_logs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if not LOG_FILE.exists() or LOG_FILE.stat().st_size < MAX_LOG_BYTES:
        return

    for index in range(LOG_BACKUPS, 0, -1):
        source = LOG_DIR / (
            "jarvis.log" if index == 1 else f"jarvis.log.{index - 1}"
        )
        destination = LOG_DIR / f"jarvis.log.{index}"

        if destination.exists() and index == LOG_BACKUPS:
            try:
                destination.unlink()
            except Exception:
                pass

        if source.exists():
            try:
                source.replace(destination)
            except Exception:
                pass


def write_launcher_log(text):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(f"[{_timestamp()}] [TRAY] {text}\n")


def _close_log_handle():
    global jarvis_log_handle
    if jarvis_log_handle is not None:
        try:
            jarvis_log_handle.flush()
            jarvis_log_handle.close()
        except Exception:
            pass
        jarvis_log_handle = None


def _ensure_env_file():
    if ENV_FILE.exists():
        return

    if ENV_EXAMPLE.exists():
        try:
            shutil.copy2(ENV_EXAMPLE, ENV_FILE)
            write_launcher_log("Created .env from .env.example.")
        except Exception as e:
            write_launcher_log(f"Could not create .env: {e}")


def _read_env_value(name):
    if not ENV_FILE.exists():
        return ""

    try:
        for raw_line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == name:
                return value.strip().strip('"').strip("'")
    except Exception:
        pass

    return ""


def _configuration_ready():
    _ensure_env_file()
    return bool(_read_env_value("OPENAI_API_KEY"))


def jarvis_is_running():
    return jarvis_process is not None and jarvis_process.poll() is None


def _core_command():
    if IS_FROZEN:
        return [str(CORE_EXE)]

    return [str(PYTHONW), "-u", str(JARVIS_SCRIPT)]


def start_jarvis(icon=None, item=None, automatic=False):
    global jarvis_process, jarvis_log_handle, desired_running

    with process_lock:
        desired_running = True

        if jarvis_is_running():
            if not automatic:
                write_launcher_log("Start requested, but Jarvis is already running.")
            return

        if IS_FROZEN:
            if not CORE_EXE.exists():
                write_launcher_log(f"Core executable not found: {CORE_EXE}")
                return
        elif not JARVIS_SCRIPT.exists():
            write_launcher_log(f"jarvis.py not found: {JARVIS_SCRIPT}")
            return

        if not _configuration_ready():
            write_launcher_log("OPENAI_API_KEY is not configured; core not started.")
            if icon and not automatic:
                try:
                    icon.notify(
                        "Open Configuration and add OPENAI_API_KEY before starting Jarvis.",
                        "JARVIS",
                    )
                except Exception:
                    pass
            return

        rotate_logs()
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _close_log_handle()

        jarvis_log_handle = open(
            LOG_FILE,
            "a",
            encoding="utf-8",
            buffering=1,
        )
        jarvis_log_handle.write(
            "\n\n========================================\n"
            f"JARVIS START: {datetime.now()}\n"
            "========================================\n"
        )

        try:
            jarvis_process = subprocess.Popen(
                _core_command(),
                cwd=str(PROJECT_DIR),
                stdin=subprocess.PIPE,
                stdout=jarvis_log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=CREATE_NO_WINDOW,
            )
            write_launcher_log(f"Jarvis started. PID={jarvis_process.pid}")

            if icon and not automatic:
                try:
                    icon.notify("Jarvis is now listening.", "JARVIS")
                except Exception:
                    pass

        except Exception as e:
            write_launcher_log(f"Failed to start Jarvis: {e}")
            jarvis_process = None
            _close_log_handle()


def _terminate_jarvis_process():
    global jarvis_process

    if not jarvis_is_running():
        jarvis_process = None
        _close_log_handle()
        return

    pid = jarvis_process.pid
    write_launcher_log(f"Stopping Jarvis PID={pid}")

    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
                timeout=10,
            )
        else:
            jarvis_process.terminate()
            try:
                jarvis_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                jarvis_process.kill()
    except Exception as e:
        write_launcher_log(f"Error while stopping Jarvis: {e}")

    jarvis_process = None
    _close_log_handle()


def stop_jarvis(icon=None, item=None):
    global desired_running
    with process_lock:
        desired_running = False
        _terminate_jarvis_process()
        write_launcher_log("Jarvis stopped by user.")

    if icon:
        try:
            icon.notify("Jarvis stopped.", "JARVIS")
        except Exception:
            pass


def restart_jarvis(icon=None, item=None):
    global desired_running
    with process_lock:
        desired_running = True
        _terminate_jarvis_process()

    time.sleep(0.7)
    start_jarvis(icon)


def open_log(icon=None, item=None):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        LOG_FILE.write_text("Jarvis log\n", encoding="utf-8")
    os.startfile(str(LOG_FILE))


def open_project_folder(icon=None, item=None):
    os.startfile(str(PROJECT_DIR))


def open_data_folder(icon=None, item=None):
    data_dir = Path.home() / "Jarvis" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    os.startfile(str(data_dir))


def open_configuration(icon=None, item=None):
    _ensure_env_file()
    if not ENV_FILE.exists():
        if icon:
            try:
                icon.notify("Could not create .env configuration file.", "JARVIS")
            except Exception:
                pass
        return

    try:
        os.startfile(str(ENV_FILE))
    except Exception:
        subprocess.Popen(["notepad.exe", str(ENV_FILE)])


def install_startup(icon=None, item=None):
    try:
        STARTUP_DIR.mkdir(parents=True, exist_ok=True)

        if IS_FROZEN:
            executable = str(Path(sys.executable).resolve()).replace('"', '""')
            content = (
                'Set shell = CreateObject("WScript.Shell")\n'
                f'shell.Run """{executable}""", 0, False\n'
            )
        else:
            pythonw = str(PYTHONW).replace('"', '""')
            tray_script = str(Path(__file__).resolve()).replace('"', '""')
            content = (
                'Set shell = CreateObject("WScript.Shell")\n'
                'shell.Run """'
                + pythonw
                + '"" ""'
                + tray_script
                + '""", 0, False\n'
            )

        STARTUP_FILE.write_text(content, encoding="utf-8")
        write_launcher_log("Windows startup installed.")

        if icon:
            try:
                icon.notify("Jarvis will start automatically with Windows.", "JARVIS")
            except Exception:
                pass
    except Exception as e:
        write_launcher_log(f"Startup installation failed: {e}")


def remove_startup(icon=None, item=None):
    try:
        if STARTUP_FILE.exists():
            STARTUP_FILE.unlink()
        write_launcher_log("Windows startup removed.")

        if icon:
            try:
                icon.notify("Automatic Windows startup removed.", "JARVIS")
            except Exception:
                pass
    except Exception as e:
        write_launcher_log(f"Could not remove startup: {e}")


def create_icon_image():
    size = 64
    image = Image.new("RGB", (size, size), "black")
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, 60, 60), outline="white", width=3)
    draw.line((38, 17, 38, 41), fill="white", width=6)
    draw.arc((18, 27, 40, 50), start=0, end=180, fill="white", width=6)
    return image


def status_text(item=None):
    if jarvis_is_running():
        return "Status: Running"
    if desired_running:
        return "Status: Ready / Not running"
    return "Status: Stopped"


def exit_tray(icon, item=None):
    global shutting_down, desired_running
    shutting_down = True
    desired_running = False
    write_launcher_log("Tray application exiting.")

    with process_lock:
        _terminate_jarvis_process()

    icon.stop()


def monitor_process(icon):
    global jarvis_process, desired_running, restart_history

    while not shutting_down:
        time.sleep(2)

        with process_lock:
            process = jarvis_process

        if process is None:
            continue

        return_code = process.poll()
        if return_code is None:
            continue

        with process_lock:
            if process is jarvis_process:
                write_launcher_log(
                    f"Jarvis exited unexpectedly with code {return_code}."
                )
                jarvis_process = None
                _close_log_handle()

        if not desired_running or shutting_down:
            continue

        now = time.time()
        restart_history = [
            stamp for stamp in restart_history
            if now - stamp <= RESTART_WINDOW_SECONDS
        ]

        if len(restart_history) >= MAX_AUTOMATIC_RESTARTS:
            desired_running = False
            write_launcher_log("Automatic restart disabled after repeated crashes.")
            try:
                icon.notify(
                    "Jarvis crashed repeatedly and automatic recovery was stopped. Open the log, then use Restart Jarvis.",
                    "JARVIS",
                )
            except Exception:
                pass
            continue

        restart_history.append(now)
        delay = min(2 * len(restart_history), 12)
        write_launcher_log(f"Automatic recovery scheduled in {delay} seconds.")
        time.sleep(delay)

        if desired_running and not shutting_down:
            start_jarvis(icon, automatic=True)
            try:
                icon.notify("Jarvis recovered from an unexpected exit.", "JARVIS")
            except Exception:
                pass


def main():
    write_launcher_log(
        "Tray application started "
        + ("(packaged)." if IS_FROZEN else "(source mode).")
    )

    _ensure_env_file()

    menu = pystray.Menu(
        pystray.MenuItem(status_text, lambda: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Start Jarvis", start_jarvis),
        pystray.MenuItem("Stop Jarvis", stop_jarvis),
        pystray.MenuItem("Restart Jarvis", restart_jarvis),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open Configuration", open_configuration),
        pystray.MenuItem("Open Log", open_log),
        pystray.MenuItem("Open Jarvis Folder", open_project_folder),
        pystray.MenuItem("Open Data Folder", open_data_folder),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Start with Windows", install_startup),
        pystray.MenuItem("Remove Windows Startup", remove_startup),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit Jarvis", exit_tray),
    )

    icon = pystray.Icon(
        "jarvis",
        create_icon_image(),
        "JARVIS",
        menu,
    )

    start_jarvis(icon)

    watcher = threading.Thread(
        target=monitor_process,
        args=(icon,),
        daemon=True,
        name="JarvisTrayWatchdog",
    )
    watcher.start()

    icon.run()


if __name__ == "__main__":
    main()
