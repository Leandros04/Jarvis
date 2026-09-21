import ctypes
import getpass
import os
import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path

import psutil
from send2trash import send2trash


CREATE_NO_WINDOW = getattr(
    subprocess,
    "CREATE_NO_WINDOW",
    0
)


# ============================================================
# PATH HELPERS
# ============================================================

def _resolve_path(path):
    expanded = os.path.expandvars(
        os.path.expanduser(
            str(path).strip()
        )
    )

    return Path(
        expanded
    ).resolve(
        strict=False
    )


def _protected_roots():
    roots = []

    for env_name in (
        "WINDIR",
        "ProgramFiles",
        "ProgramFiles(x86)",
    ):

        value = os.environ.get(
            env_name
        )

        if value:

            roots.append(
                Path(
                    value
                ).resolve(
                    strict=False
                )
            )

    return roots


def _is_protected_path(path):
    target = _resolve_path(
        path
    )

    target_text = str(
        target
    ).lower()

    for root in _protected_roots():

        root_text = (
            str(root)
            .lower()
            .rstrip("\\/")
        )

        if (
            target_text == root_text
            or target_text.startswith(
                root_text + "\\"
            )
        ):
            return True

    return False


def _reject_protected(path):
    if _is_protected_path(
        path
    ):

        return {
            "success": False,
            "error": (
                "Direct file modification inside "
                "Windows or Program Files is blocked. "
                "Use the confirmed PowerShell tool "
                "for deliberate system-level changes."
            ),
        }

    return None


# ============================================================
# FILE MANAGEMENT
# ============================================================

def get_path_info(path):
    try:
        target = _resolve_path(
            path
        )

        if not target.exists():

            return {
                "success": False,
                "error": (
                    f"Path does not exist: "
                    f"{target}"
                ),
            }

        stat = target.stat()

        return {
            "success": True,
            "path": str(target),
            "name": target.name,
            "type": (
                "directory"
                if target.is_dir()
                else "file"
            ),
            "size_bytes": (
                stat.st_size
            ),
            "modified": (
                time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(
                        stat.st_mtime
                    ),
                )
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


def create_folder(path):
    try:
        blocked = _reject_protected(
            path
        )

        if blocked:
            return blocked

        target = _resolve_path(
            path
        )

        target.mkdir(
            parents=True,
            exist_ok=False
        )

        return {
            "success": True,
            "path": str(target),
        }

    except FileExistsError:

        return {
            "success": False,
            "error": (
                "A file or folder already "
                "exists at that path."
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


def create_text_file(
    path,
    content
):
    try:
        blocked = _reject_protected(
            path
        )

        if blocked:
            return blocked

        target = _resolve_path(
            path
        )

        if target.exists():

            return {
                "success": False,
                "error": (
                    "The destination already exists. "
                    "Jarvis will not overwrite it silently."
                ),
            }

        target.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        target.write_text(
            str(content),
            encoding="utf-8"
        )

        return {
            "success": True,
            "path": str(target),
            "characters": len(
                str(content)
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


def copy_path(
    source,
    destination
):
    try:
        src = _resolve_path(
            source
        )

        dst = _resolve_path(
            destination
        )

        blocked = _reject_protected(
            destination
        )

        if blocked:
            return blocked

        if not src.exists():

            return {
                "success": False,
                "error": (
                    f"Source does not exist: "
                    f"{src}"
                ),
            }

        if dst.exists():

            return {
                "success": False,
                "error": (
                    "Destination already exists; "
                    "refusing to overwrite."
                ),
            }

        dst.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if src.is_dir():

            shutil.copytree(
                src,
                dst
            )

        else:

            shutil.copy2(
                src,
                dst
            )

        return {
            "success": True,
            "source": str(src),
            "destination": str(dst),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


def move_path(
    source,
    destination
):
    try:
        src = _resolve_path(
            source
        )

        dst = _resolve_path(
            destination
        )

        blocked_source = (
            _reject_protected(
                source
            )
        )

        blocked_destination = (
            _reject_protected(
                destination
            )
        )

        if blocked_source:
            return blocked_source

        if blocked_destination:
            return blocked_destination

        if not src.exists():

            return {
                "success": False,
                "error": (
                    f"Source does not exist: "
                    f"{src}"
                ),
            }

        if dst.exists():

            return {
                "success": False,
                "error": (
                    "Destination already exists; "
                    "refusing to overwrite."
                ),
            }

        dst.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        result = shutil.move(
            str(src),
            str(dst)
        )

        return {
            "success": True,
            "source": str(src),
            "destination": str(
                result
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


def rename_path(
    path,
    new_name
):
    try:
        target = _resolve_path(
            path
        )

        blocked = _reject_protected(
            target
        )

        if blocked:
            return blocked

        if not target.exists():

            return {
                "success": False,
                "error": (
                    f"Path does not exist: "
                    f"{target}"
                ),
            }

        new_name = str(
            new_name
        ).strip()

        if (
            not new_name
            or any(
                character in new_name
                for character
                in '<>:"/\\|?*'
            )
        ):

            return {
                "success": False,
                "error": (
                    "Invalid Windows "
                    "file/folder name."
                ),
            }

        destination = (
            target.with_name(
                new_name
            )
        )

        if destination.exists():

            return {
                "success": False,
                "error": (
                    "A path with the new name "
                    "already exists."
                ),
            }

        target.rename(
            destination
        )

        return {
            "success": True,
            "old_path": str(target),
            "new_path": str(
                destination
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


def recycle_path(path):
    try:
        target = _resolve_path(
            path
        )

        blocked = _reject_protected(
            target
        )

        if blocked:
            return blocked

        if not target.exists():

            return {
                "success": False,
                "error": (
                    f"Path does not exist: "
                    f"{target}"
                ),
            }

        send2trash(
            str(target)
        )

        return {
            "success": True,
            "recycled": str(
                target
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# PROCESS MANAGEMENT
# ============================================================

def list_processes(
    search_term=None,
    limit=50
):
    try:
        limit = max(
            1,
            min(
                int(limit),
                200
            )
        )

        needle = (
            str(search_term)
            .strip()
            .lower()
            if search_term
            else None
        )

        rows = []

        for proc in psutil.process_iter(
            [
                "pid",
                "name",
                "username",
                "memory_info",
                "cpu_percent",
            ]
        ):

            try:
                name = (
                    proc.info.get(
                        "name"
                    )
                    or ""
                )

                if (
                    needle
                    and needle
                    not in name.lower()
                    and needle
                    not in str(
                        proc.info.get(
                            "pid"
                        )
                    )
                ):
                    continue

                memory_info = (
                    proc.info.get(
                        "memory_info"
                    )
                )

                rss = (
                    memory_info.rss
                    if memory_info
                    else 0
                )

                rows.append({
                    "pid": (
                        proc.info.get(
                            "pid"
                        )
                    ),
                    "name": name,
                    "username": (
                        proc.info.get(
                            "username"
                        )
                    ),
                    "ram_mb": round(
                        rss
                        / (1024 * 1024),
                        1
                    ),
                    "cpu_percent": (
                        proc.info.get(
                            "cpu_percent"
                        )
                        or 0.0
                    ),
                })

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied
            ):
                continue

        rows.sort(
            key=lambda x: x[
                "ram_mb"
            ],
            reverse=True
        )

        return {
            "success": True,
            "count": min(
                len(rows),
                limit
            ),
            "processes": (
                rows[:limit]
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


def get_process_info(pid):
    try:
        proc = psutil.Process(
            int(pid)
        )

        with proc.oneshot():

            return {
                "success": True,
                "pid": proc.pid,
                "name": proc.name(),
                "status": proc.status(),
                "username": (
                    proc.username()
                ),
                "exe": (
                    proc.exe()
                    if proc.exe()
                    else None
                ),
                "memory_mb": round(
                    proc.memory_info().rss
                    / (1024 * 1024),
                    1
                ),
                "create_time": (
                    time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(
                            proc.create_time()
                        ),
                    )
                ),
            }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


def terminate_process(
    pid,
    force=False
):
    try:
        pid = int(
            pid
        )

        if (
            pid in (
                0,
                4
            )
            or pid
            == os.getpid()
        ):

            return {
                "success": False,
                "error": (
                    "Refusing to terminate "
                    "this protected process."
                ),
            }

        proc = psutil.Process(
            pid
        )

        name = proc.name()

        if force:

            proc.kill()

            action = "killed"

        else:

            proc.terminate()

            try:
                proc.wait(
                    timeout=5
                )

            except psutil.TimeoutExpired:

                return {
                    "success": False,
                    "error": (
                        "Process did not exit "
                        "within 5 seconds. "
                        "Force termination may "
                        "be required."
                    ),
                }

            action = "terminated"

        return {
            "success": True,
            "pid": pid,
            "name": name,
            "action": action,
        }

    except psutil.NoSuchProcess:

        return {
            "success": False,
            "error": (
                "Process no longer exists."
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# MACHINE / NETWORK
# ============================================================

def get_machine_info():
    try:
        return {
            "success": True,
            "hostname": (
                socket.gethostname()
            ),
            "username": (
                getpass.getuser()
            ),
            "platform": (
                platform.platform()
            ),
            "processor": (
                platform.processor()
            ),
            "python": (
                platform.python_version()
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


def get_network_info():
    try:
        interfaces = []

        stats = (
            psutil.net_if_stats()
        )

        for (
            name,
            addresses
        ) in psutil.net_if_addrs().items():

            item = {
                "name": name,
                "is_up": (
                    bool(
                        stats[
                            name
                        ].isup
                    )
                    if name in stats
                    else None
                ),
                "speed_mbps": (
                    stats[
                        name
                    ].speed
                    if name in stats
                    else None
                ),
                "addresses": [],
            }

            for address in addresses:

                item[
                    "addresses"
                ].append({
                    "family": str(
                        address.family
                    ),
                    "address": (
                        address.address
                    ),
                    "netmask": (
                        address.netmask
                    ),
                })

            interfaces.append(
                item
            )

        return {
            "success": True,
            "hostname": (
                socket.gethostname()
            ),
            "interfaces": interfaces,
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


def get_wifi_info():
    try:
        result = subprocess.run(
            [
                "netsh",
                "wlan",
                "show",
                "interfaces",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=(
                CREATE_NO_WINDOW
            ),
        )

        output = (
            result.stdout
            or result.stderr
            or ""
        ).strip()

        return {
            "success": (
                result.returncode
                == 0
            ),
            "output": (
                output[:20000]
            ),
            "return_code": (
                result.returncode
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


def get_active_connections(
    limit=100
):
    try:
        limit = max(
            1,
            min(
                int(limit),
                300
            )
        )

        rows = []

        for connection in (
            psutil.net_connections(
                kind="inet"
            )
        ):

            if not connection.raddr:
                continue

            rows.append({
                "local": (
                    f"{connection.laddr.ip}:"
                    f"{connection.laddr.port}"
                    if connection.laddr
                    else None
                ),
                "remote": (
                    f"{connection.raddr.ip}:"
                    f"{connection.raddr.port}"
                    if connection.raddr
                    else None
                ),
                "status": (
                    connection.status
                ),
                "pid": (
                    connection.pid
                ),
            })

            if len(rows) >= limit:
                break

        return {
            "success": True,
            "count": len(rows),
            "connections": rows,
        }

    except psutil.AccessDenied:

        return {
            "success": False,
            "error": (
                "Access denied while reading "
                "network connections."
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# POWERSHELL
# Confirmation is handled in jarvis.py
# ============================================================

def run_powershell(
    command,
    timeout=30
):
    try:
        command = str(
            command
        ).strip()

        timeout = max(
            1,
            min(
                int(timeout),
                120
            )
        )

        if not command:

            return {
                "success": False,
                "error": (
                    "PowerShell command "
                    "is empty."
                ),
            }

        result = subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=(
                CREATE_NO_WINDOW
            ),
        )

        stdout = (
            result.stdout
            or ""
        ).strip()

        stderr = (
            result.stderr
            or ""
        ).strip()

        return {
            "success": (
                result.returncode
                == 0
            ),
            "return_code": (
                result.returncode
            ),
            "stdout": (
                stdout[:30000]
            ),
            "stderr": (
                stderr[:30000]
            ),
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "error": (
                "PowerShell command "
                "timed out."
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# POWER / SESSION ACTIONS
# Confirmation is handled in jarvis.py
# ============================================================

def power_action(action):
    try:
        action = (
            str(action)
            .strip()
            .lower()
        )

        if action == "lock":

            success = bool(
                ctypes.windll
                .user32
                .LockWorkStation()
            )

            return {
                "success": success,
                "action": "lock",
            }

        if action == "shutdown":

            subprocess.Popen(
                [
                    "shutdown",
                    "/s",
                    "/t",
                    "0",
                ],
                creationflags=(
                    CREATE_NO_WINDOW
                ),
            )

            return {
                "success": True,
                "action": "shutdown",
            }

        if action == "restart":

            subprocess.Popen(
                [
                    "shutdown",
                    "/r",
                    "/t",
                    "0",
                ],
                creationflags=(
                    CREATE_NO_WINDOW
                ),
            )

            return {
                "success": True,
                "action": "restart",
            }

        if action == "signout":

            subprocess.Popen(
                [
                    "shutdown",
                    "/l",
                ],
                creationflags=(
                    CREATE_NO_WINDOW
                ),
            )

            return {
                "success": True,
                "action": "signout",
            }

        if action == "sleep":

            result = subprocess.run(
                [
                    "rundll32.exe",
                    "powrprof.dll,SetSuspendState",
                    "0,1,0",
                ],
                capture_output=True,
                text=True,
                creationflags=(
                    CREATE_NO_WINDOW
                ),
            )

            return {
                "success": (
                    result.returncode
                    == 0
                ),
                "action": "sleep",
                "return_code": (
                    result.returncode
                ),
                "stderr": (
                    result.stderr
                    or ""
                ).strip(),
            }

        return {
            "success": False,
            "error": (
                "Unsupported action. "
                "Use lock, shutdown, restart, "
                "signout, or sleep."
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }