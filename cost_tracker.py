import sqlite3
import time
from datetime import datetime
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

DB_PATH = (
    Path.home()
    / "Jarvis"
    / "data"
    / "api_usage.db"
)


# USD per 1,000,000 tokens.
PRICES = {
    "gpt-5.6-luna": {
        "input": 0.20,
        "output": 1.20,
    },

    "gpt-5.6-terra": {
        "input": 2.00,
        "output": 12.00,
    },

    "gpt-5.6-sol": {
        "input": 4.00,
        "output": 20.00,
    },

    # Alias for Sol.
    "gpt-5.6": {
        "input": 4.00,
        "output": 20.00,
    },
}


# ============================================================
# DATABASE
# ============================================================

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


def init_cost_db():
    with _connect() as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                model TEXT NOT NULL,
                purpose TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                cached_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                reasoning_tokens INTEGER NOT NULL,
                estimated_cost_usd REAL NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_api_usage_timestamp
            ON api_usage(timestamp)
            """
        )

    return {
        "success": True,
        "database": str(
            DB_PATH
        ),
    }


# ============================================================
# USAGE EXTRACTION
# ============================================================

def _get_attr(
    obj,
    name,
    default=0
):
    if obj is None:
        return default

    if isinstance(
        obj,
        dict
    ):
        return obj.get(
            name,
            default
        )

    return getattr(
        obj,
        name,
        default
    )


def record_response(
    response,
    requested_model,
    purpose="assistant"
):
    try:
        usage = getattr(
            response,
            "usage",
            None
        )

        if usage is None:
            return {
                "success": False,
                "error":
                    "Response has no usage data.",
            }

        input_tokens = int(
            _get_attr(
                usage,
                "input_tokens",
                0
            )
            or 0
        )

        output_tokens = int(
            _get_attr(
                usage,
                "output_tokens",
                0
            )
            or 0
        )

        input_details = (
            _get_attr(
                usage,
                "input_tokens_details",
                None
            )
        )

        output_details = (
            _get_attr(
                usage,
                "output_tokens_details",
                None
            )
        )

        cached_tokens = int(
            _get_attr(
                input_details,
                "cached_tokens",
                0
            )
            or 0
        )

        reasoning_tokens = int(
            _get_attr(
                output_details,
                "reasoning_tokens",
                0
            )
            or 0
        )

        actual_model = (
            getattr(
                response,
                "model",
                None
            )
            or requested_model
        )

        price = PRICES.get(
            actual_model,
            PRICES.get(
                requested_model
            )
        )

        if price:

            # Conservative estimate:
            # count all input tokens at the normal
            # published input price. Cached-input
            # discounts, if applicable, therefore
            # make real cost lower than this number.
            estimated_cost = (
                (
                    input_tokens
                    / 1_000_000
                )
                * price["input"]
                +
                (
                    output_tokens
                    / 1_000_000
                )
                * price["output"]
            )

        else:
            estimated_cost = 0.0

        with _connect() as conn:

            conn.execute(
                """
                INSERT INTO api_usage (
                    timestamp,
                    model,
                    purpose,
                    input_tokens,
                    cached_tokens,
                    output_tokens,
                    reasoning_tokens,
                    estimated_cost_usd
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    actual_model,
                    str(
                        purpose
                    ),
                    input_tokens,
                    cached_tokens,
                    output_tokens,
                    reasoning_tokens,
                    estimated_cost,
                ),
            )

        return {
            "success": True,
            "model": actual_model,
            "input_tokens":
                input_tokens,
            "cached_tokens":
                cached_tokens,
            "output_tokens":
                output_tokens,
            "reasoning_tokens":
                reasoning_tokens,
            "estimated_cost_usd":
                estimated_cost,
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# SUMMARY
# ============================================================

def get_cost_summary(
    days=None
):
    try:
        params = []

        where = ""

        if days is not None:

            days = float(
                days
            )

            cutoff = (
                time.time()
                - (
                    days
                    * 86400
                )
            )

            where = (
                "WHERE timestamp >= ?"
            )

            params.append(
                cutoff
            )

        with _connect() as conn:

            rows = conn.execute(
                f"""
                SELECT
                    model,
                    COUNT(*) AS requests,
                    SUM(input_tokens)
                        AS input_tokens,
                    SUM(cached_tokens)
                        AS cached_tokens,
                    SUM(output_tokens)
                        AS output_tokens,
                    SUM(reasoning_tokens)
                        AS reasoning_tokens,
                    SUM(estimated_cost_usd)
                        AS estimated_cost_usd
                FROM api_usage
                {where}
                GROUP BY model
                ORDER BY estimated_cost_usd DESC
                """,
                params,
            ).fetchall()

        models = []

        total_requests = 0
        total_input = 0
        total_cached = 0
        total_output = 0
        total_reasoning = 0
        total_cost = 0.0

        for row in rows:

            item = dict(
                row
            )

            item[
                "estimated_cost_usd"
            ] = float(
                item.get(
                    "estimated_cost_usd"
                )
                or 0.0
            )

            models.append(
                item
            )

            total_requests += int(
                item.get(
                    "requests"
                )
                or 0
            )

            total_input += int(
                item.get(
                    "input_tokens"
                )
                or 0
            )

            total_cached += int(
                item.get(
                    "cached_tokens"
                )
                or 0
            )

            total_output += int(
                item.get(
                    "output_tokens"
                )
                or 0
            )

            total_reasoning += int(
                item.get(
                    "reasoning_tokens"
                )
                or 0
            )

            total_cost += (
                item[
                    "estimated_cost_usd"
                ]
            )

        return {
            "success": True,
            "period": (
                "all_time"
                if days is None
                else f"{days:g}_days"
            ),
            "requests":
                total_requests,
            "input_tokens":
                total_input,
            "cached_tokens":
                total_cached,
            "output_tokens":
                total_output,
            "reasoning_tokens":
                total_reasoning,
            "estimated_cost_usd":
                total_cost,
            "models":
                models,

            "note": (
                "Cost is a conservative estimate "
                "using published standard input and "
                "output prices. Actual billed cost "
                "can be lower when cached-input "
                "discounts apply."
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


def format_cost_summary(
    days=30
):
    result = get_cost_summary(
        days
    )

    if not result.get(
        "success"
    ):
        return (
            "I couldn't read "
            "the API usage database."
        )

    cost = result[
        "estimated_cost_usd"
    ]

    requests = result[
        "requests"
    ]

    input_tokens = result[
        "input_tokens"
    ]

    output_tokens = result[
        "output_tokens"
    ]

    return (
        f"Last {days:g} days: "
        f"{requests} OpenAI requests, "
        f"{input_tokens:,} input tokens, "
        f"{output_tokens:,} output tokens, "
        f"estimated maximum cost "
        f"${cost:.4f}."
    )


init_cost_db()