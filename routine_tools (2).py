import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / "Jarvis" / "data" / "routines.db"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_routines_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS routines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                description TEXT NOT NULL,
                steps_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
    return {"success": True, "database": str(DB_PATH)}


def _normalize_steps(steps):
    if not isinstance(steps, list) or not steps:
        raise ValueError("A routine needs at least one step.")
    if len(steps) > 30:
        raise ValueError("A routine can contain at most 30 steps.")
    normalized = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"Step {index} must be an object.")
        tool = str(step.get("tool", "")).strip()
        arguments_json = step.get("arguments_json", "{}")
        if not tool:
            raise ValueError(f"Step {index} has no tool name.")
        if not isinstance(arguments_json, str):
            arguments_json = json.dumps(arguments_json, ensure_ascii=False)
        try:
            arguments = json.loads(arguments_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Step {index} arguments_json is invalid JSON: {e}") from e
        if not isinstance(arguments, dict):
            raise ValueError(f"Step {index} arguments must decode to an object.")
        normalized.append({
            "tool": tool,
            "arguments_json": json.dumps(arguments, ensure_ascii=False),
        })
    return normalized


def routine_save(name, description, steps):
    try:
        name = str(name).strip()
        description = str(description).strip()
        if not name:
            return {"success": False, "error": "Routine name cannot be empty."}
        normalized = _normalize_steps(steps)
        now = time.time()
        with _connect() as conn:
            existing = conn.execute(
                "SELECT id, created_at FROM routines WHERE lower(name)=lower(?)",
                (name,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE routines
                    SET description=?, steps_json=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        description,
                        json.dumps(normalized, ensure_ascii=False),
                        now,
                        existing["id"],
                    ),
                )
                action = "updated"
            else:
                conn.execute(
                    """
                    INSERT INTO routines
                    (name, description, steps_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        description,
                        json.dumps(normalized, ensure_ascii=False),
                        now,
                        now,
                    ),
                )
                action = "created"
        result = routine_get(name)
        result["action"] = action
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


def routine_get(name):
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT * FROM routines WHERE lower(name)=lower(?)",
                (str(name).strip(),),
            ).fetchone()
        if not row:
            return {"success": False, "error": f"Routine not found: {name}"}
        item = dict(row)
        item["steps"] = json.loads(item.pop("steps_json"))
        return {"success": True, "routine": item}
    except Exception as e:
        return {"success": False, "error": str(e)}


def routine_list(limit=50):
    try:
        limit = max(1, min(int(limit), 200))
        with _connect() as conn:
            rows = conn.execute(
                "SELECT id, name, description, created_at, updated_at FROM routines ORDER BY name COLLATE NOCASE LIMIT ?",
                (limit,),
            ).fetchall()
        return {
            "success": True,
            "count": len(rows),
            "routines": [dict(row) for row in rows],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def routine_delete(name):
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT id, name FROM routines WHERE lower(name)=lower(?)",
                (str(name).strip(),),
            ).fetchone()
            if not row:
                return {"success": False, "error": f"Routine not found: {name}"}
            conn.execute("DELETE FROM routines WHERE id=?", (row["id"],))
        return {"success": True, "deleted": row["name"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


init_routines_db()
