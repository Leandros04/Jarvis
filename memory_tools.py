import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = (
    Path.home()
    / "Jarvis"
    / "data"
    / "memory.db"
)


def _now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def _connect():
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = (
        sqlite3.Row
    )

    return conn


def init_memory_db():
    with _connect() as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(category, key)
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_memories_category
            ON memories(category)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_memories_key
            ON memories(key)
            """
        )

    return {
        "success": True,
        "database": str(
            DB_PATH
        ),
    }


def memory_store(
    category,
    key,
    value
):
    try:
        category = (
            str(category)
            .strip()
            .lower()
        )

        key = (
            str(key)
            .strip()
            .lower()
        )

        value = str(
            value
        ).strip()

        if not category:
            return {
                "success": False,
                "error": (
                    "Category cannot be empty."
                ),
            }

        if not key:
            return {
                "success": False,
                "error": (
                    "Key cannot be empty."
                ),
            }

        if not value:
            return {
                "success": False,
                "error": (
                    "Value cannot be empty."
                ),
            }

        now = _now()

        with _connect() as conn:

            existing = conn.execute(
                """
                SELECT
                    id,
                    created_at
                FROM memories
                WHERE category = ?
                AND key = ?
                """,
                (
                    category,
                    key
                ),
            ).fetchone()

            if existing:

                conn.execute(
                    """
                    UPDATE memories
                    SET
                        value = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        value,
                        now,
                        existing["id"]
                    ),
                )

                memory_id = (
                    existing["id"]
                )

                created_at = (
                    existing[
                        "created_at"
                    ]
                )

                action = "updated"

            else:

                cursor = conn.execute(
                    """
                    INSERT INTO memories (
                        category,
                        key,
                        value,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        category,
                        key,
                        value,
                        now,
                        now
                    ),
                )

                memory_id = (
                    cursor.lastrowid
                )

                created_at = now

                action = "created"

        return {
            "success": True,
            "action": action,
            "memory": {
                "id": memory_id,
                "category": category,
                "key": key,
                "value": value,
                "created_at": (
                    created_at
                ),
                "updated_at": now,
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def memory_search(
    query,
    limit=10
):
    try:
        query = (
            str(query)
            .strip()
            .lower()
        )

        limit = max(
            1,
            min(
                int(limit),
                50
            )
        )

        if not query:
            return {
                "success": False,
                "error": (
                    "Search query "
                    "cannot be empty."
                ),
            }

        terms = [
            term
            for term
            in query
            .replace(
                "_",
                " "
            )
            .split()
            if len(term) >= 2
        ]

        if not terms:
            terms = [query]

        where_parts = []
        params = []

        for term in terms:

            like = (
                f"%{term}%"
            )

            where_parts.append(
                """
                (
                    LOWER(category) LIKE ?
                    OR LOWER(key) LIKE ?
                    OR LOWER(value) LIKE ?
                )
                """
            )

            params.extend(
                [
                    like,
                    like,
                    like
                ]
            )

        sql = (
            """
            SELECT
                id,
                category,
                key,
                value,
                created_at,
                updated_at
            FROM memories
            WHERE
            """
            + " OR ".join(
                where_parts
            )
            +
            """
            ORDER BY
                updated_at DESC
            LIMIT ?
            """
        )

        params.append(
            limit
        )

        with _connect() as conn:

            rows = conn.execute(
                sql,
                params
            ).fetchall()

        return {
            "success": True,
            "query": query,
            "count": len(rows),
            "results": [
                dict(row)
                for row in rows
            ],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def memory_list(
    category=None,
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

            if category:

                category = (
                    str(category)
                    .strip()
                    .lower()
                )

                rows = conn.execute(
                    """
                    SELECT
                        id,
                        category,
                        key,
                        value,
                        created_at,
                        updated_at
                    FROM memories
                    WHERE category = ?
                    ORDER BY
                        updated_at DESC
                    LIMIT ?
                    """,
                    (
                        category,
                        limit
                    ),
                ).fetchall()

            else:

                rows = conn.execute(
                    """
                    SELECT
                        id,
                        category,
                        key,
                        value,
                        created_at,
                        updated_at
                    FROM memories
                    ORDER BY
                        updated_at DESC
                    LIMIT ?
                    """,
                    (
                        limit,
                    ),
                ).fetchall()

        return {
            "success": True,
            "category": category,
            "count": len(rows),
            "results": [
                dict(row)
                for row in rows
            ],
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def memory_delete(
    memory_id
):
    try:
        memory_id = int(
            memory_id
        )

        with _connect() as conn:

            row = conn.execute(
                """
                SELECT
                    id,
                    category,
                    key,
                    value
                FROM memories
                WHERE id = ?
                """,
                (
                    memory_id,
                ),
            ).fetchone()

            if not row:
                return {
                    "success": False,
                    "error": (
                        f"Memory id "
                        f"{memory_id} "
                        "does not exist."
                    ),
                }

            conn.execute(
                """
                DELETE FROM memories
                WHERE id = ?
                """,
                (
                    memory_id,
                ),
            )

        return {
            "success": True,
            "deleted": dict(
                row
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }