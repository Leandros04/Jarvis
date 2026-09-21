import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import pystray
from PIL import Image, ImageDraw


# ============================================================
# PATHS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent

JARVIS_SCRIPT = PROJECT_DIR / "jarvis.py"

LOG_DIR = PROJECT_DIR / "logs"
LOG_FILE = LOG_DIR / "jarvis.log"

STARTUP_DIR = (
    Path(os.environ["APPDATA"])
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs"
    / "Startup"
)

STARTUP_FILE = STARTUP_DIR / "JarvisAssistant.vbs"


# ============================================================
# PYTHON EXECUTABLE
# ============================================================

CURRENT_PYTHON = Path(sys.executable)

PYTHONW = CURRENT_PYTHON.with_name(
    "pythonw.exe"
)

if not PYTHONW.exists():
    PYTHONW = CURRENT_PYTHON


# ============================================================
# PROCESS STATE
# ============================================================

jarvis_process = None
process_lock = threading.Lock()


# ============================================================
# LOGGING
# ============================================================

def write_launcher_log(text):
    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    with open(
        LOG_FILE,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            f"[{timestamp}] "
            f"[TRAY] {text}\n"
        )


# ============================================================
# JARVIS PROCESS MANAGEMENT
# ============================================================

def jarvis_is_running():
    global jarvis_process

    return (
        jarvis_process is not None
        and jarvis_process.poll() is None
    )


def start_jarvis(icon=None, item=None):
    global jarvis_process

    with process_lock:

        if jarvis_is_running():

            write_launcher_log(
                "Start requested, but Jarvis "
                "is already running."
            )

            if icon:
                try:
                    icon.notify(
                        "Jarvis is already running.",
                        "JARVIS"
                    )
                except Exception:
                    pass

            return

        if not JARVIS_SCRIPT.exists():

            write_launcher_log(
                f"jarvis.py not found: "
                f"{JARVIS_SCRIPT}"
            )

            return

        LOG_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        log_handle = open(
            LOG_FILE,
            "a",
            encoding="utf-8",
            buffering=1,
        )

        separator = (
            "\n\n"
            "========================================\n"
            f"JARVIS START: {datetime.now()}\n"
            "========================================\n"
        )

        log_handle.write(
            separator
        )

        creation_flags = 0

        if os.name == "nt":
            creation_flags = (
                subprocess.CREATE_NO_WINDOW
            )

        try:

            jarvis_process = subprocess.Popen(
                [
                    str(PYTHONW),
                    "-u",
                    str(JARVIS_SCRIPT),
                ],
                cwd=str(PROJECT_DIR),

                # Keep stdin open. Jarvis normally
                # stays in wake mode and does not use it.
                stdin=subprocess.PIPE,

                stdout=log_handle,
                stderr=subprocess.STDOUT,

                text=True,
                creationflags=creation_flags,
            )

            write_launcher_log(
                f"Jarvis started. "
                f"PID={jarvis_process.pid}"
            )

            if icon:
                try:
                    icon.notify(
                        "Jarvis is now listening.",
                        "JARVIS"
                    )
                except Exception:
                    pass

        except Exception as e:

            write_launcher_log(
                f"Failed to start Jarvis: {e}"
            )

            try:
                log_handle.close()
            except Exception:
                pass


def stop_jarvis(icon=None, item=None):
    global jarvis_process

    with process_lock:

        if not jarvis_is_running():

            jarvis_process = None

            write_launcher_log(
                "Stop requested, but Jarvis "
                "was not running."
            )

            return

        pid = jarvis_process.pid

        write_launcher_log(
            f"Stopping Jarvis PID={pid}"
        )

        try:

            if os.name == "nt":

                subprocess.run(
                    [
                        "taskkill",
                        "/PID",
                        str(pid),
                        "/T",
                        "/F",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                    ),
                )

            else:

                jarvis_process.terminate()

                try:
                    jarvis_process.wait(
                        timeout=5
                    )

                except subprocess.TimeoutExpired:
                    jarvis_process.kill()

        except Exception as e:

            write_launcher_log(
                f"Error while stopping: {e}"
            )

        jarvis_process = None

        write_launcher_log(
            "Jarvis stopped."
        )

        if icon:
            try:
                icon.notify(
                    "Jarvis stopped.",
                    "JARVIS"
                )
            except Exception:
                pass


def restart_jarvis(
    icon=None,
    item=None
):
    stop_jarvis()

    time.sleep(
        0.8
    )

    start_jarvis(
        icon
    )


# ============================================================
# FILE / FOLDER ACTIONS
# ============================================================

def open_log(
    icon=None,
    item=None
):
    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not LOG_FILE.exists():

        LOG_FILE.write_text(
            "Jarvis log\n",
            encoding="utf-8"
        )

    os.startfile(
        str(LOG_FILE)
    )


def open_project_folder(
    icon=None,
    item=None
):
    os.startfile(
        str(PROJECT_DIR)
    )


# ============================================================
# WINDOWS STARTUP
# ============================================================

def install_startup(
    icon=None,
    item=None
):
    try:

        STARTUP_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        # VBS lets Windows start the tray app
        # invisibly, without a console window.
        pythonw = str(
            PYTHONW
        ).replace(
            '"',
            '""'
        )

        tray_script = str(
            Path(__file__).resolve()
        ).replace(
            '"',
            '""'
        )

        content = (
            'Set shell = '
            'CreateObject("WScript.Shell")\n'
            'shell.Run '
            '"""'
            + pythonw
            + '"" ""'
            + tray_script
            + '""", 0, False\n'
        )

        STARTUP_FILE.write_text(
            content,
            encoding="utf-8"
        )

        write_launcher_log(
            "Windows startup installed."
        )

        if icon:
            try:
                icon.notify(
                    "Jarvis will now start "
                    "automatically with Windows.",
                    "JARVIS"
                )
            except Exception:
                pass

    except Exception as e:

        write_launcher_log(
            f"Startup installation failed: {e}"
        )


def remove_startup(
    icon=None,
    item=None
):
    try:

        if STARTUP_FILE.exists():
            STARTUP_FILE.unlink()

        write_launcher_log(
            "Windows startup removed."
        )

        if icon:
            try:
                icon.notify(
                    "Automatic Windows startup removed.",
                    "JARVIS"
                )
            except Exception:
                pass

    except Exception as e:

        write_launcher_log(
            f"Could not remove startup: {e}"
        )


# ============================================================
# TRAY ICON
# ============================================================

def create_icon_image():

    size = 64

    image = Image.new(
        "RGB",
        (
            size,
            size
        ),
        "black"
    )

    draw = ImageDraw.Draw(
        image
    )

    # Minimal J icon
    draw.ellipse(
        (
            4,
            4,
            60,
            60
        ),
        outline="white",
        width=3,
    )

    draw.line(
        (
            38,
            17,
            38,
            41
        ),
        fill="white",
        width=6,
    )

    draw.arc(
        (
            18,
            27,
            40,
            50
        ),
        start=0,
        end=180,
        fill="white",
        width=6,
    )

    return image


# ============================================================
# MENU STATUS
# ============================================================

def status_text(item=None):

    if jarvis_is_running():
        return "Status: Running"

    return "Status: Stopped"


# ============================================================
# EXIT
# ============================================================

def exit_tray(
    icon,
    item=None
):
    write_launcher_log(
        "Tray application exiting."
    )

    stop_jarvis()

    icon.stop()


# ============================================================
# HEALTH WATCHER
# ============================================================

def monitor_process(icon):

    global jarvis_process

    while True:

        time.sleep(
            3
        )

        try:

            if jarvis_process is None:
                continue

            return_code = (
                jarvis_process.poll()
            )

            if return_code is None:
                continue

            write_launcher_log(
                f"Jarvis exited unexpectedly "
                f"with code {return_code}."
            )

            jarvis_process = None

            try:
                icon.notify(
                    "Jarvis stopped unexpectedly. "
                    "Use Restart Jarvis from the tray.",
                    "JARVIS"
                )
            except Exception:
                pass

        except Exception as e:

            write_launcher_log(
                f"Monitor error: {e}"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    write_launcher_log(
        "Tray application started."
    )

    image = create_icon_image()

    menu = pystray.Menu(

        pystray.MenuItem(
            status_text,
            lambda: None,
            enabled=False,
        ),

        pystray.Menu.SEPARATOR,

        pystray.MenuItem(
            "Start Jarvis",
            start_jarvis,
        ),

        pystray.MenuItem(
            "Stop Jarvis",
            stop_jarvis,
        ),

        pystray.MenuItem(
            "Restart Jarvis",
            restart_jarvis,
        ),

        pystray.Menu.SEPARATOR,

        pystray.MenuItem(
            "Open Log",
            open_log,
        ),

        pystray.MenuItem(
            "Open Jarvis Folder",
            open_project_folder,
        ),

        pystray.Menu.SEPARATOR,

        pystray.MenuItem(
            "Start with Windows",
            install_startup,
        ),

        pystray.MenuItem(
            "Remove Windows Startup",
            remove_startup,
        ),

        pystray.Menu.SEPARATOR,

        pystray.MenuItem(
            "Exit Jarvis",
            exit_tray,
        ),
    )

    icon = pystray.Icon(
        "jarvis",
        image,
        "JARVIS",
        menu,
    )

    # Start Jarvis automatically whenever
    # the tray application itself starts.
    start_jarvis(
        icon
    )

    monitor_thread = threading.Thread(
        target=monitor_process,
        args=(
            icon,
        ),
        daemon=True,
    )

    monitor_thread.start()

    icon.run()


if __name__ == "__main__":
    main()