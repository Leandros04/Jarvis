import json
import os
import re
import urllib.error
import urllib.request


# ============================================================
# MODELS
# ============================================================

LUNA = "gpt-5.6-luna"
TERRA = "gpt-5.6-terra"
SOL = "gpt-5.6-sol"

MODEL_INFO = {
    "luna": {
        "model": LUNA,
        "effort": "none",
        "display": "GPT-5.6 Luna",
    },
    "terra": {
        "model": TERRA,
        "effort": "low",
        "display": "GPT-5.6 Terra",
    },
    "sol": {
        "model": SOL,
        "effort": "medium",
        "display": "GPT-5.6 Sol",
    },
}


# ============================================================
# OLLAMA
# ============================================================

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://127.0.0.1:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_ROUTER_MODEL",
    "qwen3.5:0.8b"
)

OLLAMA_ENABLED = (
    os.getenv(
        "OLLAMA_ROUTER_ENABLED",
        "1"
    ).strip().lower()
    not in {
        "0",
        "false",
        "no",
        "off",
    }
)


# ============================================================
# OVERRIDE
# ============================================================

_override = "auto"


def set_model_override(mode):
    global _override

    mode = str(
        mode
    ).strip().lower()

    if mode not in {
        "auto",
        "luna",
        "terra",
        "sol",
    }:
        return {
            "success": False,
            "error": (
                "Mode must be auto, luna, "
                "terra, or sol."
            ),
        }

    _override = mode

    return {
        "success": True,
        "mode": _override,
    }


def get_model_override():
    return _override


# ============================================================
# OLLAMA STATUS
# ============================================================

def ollama_status():
    if not OLLAMA_ENABLED:

        return {
            "available": False,
            "enabled": False,
            "model": OLLAMA_MODEL,
            "reason": "disabled",
        }

    try:
        request = urllib.request.Request(
            f"{OLLAMA_URL}/api/tags",
            method="GET",
        )

        with urllib.request.urlopen(
            request,
            timeout=1.2
        ) as response:

            data = json.loads(
                response.read()
                .decode("utf-8")
            )

        models = []

        for item in data.get(
            "models",
            []
        ):
            name = item.get(
                "name",
                ""
            )

            if name:
                models.append(
                    name
                )

        installed = any(
            name == OLLAMA_MODEL
            or name.startswith(
                OLLAMA_MODEL + ":"
            )
            for name in models
        )

        return {
            "available": installed,
            "enabled": True,
            "server_running": True,
            "model": OLLAMA_MODEL,
            "installed": installed,
        }

    except Exception as e:

        return {
            "available": False,
            "enabled": True,
            "server_running": False,
            "model": OLLAMA_MODEL,
            "reason": str(e),
        }


# ============================================================
# LOCAL MODEL ROUTER
# ============================================================

def _ollama_classify(text):
    prompt = f"""
You are a routing classifier for a Windows personal assistant.

Choose exactly one capability tier:

luna:
Normal conversation, basic explanations, ordinary computer
automation, browser navigation, file operations, reminders,
short summaries, simple reasoning, straightforward questions.

terra:
Substantial coding/debugging, difficult technical explanations,
multi-step planning, detailed analysis, complex comparisons,
large documents, or tasks where extra reasoning materially helps.

sol:
Only exceptionally difficult tasks: advanced architecture,
very hard mathematics/science, difficult research synthesis,
complex debugging where Terra may struggle, or when the user
explicitly requests maximum intelligence.

Cost matters heavily.
Prefer luna unless extra intelligence is genuinely useful.
Prefer terra over sol unless the task is unusually difficult.

User request:
{text}

Return only JSON:
{{"route":"luna|terra|sol","reason":"short reason"}}
""".strip()

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",

        # Keep the tiny model around briefly for follow-ups,
        # then let Ollama free its RAM.
        "keep_alive": "30s",

        "options": {
            "temperature": 0,
            "num_predict": 80,
        },
    }).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={
            "Content-Type":
                "application/json"
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=15
    ) as response:

        result = json.loads(
            response.read()
            .decode("utf-8")
        )

    raw = result.get(
        "response",
        ""
    ).strip()

    parsed = json.loads(
        raw
    )

    route = str(
        parsed.get(
            "route",
            ""
        )
    ).strip().lower()

    if route not in MODEL_INFO:
        raise ValueError(
            "Invalid Ollama route."
        )

    return {
        "tier": route,
        "reason": str(
            parsed.get(
                "reason",
                "local classification"
            )
        ),
    }


# ============================================================
# FAST HEURISTICS
# ============================================================

def _explicit_route(text):
    lower = text.lower()

    sol_patterns = (
        "use sol",
        "use the strongest model",
        "maximum intelligence",
        "maximum reasoning",
        "strongest model",
        "think as hard as possible",
    )

    if any(
        item in lower
        for item in sol_patterns
    ):
        return {
            "tier": "sol",
            "reason":
                "explicit high-capability request",
        }

    terra_patterns = (
        "use terra",
        "deep analysis",
        "analyze deeply",
        "debug this code",
        "debug this program",
        "architect ",
        "architecture ",
        "research this",
        "extensive research",
        "compare in detail",
    )

    if any(
        item in lower
        for item in terra_patterns
    ):
        return {
            "tier": "terra",
            "reason":
                "complex-task keyword",
        }

    return None


def _obviously_simple(text):
    lower = text.lower().strip()

    if len(lower) <= 55:
        return True

    simple_prefixes = (
        "open ",
        "close ",
        "set volume",
        "volume ",
        "pause",
        "play ",
        "next ",
        "previous ",
        "remind me",
        "set a timer",
        "create a folder",
        "create a file",
        "rename ",
        "move ",
        "copy ",
        "what's on my clipboard",
        "what is on my clipboard",
        "show me",
        "bring ",
        "minimize ",
        "maximize ",
        "search for ",
        "google ",
    )

    return lower.startswith(
        simple_prefixes
    )


# ============================================================
# MAIN ROUTER
# ============================================================

def route_model(text):
    text = str(
        text
    ).strip()

    # Manual override always wins.
    if _override != "auto":

        info = MODEL_INFO[
            _override
        ]

        return {
            "tier": _override,
            "model": info[
                "model"
            ],
            "display": info[
                "display"
            ],
            "effort": info[
                "effort"
            ],
            "source": "manual_override",
            "reason": (
                f"manual {_override} mode"
            ),
        }

    explicit = _explicit_route(
        text
    )

    if explicit:

        tier = explicit[
            "tier"
        ]

        info = MODEL_INFO[
            tier
        ]

        return {
            "tier": tier,
            "model": info[
                "model"
            ],
            "display": info[
                "display"
            ],
            "effort": info[
                "effort"
            ],
            "source": "heuristic",
            "reason": explicit[
                "reason"
            ],
        }

    if _obviously_simple(
        text
    ):

        info = MODEL_INFO[
            "luna"
        ]

        return {
            "tier": "luna",
            "model": info[
                "model"
            ],
            "display": info[
                "display"
            ],
            "effort": info[
                "effort"
            ],
            "source": "fast_local",
            "reason":
                "routine/simple request",
        }

    # For longer ambiguous requests, let the tiny
    # local model decide. No OpenAI tokens are spent.
    if (
        OLLAMA_ENABLED
        and len(text) >= 80
    ):

        status = ollama_status()

        if status.get(
            "available"
        ):

            try:
                decision = (
                    _ollama_classify(
                        text
                    )
                )

                tier = decision[
                    "tier"
                ]

                info = MODEL_INFO[
                    tier
                ]

                return {
                    "tier": tier,
                    "model": info[
                        "model"
                    ],
                    "display": info[
                        "display"
                    ],
                    "effort": info[
                        "effort"
                    ],
                    "source":
                        "ollama",
                    "reason":
                        decision[
                            "reason"
                        ],
                }

            except Exception:
                pass

    # Most requests should stay cheap.
    info = MODEL_INFO[
        "luna"
    ]

    return {
        "tier": "luna",
        "model": info[
            "model"
        ],
        "display": info[
            "display"
        ],
        "effort": info[
            "effort"
        ],
        "source": "fallback",
        "reason":
            "cost-efficient default",
    }


def router_status():
    return {
        "override":
            _override,
        "ollama":
            ollama_status(),
        "models":
            MODEL_INFO,
    }