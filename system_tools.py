import os
import csv
import json
import shutil
import subprocess
import winreg
from difflib import get_close_matches
from pathlib import Path

import psutil
import mss
import mss.tools
import pyautogui
from pypdf import PdfReader


# ============================================================
# AUTOMATION SAFETY
# ============================================================

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.20


# ============================================================
# SYSTEM INFORMATION
# ============================================================

def get_system_status():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage("C:\\")

    return {
        "success": True,
        "cpu_percent": cpu,
        "ram_total_gb": round(memory.total / (1024 ** 3), 2),
        "ram_used_gb": round(memory.used / (1024 ** 3), 2),
        "ram_percent": memory.percent,
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        "disk_used_gb": round(disk.used / (1024 ** 3), 2),
        "disk_free_gb": round(disk.free / (1024 ** 3), 2),
    }


def get_top_processes():
    processes = []

    for process in psutil.process_iter(
        ["pid", "name", "memory_info"]
    ):
        try:
            memory_mb = process.info["memory_info"].rss / (1024 ** 2)

            processes.append({
                "pid": process.info["pid"],
                "name": process.info["name"],
                "memory_mb": round(memory_mb, 1),
            })

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processes.sort(
        key=lambda x: x["memory_mb"],
        reverse=True
    )

    return {
        "success": True,
        "processes": processes[:10],
    }


# ============================================================
# WINDOWS PATHS
# ============================================================

def get_user_paths():
    home = Path.home()

    common_paths = {
        "home": home,
        "desktop": home / "Desktop",
        "documents": home / "Documents",
        "downloads": home / "Downloads",
        "pictures": home / "Pictures",
        "videos": home / "Videos",
        "music": home / "Music",
    }

    result = {}

    for name, path in common_paths.items():
        result[name] = {
            "path": str(path),
            "exists": path.exists(),
        }

    return {
        "success": True,
        "paths": result,
    }


# ============================================================
# SCREEN / CURSOR
# ============================================================

def get_screen_info():
    width, height = pyautogui.size()
    x, y = pyautogui.position()

    return {
        "success": True,
        "screen_width": width,
        "screen_height": height,
        "cursor_x": x,
        "cursor_y": y,
    }


def capture_screen():
    try:
        screenshot_dir = (
            Path.home()
            / "Jarvis"
            / "screenshots"
        )

        screenshot_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        output_path = (
            screenshot_dir
            / "latest_screen.png"
        )

        with mss.mss() as sct:

            # Capture the primary monitor.
            if len(sct.monitors) > 1:
                monitor = sct.monitors[1]
            else:
                monitor = sct.monitors[0]

            screenshot = sct.grab(
                monitor
            )

            mss.tools.to_png(
                screenshot.rgb,
                screenshot.size,
                output=str(output_path),
            )

        return {
            "success": True,
            "path": str(output_path),
            "width": screenshot.width,
            "height": screenshot.height,
            "left": monitor["left"],
            "top": monitor["top"],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# MOUSE CONTROL
# ============================================================

def move_mouse(x, y, duration=0.3):
    try:
        width, height = pyautogui.size()

        if not (
            0 <= x < width
            and 0 <= y < height
        ):
            return {
                "success": False,
                "error": (
                    f"Coordinates ({x}, {y}) are outside "
                    f"the screen size {width}x{height}."
                ),
            }

        duration = max(
            0.0,
            min(float(duration), 3.0)
        )

        pyautogui.moveTo(
            x,
            y,
            duration=duration
        )

        return {
            "success": True,
            "x": x,
            "y": y,
        }

    except pyautogui.FailSafeException:
        return {
            "success": False,
            "error": "PyAutoGUI fail-safe triggered."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def click_mouse(
    x=None,
    y=None,
    button="left",
    clicks=1
):
    try:
        allowed_buttons = {
            "left",
            "right",
            "middle",
        }

        if button not in allowed_buttons:
            return {
                "success": False,
                "error": "Invalid mouse button.",
            }

        clicks = max(
            1,
            min(int(clicks), 3)
        )

        if x is not None and y is not None:

            width, height = pyautogui.size()

            if not (
                0 <= x < width
                and 0 <= y < height
            ):
                return {
                    "success": False,
                    "error": (
                        f"Coordinates ({x}, {y}) "
                        "are outside the screen."
                    ),
                }

            pyautogui.click(
                x=x,
                y=y,
                button=button,
                clicks=clicks,
                interval=0.12,
            )

        else:
            pyautogui.click(
                button=button,
                clicks=clicks,
                interval=0.12,
            )

        current_x, current_y = (
            pyautogui.position()
        )

        return {
            "success": True,
            "button": button,
            "clicks": clicks,
            "cursor_x": current_x,
            "cursor_y": current_y,
        }

    except pyautogui.FailSafeException:
        return {
            "success": False,
            "error": "PyAutoGUI fail-safe triggered."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def scroll_mouse(amount):
    try:
        amount = int(amount)

        amount = max(
            -20,
            min(amount, 20)
        )

        pyautogui.scroll(
            amount
        )

        return {
            "success": True,
            "amount": amount,
        }

    except pyautogui.FailSafeException:
        return {
            "success": False,
            "error": "PyAutoGUI fail-safe triggered."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# KEYBOARD CONTROL
# ============================================================

def type_text(text, interval=0.02):
    try:
        interval = max(
            0.0,
            min(float(interval), 0.5)
        )

        pyautogui.write(
            text,
            interval=interval
        )

        return {
            "success": True,
            "characters_typed": len(text),
        }

    except pyautogui.FailSafeException:
        return {
            "success": False,
            "error": "PyAutoGUI fail-safe triggered."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def press_key(key, presses=1):
    try:
        key = key.lower().strip()

        if key not in pyautogui.KEYBOARD_KEYS:
            return {
                "success": False,
                "error": f"Unsupported key: {key}",
            }

        presses = max(
            1,
            min(int(presses), 20)
        )

        pyautogui.press(
            key,
            presses=presses,
            interval=0.08,
        )

        return {
            "success": True,
            "key": key,
            "presses": presses,
        }

    except pyautogui.FailSafeException:
        return {
            "success": False,
            "error": "PyAutoGUI fail-safe triggered."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def press_hotkey(keys):
    try:
        if not isinstance(keys, list):
            return {
                "success": False,
                "error": "keys must be a list.",
            }

        cleaned = [
            str(key).lower().strip()
            for key in keys
        ]

        if not cleaned:
            return {
                "success": False,
                "error": "No keys supplied.",
            }

        for key in cleaned:
            if key not in pyautogui.KEYBOARD_KEYS:
                return {
                    "success": False,
                    "error": (
                        f"Unsupported key: {key}"
                    ),
                }

        pyautogui.hotkey(
            *cleaned
        )

        return {
            "success": True,
            "keys": cleaned,
        }

    except pyautogui.FailSafeException:
        return {
            "success": False,
            "error": "PyAutoGUI fail-safe triggered."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# APPLICATION DISCOVERY
# ============================================================

def _start_menu_locations():
    locations = []

    appdata = os.getenv("APPDATA")
    programdata = os.getenv("PROGRAMDATA")

    if appdata:
        locations.append(
            Path(appdata)
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
        )

    if programdata:
        locations.append(
            Path(programdata)
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
        )

    return locations


def _discover_start_menu_apps():
    apps = {}

    for root in _start_menu_locations():

        if not root.exists():
            continue

        try:
            for path in root.rglob("*"):

                if not path.is_file():
                    continue

                if path.suffix.lower() not in {
                    ".lnk",
                    ".url",
                    ".exe",
                }:
                    continue

                name = path.stem.strip()

                if not name:
                    continue

                apps[name.lower()] = {
                    "name": name,
                    "launch_target": str(path),
                    "source": "start_menu",
                }

        except (PermissionError, OSError):
            continue

    return apps


def _read_app_paths_registry(
    root_key,
    registry_path
):
    apps = {}

    try:
        with winreg.OpenKey(
            root_key,
            registry_path
        ) as key:

            count = winreg.QueryInfoKey(
                key
            )[0]

            for index in range(count):

                try:
                    subkey_name = (
                        winreg.EnumKey(
                            key,
                            index
                        )
                    )

                    with winreg.OpenKey(
                        key,
                        subkey_name
                    ) as subkey:

                        try:
                            executable, _ = (
                                winreg.QueryValueEx(
                                    subkey,
                                    None
                                )
                            )

                        except OSError:
                            continue

                        executable = str(
                            executable
                        ).strip('"')

                        if not executable:
                            continue

                        name = Path(
                            subkey_name
                        ).stem.strip()

                        apps[name.lower()] = {
                            "name": name,
                            "launch_target": executable,
                            "source": "registry",
                        }

                except OSError:
                    continue

    except OSError:
        pass

    return apps


def _discover_registry_apps():
    apps = {}

    paths = [
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        ),
        (
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"
        ),
    ]

    for root_key, registry_path in paths:
        apps.update(
            _read_app_paths_registry(
                root_key,
                registry_path
            )
        )

    return apps


def discover_applications():
    apps = {}

    apps.update(
        _discover_start_menu_apps()
    )

    apps.update(
        _discover_registry_apps()
    )

    builtins = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "file explorer": "explorer.exe",
        "explorer": "explorer.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
        "task manager": "taskmgr.exe",
        "control panel": "control.exe",
    }

    for name, target in builtins.items():
        apps[name] = {
            "name": name.title(),
            "launch_target": target,
            "source": "windows_builtin",
        }

    return apps


def list_applications(search_term=None):
    apps = discover_applications()
    results = list(apps.values())

    if search_term:
        term = search_term.lower()

        results = [
            app
            for app in results
            if term in app["name"].lower()
        ]

    results.sort(
        key=lambda app: app["name"].lower()
    )

    return {
        "success": True,
        "count": len(results),
        "applications": results[:200],
        "limited": len(results) > 200,
    }


def open_application(app_name):
    try:
        apps = discover_applications()

        requested = (
            app_name
            .lower()
            .strip()
        )

        if requested in apps:
            selected = apps[requested]

        else:
            partial_matches = [
                key
                for key in apps
                if requested in key
            ]

            if len(partial_matches) == 1:
                selected = apps[
                    partial_matches[0]
                ]

            elif len(partial_matches) > 1:
                best = sorted(
                    partial_matches,
                    key=len
                )[0]

                selected = apps[best]

            else:
                matches = get_close_matches(
                    requested,
                    list(apps.keys()),
                    n=5,
                    cutoff=0.5,
                )

                if not matches:
                    return {
                        "success": False,
                        "error": (
                            "Could not find an installed "
                            f"application matching '{app_name}'."
                        ),
                    }

                selected = apps[
                    matches[0]
                ]

        target = selected[
            "launch_target"
        ]

        if selected["source"] == "start_menu":
            os.startfile(target)

        else:
            subprocess.Popen(
                [target],
                shell=False
            )

        return {
            "success": True,
            "requested": app_name,
            "opened": selected["name"],
            "source": selected["source"],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# DIRECTORY / FILE SEARCH
# ============================================================

def list_directory(path):
    try:
        target = (
            Path(path)
            .expanduser()
            .resolve()
        )

        if not target.exists():
            return {
                "success": False,
                "error": "Path does not exist."
            }

        if not target.is_dir():
            return {
                "success": False,
                "error": "Path is not a directory."
            }

        items = []

        for item in target.iterdir():
            try:
                stat = item.stat()

                items.append({
                    "name": item.name,
                    "path": str(item),
                    "type": (
                        "folder"
                        if item.is_dir()
                        else "file"
                    ),
                    "size_mb": (
                        round(
                            stat.st_size
                            / (1024 ** 2),
                            2
                        )
                        if item.is_file()
                        else None
                    ),
                    "modified": stat.st_mtime,
                })

            except (
                PermissionError,
                OSError
            ):
                continue

        items.sort(
            key=lambda x: (
                x["type"] != "folder",
                x["name"].lower()
            )
        )

        return {
            "success": True,
            "path": str(target),
            "item_count": len(items),
            "items": items,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def find_files(
    search_term,
    root=None
):
    try:
        if root is None:
            root = str(
                Path.home()
            )

        root_path = (
            Path(root)
            .expanduser()
            .resolve()
        )

        if not root_path.exists():
            return {
                "success": False,
                "error": "Search location does not exist."
            }

        search_term = search_term.lower()
        results = []

        excluded_folders = {
            ".git",
            ".venv",
            "node_modules",
            "__pycache__",
            "appdata",
        }

        for current_root, dirs, files in os.walk(
            root_path
        ):

            dirs[:] = [
                d
                for d in dirs
                if d.lower()
                not in excluded_folders
            ]

            for filename in files:

                if search_term in filename.lower():

                    full_path = (
                        Path(current_root)
                        / filename
                    )

                    try:
                        stat = full_path.stat()

                        results.append({
                            "name": filename,
                            "path": str(full_path),
                            "size_mb": round(
                                stat.st_size
                                / (1024 ** 2),
                                2
                            ),
                            "modified": stat.st_mtime,
                        })

                    except (
                        PermissionError,
                        OSError
                    ):
                        continue

                if len(results) >= 50:
                    return {
                        "success": True,
                        "results": results,
                        "limited": True,
                    }

        return {
            "success": True,
            "results": results,
            "limited": False,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def open_file(path):
    try:
        target = (
            Path(path)
            .expanduser()
            .resolve()
        )

        if not target.exists():
            return {
                "success": False,
                "error": "File does not exist."
            }

        os.startfile(
            str(target)
        )

        return {
            "success": True,
            "opened": str(target),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# FILE READING
# ============================================================

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".htm",
    ".css",
    ".xml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".conf",
    ".log",
    ".sql",
    ".ps1",
    ".bat",
    ".cmd",
    ".sh",
    ".env",
}


def read_text_file(
    path,
    max_chars
):
    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin-1",
    ]

    last_error = None

    for encoding in encodings:
        try:
            with open(
                path,
                "r",
                encoding=encoding,
                errors="strict"
            ) as file:
                content = file.read(
                    max_chars + 1
                )

            truncated = (
                len(content) > max_chars
            )

            if truncated:
                content = content[:max_chars]

            return {
                "success": True,
                "content": content,
                "truncated": truncated,
                "encoding": encoding,
            }

        except UnicodeDecodeError as e:
            last_error = str(e)

    return {
        "success": False,
        "error": (
            "Could not decode text file. "
            f"Last error: {last_error}"
        )
    }


def read_json_file(
    path,
    max_chars
):
    try:
        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        content = json.dumps(
            data,
            indent=2,
            ensure_ascii=False
        )

        truncated = (
            len(content) > max_chars
        )

        if truncated:
            content = content[:max_chars]

        return {
            "success": True,
            "content": content,
            "truncated": truncated,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def read_csv_file(
    path,
    max_chars
):
    try:
        rows = []

        with open(
            path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.reader(file)

            for row_number, row in enumerate(reader):
                rows.append(row)

                if row_number >= 199:
                    break

        content = "\n".join(
            " | ".join(
                str(value)
                for value in row
            )
            for row in rows
        )

        truncated = (
            len(content) > max_chars
        )

        if truncated:
            content = content[:max_chars]

        return {
            "success": True,
            "rows_read": len(rows),
            "content": content,
            "truncated": truncated,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def read_pdf_file(
    path,
    max_chars,
    start_page=None,
    end_page=None
):
    try:
        reader = PdfReader(
            str(path)
        )

        page_count = len(
            reader.pages
        )

        if page_count == 0:
            return {
                "success": False,
                "error": "PDF contains no pages."
            }

        if start_page is None:
            start_page = 1

        if end_page is None:
            end_page = page_count

        start_page = max(
            1,
            start_page
        )

        end_page = min(
            page_count,
            end_page
        )

        extracted = []
        total_chars = 0
        pages_read = []

        for page_number in range(
            start_page - 1,
            end_page
        ):

            text = (
                reader.pages[
                    page_number
                ].extract_text()
                or ""
            )

            block = (
                f"\n\n--- PAGE "
                f"{page_number + 1} "
                f"---\n\n{text}"
            )

            remaining = (
                max_chars - total_chars
            )

            if remaining <= 0:
                break

            if len(block) > remaining:
                extracted.append(
                    block[:remaining]
                )

                pages_read.append(
                    page_number + 1
                )

                break

            extracted.append(block)

            pages_read.append(
                page_number + 1
            )

            total_chars += len(block)

        content = "".join(
            extracted
        )

        return {
            "success": True,
            "page_count": page_count,
            "pages_read": pages_read,
            "content": content,
            "text_found": bool(
                content.strip()
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def read_file(
    path,
    max_chars=None,
    start_page=None,
    end_page=None
):
    try:
        if max_chars is None:
            max_chars = 30000

        max_chars = max(
            1000,
            min(
                max_chars,
                100000
            )
        )

        target = (
            Path(path)
            .expanduser()
            .resolve()
        )

        if not target.exists():
            return {
                "success": False,
                "error": "File does not exist."
            }

        if not target.is_file():
            return {
                "success": False,
                "error": "Path is not a file."
            }

        extension = (
            target.suffix.lower()
        )

        if extension == ".pdf":
            result = read_pdf_file(
                target,
                max_chars,
                start_page,
                end_page
            )

        elif extension == ".json":
            result = read_json_file(
                target,
                max_chars
            )

        elif extension == ".csv":
            result = read_csv_file(
                target,
                max_chars
            )

        elif extension in TEXT_EXTENSIONS:
            result = read_text_file(
                target,
                max_chars
            )

        else:
            return {
                "success": False,
                "error": (
                    f"Reading {extension} "
                    "is not supported yet."
                ),
            }

        return {
            "path": str(target),
            "name": target.name,
            **result,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }