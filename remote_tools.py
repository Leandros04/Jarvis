import os
import shlex
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path

DB_PATH = Path.home() / "Jarvis" / "data" / "nodes.db"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DEFAULT_IDENTITY = Path.home() / ".ssh" / "jarvis_ed25519"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_remote_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                host TEXT NOT NULL,
                username TEXT NOT NULL,
                port INTEGER NOT NULL DEFAULT 22,
                identity_file TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        existing = conn.execute(
            "SELECT id FROM nodes WHERE lower(name)=lower(?)",
            ("leandros-pi",),
        ).fetchone()
        if not existing:
            now = time.time()
            conn.execute(
                """
                INSERT INTO nodes
                (name, host, username, port, identity_file, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    "leandros-pi",
                    "leandros-pi",
                    "lendis",
                    22,
                    str(DEFAULT_IDENTITY),
                    now,
                    now,
                ),
            )
    return {"success": True, "database": str(DB_PATH)}


def node_add(name, host, username, port=22, identity_file=None):
    try:
        name = str(name).strip()
        host = str(host).strip()
        username = str(username).strip()
        port = int(port)
        if not name or not host or not username:
            return {"success": False, "error": "name, host and username are required."}
        if not 1 <= port <= 65535:
            return {"success": False, "error": "Invalid SSH port."}
        if identity_file:
            identity_file = str(Path(os.path.expandvars(os.path.expanduser(str(identity_file)))).resolve(strict=False))
        now = time.time()
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO nodes
                (name, host, username, port, identity_file, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    host=excluded.host,
                    username=excluded.username,
                    port=excluded.port,
                    identity_file=excluded.identity_file,
                    enabled=1,
                    updated_at=excluded.updated_at
                """,
                (name, host, username, port, identity_file, now, now),
            )
        return {"success": True, "node": node_get(name)["node"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def node_get(name):
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT * FROM nodes WHERE lower(name)=lower(?)",
                (str(name).strip(),),
            ).fetchone()
        if not row:
            return {"success": False, "error": f"Unknown node: {name}"}
        node = dict(row)
        node["enabled"] = bool(node["enabled"])
        return {"success": True, "node": node}
    except Exception as e:
        return {"success": False, "error": str(e)}


def node_list():
    try:
        with _connect() as conn:
            rows = conn.execute("SELECT * FROM nodes ORDER BY name COLLATE NOCASE").fetchall()
        nodes = []
        for row in rows:
            item = dict(row)
            item["enabled"] = bool(item["enabled"])
            nodes.append(item)
        return {"success": True, "count": len(nodes), "nodes": nodes}
    except Exception as e:
        return {"success": False, "error": str(e)}


def node_remove(name):
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT name FROM nodes WHERE lower(name)=lower(?)",
                (str(name).strip(),),
            ).fetchone()
            if not row:
                return {"success": False, "error": f"Unknown node: {name}"}
            conn.execute(
                "DELETE FROM nodes WHERE lower(name)=lower(?)",
                (str(name).strip(),),
            )
        return {"success": True, "removed": row["name"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _node(name):
    result = node_get(name)
    if not result.get("success"):
        return None, result
    node = result["node"]
    if not node.get("enabled"):
        return None, {"success": False, "error": f"Node {name} is disabled."}
    identity = node.get("identity_file")
    if identity and not Path(identity).exists():
        return None, {
            "success": False,
            "error": f"SSH identity file not found: {identity}",
            "password_fallback": "Manual SSH can still fall back to the node password.",
        }
    return node, None


def _ssh_base(node):
    ssh = shutil.which("ssh")
    if not ssh:
        raise RuntimeError("Windows OpenSSH client (ssh.exe) was not found.")
    args = [
        ssh,
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=8",
        "-o", "ServerAliveInterval=10",
        "-o", "ServerAliveCountMax=2",
        "-p", str(node["port"]),
    ]
    if node.get("identity_file"):
        args.extend([
            "-o", "IdentitiesOnly=yes",
            "-i", node["identity_file"],
        ])
    args.append(f"{node['username']}@{node['host']}")
    return args


def _scp_base(node):
    scp = shutil.which("scp")
    if not scp:
        raise RuntimeError("Windows OpenSSH client (scp.exe) was not found.")
    args = [
        scp,
        "-B",
        "-o", "ConnectTimeout=8",
        "-P", str(node["port"]),
    ]
    if node.get("identity_file"):
        args.extend([
            "-o", "IdentitiesOnly=yes",
            "-i", node["identity_file"],
        ])
    return args


def _run_ssh(node, command, timeout=30):
    result = subprocess.run(
        _ssh_base(node) + [command],
        capture_output=True,
        text=True,
        timeout=max(1, min(int(timeout), 300)),
        creationflags=CREATE_NO_WINDOW,
    )
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    return {
        "success": result.returncode == 0,
        "return_code": result.returncode,
        "stdout": stdout[:50000],
        "stderr": stderr[:30000],
        "password_fallback": (
            "If key authentication fails, manual `ssh leandros-pi` can still use the password. "
            "Background Jarvis does not store or auto-type the password."
        ),
    }


def _shell_path(path):
    p = str(path).strip()
    if p == "~":
        return '"$HOME"'
    if p.startswith("~/"):
        return '"$HOME"/' + shlex.quote(p[2:])
    return shlex.quote(p)


def node_status(name):
    try:
        node, error = _node(name)
        if error:
            return error
        command = (
            "printf 'HOSTNAME='; hostname; "
            "printf 'USER='; whoami; "
            "printf 'UPTIME='; (uptime -p 2>/dev/null || uptime); "
            "printf 'KERNEL='; uname -sr; "
            "printf 'MEMORY='; (free -h 2>/dev/null | awk 'NR==2{print $3\"/\"$2}' || true); "
            "printf 'ROOT_DISK='; (df -h / 2>/dev/null | awk 'NR==2{print $3\"/\"$2\" used=\"$5}' || true); "
            "if command -v vcgencmd >/dev/null 2>&1; then printf 'TEMP='; vcgencmd measure_temp; fi"
        )
        result = _run_ssh(node, command, timeout=15)
        result["node"] = name
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def remote_run(name, command, timeout=30):
    try:
        node, error = _node(name)
        if error:
            return error
        command = str(command).strip()
        if not command:
            return {"success": False, "error": "Remote command is empty."}
        result = _run_ssh(node, command, timeout=timeout)
        result["node"] = name
        return result
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Remote command timed out."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def remote_list_directory(name, path="~"):
    try:
        node, error = _node(name)
        if error:
            return error
        command = f"ls -la -- {_shell_path(path)}"
        result = _run_ssh(node, command, timeout=20)
        result.update({"node": name, "path": str(path)})
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def remote_read_file(name, path, max_chars=30000):
    try:
        node, error = _node(name)
        if error:
            return error
        max_chars = max(100, min(int(max_chars), 100000))
        command = f"head -c {max_chars} -- {_shell_path(path)}"
        result = _run_ssh(node, command, timeout=20)
        result.update({"node": name, "path": str(path), "max_chars": max_chars})
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def remote_upload(name, local_path, remote_path):
    try:
        node, error = _node(name)
        if error:
            return error
        local = Path(os.path.expandvars(os.path.expanduser(str(local_path)))).resolve(strict=False)
        if not local.exists():
            return {"success": False, "error": f"Local path does not exist: {local}"}

        exists_check = _run_ssh(
            node,
            f"test -e {_shell_path(remote_path)}",
            timeout=10,
        )
        if exists_check.get("success"):
            return {
                "success": False,
                "error": "Remote destination already exists; refusing to overwrite.",
                "remote_path": str(remote_path),
            }

        args = _scp_base(node)
        if local.is_dir():
            args.append("-r")
        args.extend([
            str(local),
            f"{node['username']}@{node['host']}:{remote_path}",
        ])
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=180,
            creationflags=CREATE_NO_WINDOW,
        )
        return {
            "success": result.returncode == 0,
            "node": name,
            "local_path": str(local),
            "remote_path": str(remote_path),
            "return_code": result.returncode,
            "stdout": (result.stdout or "").strip()[:20000],
            "stderr": (result.stderr or "").strip()[:20000],
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Upload timed out."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def remote_download(name, remote_path, local_path):
    try:
        node, error = _node(name)
        if error:
            return error
        local = Path(os.path.expandvars(os.path.expanduser(str(local_path)))).resolve(strict=False)
        if local.exists():
            return {"success": False, "error": "Local destination already exists; refusing to overwrite."}
        local.parent.mkdir(parents=True, exist_ok=True)

        # Detect whether the source is a directory so scp can recurse when needed.
        dir_check = _run_ssh(
            node,
            f"test -d {_shell_path(remote_path)}",
            timeout=10,
        )
        args = _scp_base(node)
        if dir_check.get("success"):
            args.append("-r")
        args.extend([
            f"{node['username']}@{node['host']}:{remote_path}",
            str(local),
        ])
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=180,
            creationflags=CREATE_NO_WINDOW,
        )
        return {
            "success": result.returncode == 0,
            "node": name,
            "remote_path": str(remote_path),
            "local_path": str(local),
            "return_code": result.returncode,
            "stdout": (result.stdout or "").strip()[:20000],
            "stderr": (result.stderr or "").strip()[:20000],
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Download timed out."}
    except Exception as e:
        return {"success": False, "error": str(e)}


init_remote_db()
