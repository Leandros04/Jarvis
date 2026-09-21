import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

from desktop_tools import show_notification


DB_PATH = (
    Path.home()
    / "Jarvis"
    / "data"
    / "scheduler.db"
)

CHECK_INTERVAL_SECONDS = 1.0


def _connect():
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_scheduler_db():
    with _connect() as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                run_at REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at REAL NOT NULL,
                completed_at REAL
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_scheduler_status_run_at
            ON scheduled_tasks(status, run_at)
            """
        )

    return {
        "success": True,
        "database": str(DB_PATH),
    }


def get_local_datetime():
    now = datetime.now().astimezone()

    return {
        "success": True,
        "iso": now.isoformat(),
        "date": now.strftime(
            "%Y-%m-%d"
        ),
        "time": now.strftime(
            "%H:%M:%S"
        ),
        "timezone": str(
            now.tzinfo
        ),
        "timestamp": now.timestamp(),
    }


def _display_time(timestamp):
    return (
        datetime
        .fromtimestamp(timestamp)
        .astimezone()
        .strftime(
            "%Y-%m-%d %H:%M:%S %Z"
        )
    )


def schedule_reminder(
    title,
    message,
    run_at_timestamp
):
    try:
        title = str(
            title
        ).strip()

        message = str(
            message
        ).strip()

        timestamp = float(
            run_at_timestamp
        )

        if not title:
            title = "JARVIS Reminder"

        if not message:
            return {
                "success": False,
                "error": (
                    "Reminder message "
                    "cannot be empty."
                ),
            }

        now = time.time()

        if timestamp <= now:
            return {
                "success": False,
                "error": (
                    "Reminder time must "
                    "be in the future."
                ),
            }

        with _connect() as conn:

            cursor = conn.execute(
                """
                INSERT INTO scheduled_tasks (
                    title,
                    message,
                    run_at,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    title,
                    message,
                    timestamp,
                    "pending",
                    now,
                ),
            )

            task_id = (
                cursor.lastrowid
            )

        return {
            "success": True,
            "task": {
                "id": task_id,
                "title": title,
                "message": message,
                "run_at_timestamp": timestamp,
                "run_at": _display_time(
                    timestamp
                ),
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def schedule_timer(
    seconds,
    message="Timer finished."
):
    try:
        seconds = float(
            seconds
        )

        if seconds <= 0:
            return {
                "success": False,
                "error": (
                    "Timer must be "
                    "greater than zero."
                ),
            }

        return schedule_reminder(
            title="JARVIS Timer",
            message=message,
            run_at_timestamp=(
                time.time()
                + seconds
            ),
        )

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def schedule_reminder_at(
    local_datetime,
    message,
    title="JARVIS Reminder"
):
    try:
        text = str(
            local_datetime
        ).strip()

        dt = datetime.fromisoformat(
            text
        )

        if dt.tzinfo is None:
            dt = dt.astimezone()

        return schedule_reminder(
            title=title,
            message=message,
            run_at_timestamp=(
                dt.timestamp()
            ),
        )

    except Exception as e:
        return {
            "success": False,
            "error": (
                "Could not understand "
                f"datetime '{local_datetime}': "
                f"{e}"
            ),
        }


def list_scheduled_tasks(
    include_completed=False,
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

        with _connect() as conn:

            if include_completed:

                rows = conn.execute(
                    """
                    SELECT *
                    FROM scheduled_tasks
                    ORDER BY run_at ASC
                    LIMIT ?
                    """,
                    (
                        limit,
                    ),
                ).fetchall()

            else:

                rows = conn.execute(
                    """
                    SELECT *
                    FROM scheduled_tasks
                    WHERE status = 'pending'
                    ORDER BY run_at ASC
                    LIMIT ?
                    """,
                    (
                        limit,
                    ),
                ).fetchall()

        tasks = []

        for row in rows:

            task = dict(row)

            task[
                "run_at_local"
            ] = _display_time(
                task["run_at"]
            )

            tasks.append(
                task
            )

        return {
            "success": True,
            "count": len(tasks),
            "tasks": tasks,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def cancel_scheduled_task(
    task_id
):
    try:
        task_id = int(
            task_id
        )

        with _connect() as conn:

            row = conn.execute(
                """
                SELECT *
                FROM scheduled_tasks
                WHERE id = ?
                """,
                (
                    task_id,
                ),
            ).fetchone()

            if not row:

                return {
                    "success": False,
                    "error": (
                        f"Task {task_id} "
                        "does not exist."
                    ),
                }

            if (
                row["status"]
                != "pending"
            ):

                return {
                    "success": False,
                    "error": (
                        f"Task is already "
                        f"{row['status']}."
                    ),
                }

            conn.execute(
                """
                UPDATE scheduled_tasks
                SET status = 'cancelled'
                WHERE id = ?
                """,
                (
                    task_id,
                ),
            )

        return {
            "success": True,
            "cancelled_task_id": (
                task_id
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def _get_due_tasks():

    with _connect() as conn:

        rows = conn.execute(
            """
            SELECT *
            FROM scheduled_tasks
            WHERE status = 'pending'
            AND run_at <= ?
            ORDER BY run_at ASC
            """,
            (
                time.time(),
            ),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def _mark_completed(
    task_id
):

    with _connect() as conn:

        conn.execute(
            """
            UPDATE scheduled_tasks
            SET
                status = 'completed',
                completed_at = ?
            WHERE id = ?
            """,
            (
                time.time(),
                task_id,
            ),
        )


class JarvisScheduler:

    def __init__(
        self,
        reminder_callback=None
    ):
        self.reminder_callback = (
            reminder_callback
        )

        self.stop_event = (
            threading.Event()
        )

        self.thread = None

    def start(self):

        if (
            self.thread
            and self.thread.is_alive()
        ):

            return {
                "success": True,
                "already_running": True,
            }

        self.stop_event.clear()

        self.thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="JarvisScheduler",
        )

        self.thread.start()

        return {
            "success": True,
            "running": True,
        }

    def stop(self):

        self.stop_event.set()

        return {
            "success": True,
        }

    def _run(self):

        while not self.stop_event.is_set():

            try:

                tasks = (
                    _get_due_tasks()
                )

                for task in tasks:

                    self._fire(
                        task
                    )

            except Exception as e:

                print(
                    "[SCHEDULER ERROR]",
                    e
                )

            self.stop_event.wait(
                CHECK_INTERVAL_SECONDS
            )

    def _fire(
        self,
        task
    ):

        try:

            show_notification(
                task["title"],
                task["message"],
            )

            if (
                self.reminder_callback
                is not None
            ):

                try:

                    self.reminder_callback(
                        task
                    )

                except Exception as e:

                    print(
                        "[REMINDER CALLBACK ERROR]",
                        e
                    )

            _mark_completed(
                task["id"]
            )

        except Exception as e:

            print(
                "[REMINDER ERROR]",
                e
            )