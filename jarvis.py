import base64
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# ORIGINAL SYSTEM TOOLS
# ============================================================

from system_tools import (
    get_system_status,
    get_top_processes,
    get_user_paths,
    get_screen_info,
    capture_screen,
    move_mouse,
    click_mouse,
    scroll_mouse,
    type_text,
    press_key,
    press_hotkey,
    list_applications,
    open_application,
    list_directory,
    find_files,
    open_file,
    read_file,
)


# ============================================================
# BROWSER
# ============================================================

from browser_tools import (
    browser_open,
    browser_close,
    browser_navigate,
    browser_search,
    browser_back,
    browser_forward,
    browser_reload,
    browser_current_page,
    browser_inspect,
    browser_click,
    browser_fill,
    browser_press,
)


# ============================================================
# MEMORY
# ============================================================

from memory_tools import (
    init_memory_db,
    memory_store,
    memory_search,
    memory_list,
    memory_delete,
)


# ============================================================
# VOICE
# ============================================================

from voice_tools import (
    listen_and_transcribe,
    speak,
)


# ============================================================
# WAKE WORD
# ============================================================

from wakeword_tools import (
    wait_for_wakeword,
    load_wakeword_model,
)


# ============================================================
# DESKTOP CONTROL
# ============================================================

from desktop_tools import (
    get_audio_status,
    set_volume,
    change_volume,
    set_mute,
    toggle_mute,
    media_play_pause,
    media_next,
    media_previous,
    media_stop,
    get_clipboard,
    set_clipboard,
    clear_clipboard,
    list_windows,
    get_active_window,
    focus_window,
    minimize_window,
    maximize_window,
    restore_window,
    show_notification,
)


# ============================================================
# SCHEDULER
# ============================================================

from scheduler_tools import (
    init_scheduler_db,
    get_local_datetime,
    schedule_timer,
    schedule_reminder_at,
    list_scheduled_tasks,
    cancel_scheduled_task,
    JarvisScheduler,
)


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

client = OpenAI(
    api_key=os.getenv(
        "OPENAI_API_KEY"
    )
)

MODEL = "gpt-5.5"

VOICE_RESPONSE_MAX_CHARS = 1200


init_memory_db()
init_scheduler_db()


# ============================================================
# SCREEN VISION
# ============================================================

def analyze_screen(
    question
):

    capture = capture_screen()

    if not capture.get(
        "success"
    ):
        return capture

    image_path = Path(
        capture["path"]
    )

    try:

        with open(
            image_path,
            "rb"
        ) as file:

            encoded = (
                base64
                .b64encode(
                    file.read()
                )
                .decode(
                    "utf-8"
                )
            )

        response = (
            client.responses.create(
                model=MODEL,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": (
                                    "input_text"
                                ),
                                "text": (
                                    "Examine the current "
                                    "Windows desktop screenshot.\n\n"
                                    "Only describe what is "
                                    "actually visible.\n\n"
                                    "If locating a clickable "
                                    "element, provide its approximate "
                                    "center pixel coordinates.\n\n"
                                    f"Question: {question}"
                                ),
                            },
                            {
                                "type": (
                                    "input_image"
                                ),
                                "image_url": (
                                    "data:image/png;base64,"
                                    + encoded
                                ),
                                "detail": "high",
                            },
                        ],
                    }
                ],
            )
        )

        return {
            "success": True,
            "analysis": (
                response.output_text
            ),
            "screenshot": str(
                image_path
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# TOOL BUILDER
# ============================================================

def function_tool(
    name,
    description,
    properties=None,
    required=None
):

    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": (
                properties
                or {}
            ),
            "required": (
                required
                or []
            ),
            "additionalProperties": False,
        },
        "strict": True,
    }


# ============================================================
# TOOL DEFINITIONS
# ============================================================

TOOLS = [

    # SYSTEM

    function_tool(
        "get_system_status",
        "Get CPU, RAM and disk usage."
    ),

    function_tool(
        "get_top_processes",
        "Get processes using the most RAM."
    ),

    function_tool(
        "get_user_paths",
        "Get standard Windows user folders."
    ),

    # SCREEN

    function_tool(
        "get_screen_info",
        (
            "Get screen dimensions and "
            "cursor position."
        ),
    ),

    function_tool(
        "analyze_screen",
        (
            "Visually inspect the current "
            "Windows desktop."
        ),
        {
            "question": {
                "type": "string"
            }
        },
        [
            "question"
        ],
    ),

    # MOUSE

    function_tool(
        "move_mouse",
        "Move the mouse.",
        {
            "x": {
                "type": "integer"
            },
            "y": {
                "type": "integer"
            },
            "duration": {
                "type": "number"
            },
        },
        [
            "x",
            "y",
            "duration"
        ],
    ),

    function_tool(
        "click_mouse",
        "Click the mouse.",
        {
            "x": {
                "type": [
                    "integer",
                    "null"
                ]
            },
            "y": {
                "type": [
                    "integer",
                    "null"
                ]
            },
            "button": {
                "type": "string",
                "enum": [
                    "left",
                    "right",
                    "middle"
                ]
            },
            "clicks": {
                "type": "integer"
            },
        },
        [
            "x",
            "y",
            "button",
            "clicks"
        ],
    ),

    function_tool(
        "scroll_mouse",
        "Scroll the active window.",
        {
            "amount": {
                "type": "integer"
            }
        },
        [
            "amount"
        ],
    ),

    # KEYBOARD

    function_tool(
        "type_text",
        "Type text into the active application.",
        {
            "text": {
                "type": "string"
            },
            "interval": {
                "type": "number"
            },
        },
        [
            "text",
            "interval"
        ],
    ),

    function_tool(
        "press_key",
        "Press a keyboard key.",
        {
            "key": {
                "type": "string"
            },
            "presses": {
                "type": "integer"
            },
        },
        [
            "key",
            "presses"
        ],
    ),

    function_tool(
        "press_hotkey",
        "Press a keyboard shortcut.",
        {
            "keys": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },
        [
            "keys"
        ],
    ),

    # APPLICATIONS

    function_tool(
        "list_applications",
        "Find installed applications.",
        {
            "search_term": {
                "type": [
                    "string",
                    "null"
                ]
            }
        },
        [
            "search_term"
        ],
    ),

    function_tool(
        "open_application",
        "Open an installed application.",
        {
            "app_name": {
                "type": "string"
            }
        },
        [
            "app_name"
        ],
    ),

    # FILES

    function_tool(
        "list_directory",
        "List a directory.",
        {
            "path": {
                "type": "string"
            }
        },
        [
            "path"
        ],
    ),

    function_tool(
        "find_files",
        "Search for files.",
        {
            "search_term": {
                "type": "string"
            },
            "root": {
                "type": [
                    "string",
                    "null"
                ]
            },
        },
        [
            "search_term",
            "root"
        ],
    ),

    function_tool(
        "open_file",
        "Open a file or folder.",
        {
            "path": {
                "type": "string"
            }
        },
        [
            "path"
        ],
    ),

    function_tool(
        "read_file",
        "Read supported file contents.",
        {
            "path": {
                "type": "string"
            },
            "max_chars": {
                "type": [
                    "integer",
                    "null"
                ]
            },
            "start_page": {
                "type": [
                    "integer",
                    "null"
                ]
            },
            "end_page": {
                "type": [
                    "integer",
                    "null"
                ]
            },
        },
        [
            "path",
            "max_chars",
            "start_page",
            "end_page"
        ],
    ),

    # BROWSER

    function_tool(
        "browser_open",
        "Open Jarvis Chromium."
    ),

    function_tool(
        "browser_navigate",
        "Navigate to a URL.",
        {
            "url": {
                "type": "string"
            }
        },
        [
            "url"
        ],
    ),

    function_tool(
        "browser_search",
        "Search Google.",
        {
            "query": {
                "type": "string"
            }
        },
        [
            "query"
        ],
    ),

    function_tool(
        "browser_current_page",
        "Get current webpage title and URL."
    ),

    function_tool(
        "browser_inspect",
        (
            "Read webpage text and interactive "
            "elements."
        ),
        {
            "max_elements": {
                "type": "integer"
            },
            "max_text_chars": {
                "type": "integer"
            },
        },
        [
            "max_elements",
            "max_text_chars"
        ],
    ),

    function_tool(
        "browser_click",
        "Click a webpage J-reference.",
        {
            "ref": {
                "type": "string"
            }
        },
        [
            "ref"
        ],
    ),

    function_tool(
        "browser_fill",
        "Fill a webpage field.",
        {
            "ref": {
                "type": "string"
            },
            "text": {
                "type": "string"
            },
        },
        [
            "ref",
            "text"
        ],
    ),

    function_tool(
        "browser_press",
        "Press a key on a webpage field.",
        {
            "ref": {
                "type": "string"
            },
            "key": {
                "type": "string"
            },
        },
        [
            "ref",
            "key"
        ],
    ),

    function_tool(
        "browser_back",
        "Browser back."
    ),

    function_tool(
        "browser_forward",
        "Browser forward."
    ),

    function_tool(
        "browser_reload",
        "Reload browser page."
    ),

    # MEMORY

    function_tool(
        "memory_store",
        "Store a persistent memory.",
        {
            "category": {
                "type": "string"
            },
            "key": {
                "type": "string"
            },
            "value": {
                "type": "string"
            },
        },
        [
            "category",
            "key",
            "value"
        ],
    ),

    function_tool(
        "memory_search",
        "Search persistent memory.",
        {
            "query": {
                "type": "string"
            },
            "limit": {
                "type": "integer"
            },
        },
        [
            "query",
            "limit"
        ],
    ),

    function_tool(
        "memory_list",
        "List persistent memories.",
        {
            "category": {
                "type": [
                    "string",
                    "null"
                ]
            },
            "limit": {
                "type": "integer"
            },
        },
        [
            "category",
            "limit"
        ],
    ),

    function_tool(
        "memory_delete",
        "Delete a persistent memory.",
        {
            "memory_id": {
                "type": "integer"
            }
        },
        [
            "memory_id"
        ],
    ),

    # AUDIO / MEDIA

    function_tool(
        "get_audio_status",
        "Get Windows master volume and mute state."
    ),

    function_tool(
        "set_volume",
        "Set Windows master volume percentage.",
        {
            "percent": {
                "type": "number"
            }
        },
        [
            "percent"
        ],
    ),

    function_tool(
        "change_volume",
        "Increase or decrease Windows volume.",
        {
            "amount": {
                "type": "number"
            }
        },
        [
            "amount"
        ],
    ),

    function_tool(
        "set_mute",
        "Set Windows mute state.",
        {
            "muted": {
                "type": "boolean"
            }
        },
        [
            "muted"
        ],
    ),

    function_tool(
        "media_play_pause",
        "Play or pause current media."
    ),

    function_tool(
        "media_next",
        "Skip to next media track."
    ),

    function_tool(
        "media_previous",
        "Go to previous media track."
    ),

    function_tool(
        "media_stop",
        "Stop current media."
    ),

    # CLIPBOARD

    function_tool(
        "get_clipboard",
        "Read plaintext from Windows clipboard."
    ),

    function_tool(
        "set_clipboard",
        "Copy plaintext to Windows clipboard.",
        {
            "text": {
                "type": "string"
            }
        },
        [
            "text"
        ],
    ),

    function_tool(
        "clear_clipboard",
        "Clear the Windows clipboard."
    ),

    # WINDOWS

    function_tool(
        "list_windows",
        "List currently open Windows windows."
    ),

    function_tool(
        "get_active_window",
        "Get the currently active window."
    ),

    function_tool(
        "focus_window",
        "Bring a window to the front.",
        {
            "title_query": {
                "type": "string"
            }
        },
        [
            "title_query"
        ],
    ),

    function_tool(
        "minimize_window",
        "Minimize a window.",
        {
            "title_query": {
                "type": "string"
            }
        },
        [
            "title_query"
        ],
    ),

    function_tool(
        "maximize_window",
        "Maximize a window.",
        {
            "title_query": {
                "type": "string"
            }
        },
        [
            "title_query"
        ],
    ),

    function_tool(
        "restore_window",
        "Restore a window.",
        {
            "title_query": {
                "type": "string"
            }
        },
        [
            "title_query"
        ],
    ),

    function_tool(
        "show_notification",
        "Show a Windows notification.",
        {
            "title": {
                "type": "string"
            },
            "message": {
                "type": "string"
            },
        },
        [
            "title",
            "message"
        ],
    ),

    # TIME + SCHEDULER

    function_tool(
        "get_local_datetime",
        (
            "Get the computer's exact "
            "current local date and time."
        ),
    ),

    function_tool(
        "schedule_timer",
        "Create a timer.",
        {
            "seconds": {
                "type": "number"
            },
            "message": {
                "type": "string"
            },
        },
        [
            "seconds",
            "message"
        ],
    ),

    function_tool(
        "schedule_reminder_at",
        (
            "Create a reminder at an exact local "
            "ISO datetime."
        ),
        {
            "local_datetime": {
                "type": "string"
            },
            "message": {
                "type": "string"
            },
            "title": {
                "type": "string"
            },
        },
        [
            "local_datetime",
            "message",
            "title"
        ],
    ),

    function_tool(
        "list_scheduled_tasks",
        "List scheduled reminders and timers.",
        {
            "include_completed": {
                "type": "boolean"
            },
            "limit": {
                "type": "integer"
            },
        },
        [
            "include_completed",
            "limit"
        ],
    ),

    function_tool(
        "cancel_scheduled_task",
        "Cancel a scheduled task by id.",
        {
            "task_id": {
                "type": "integer"
            }
        },
        [
            "task_id"
        ],
    ),
]


# ============================================================
# SYSTEM PROMPT
# ============================================================

INSTRUCTIONS = """
You are JARVIS, a personal AI assistant running on the user's
Windows computer.

Use tools whenever computer state or an action is required.

Be concise for simple commands.

EFFICIENCY

Prefer the cheapest reliable path.
Do not call unnecessary tools.
Common audio, media, timer and reminder commands may already be
handled locally before reaching you.

TIME

When the user requests a relative timer such as "in 20 minutes",
use schedule_timer.

When the user requests a specific clock time or date, call
get_local_datetime first when necessary, resolve the requested
future local datetime, then use schedule_reminder_at.

MEMORY

Store durable user-requested information using memory_store.
Never store credentials or secrets.

BROWSER

Prefer Playwright browser tools for normal websites.

WINDOWS GUI

Use screen vision and mouse/keyboard tools for desktop programs.

FILES

Use filesystem tools instead of guessing.

SAFETY

Never claim success unless a tool reported success.

Do not autonomously confirm purchases, financial transactions,
account deletion, drive formatting, irreversible deletion, or
similarly consequential actions.
"""


# ============================================================
# TOOL EXECUTOR
# ============================================================

def execute_tool(
    name,
    a
):

    mapping_no_args = {

        "get_system_status":
            get_system_status,

        "get_top_processes":
            get_top_processes,

        "get_user_paths":
            get_user_paths,

        "get_screen_info":
            get_screen_info,

        "browser_open":
            browser_open,

        "browser_current_page":
            browser_current_page,

        "browser_back":
            browser_back,

        "browser_forward":
            browser_forward,

        "browser_reload":
            browser_reload,

        "get_audio_status":
            get_audio_status,

        "media_play_pause":
            media_play_pause,

        "media_next":
            media_next,

        "media_previous":
            media_previous,

        "media_stop":
            media_stop,

        "get_clipboard":
            get_clipboard,

        "clear_clipboard":
            clear_clipboard,

        "list_windows":
            list_windows,

        "get_active_window":
            get_active_window,

        "get_local_datetime":
            get_local_datetime,
    }

    if name in mapping_no_args:

        return (
            mapping_no_args[
                name
            ]()
        )


    if name == "analyze_screen":

        return analyze_screen(
            a["question"]
        )


    if name == "move_mouse":

        return move_mouse(
            a["x"],
            a["y"],
            a["duration"]
        )


    if name == "click_mouse":

        return click_mouse(
            a["x"],
            a["y"],
            a["button"],
            a["clicks"],
        )


    if name == "scroll_mouse":

        return scroll_mouse(
            a["amount"]
        )


    if name == "type_text":

        return type_text(
            a["text"],
            a["interval"]
        )


    if name == "press_key":

        return press_key(
            a["key"],
            a["presses"]
        )


    if name == "press_hotkey":

        return press_hotkey(
            a["keys"]
        )


    if name == "list_applications":

        return list_applications(
            a["search_term"]
        )


    if name == "open_application":

        return open_application(
            a["app_name"]
        )


    if name == "list_directory":

        return list_directory(
            a["path"]
        )


    if name == "find_files":

        return find_files(
            a["search_term"],
            a["root"]
        )


    if name == "open_file":

        return open_file(
            a["path"]
        )


    if name == "read_file":

        return read_file(
            a["path"],
            a["max_chars"],
            a["start_page"],
            a["end_page"],
        )


    if name == "browser_navigate":

        return browser_navigate(
            a["url"]
        )


    if name == "browser_search":

        return browser_search(
            a["query"]
        )


    if name == "browser_inspect":

        return browser_inspect(
            a["max_elements"],
            a["max_text_chars"]
        )


    if name == "browser_click":

        return browser_click(
            a["ref"]
        )


    if name == "browser_fill":

        return browser_fill(
            a["ref"],
            a["text"]
        )


    if name == "browser_press":

        return browser_press(
            a["ref"],
            a["key"]
        )


    if name == "memory_store":

        return memory_store(
            a["category"],
            a["key"],
            a["value"]
        )


    if name == "memory_search":

        return memory_search(
            a["query"],
            a["limit"]
        )


    if name == "memory_list":

        return memory_list(
            a["category"],
            a["limit"]
        )


    if name == "memory_delete":

        return memory_delete(
            a["memory_id"]
        )


    if name == "set_volume":

        return set_volume(
            a["percent"]
        )


    if name == "change_volume":

        return change_volume(
            a["amount"]
        )


    if name == "set_mute":

        return set_mute(
            a["muted"]
        )


    if name == "set_clipboard":

        return set_clipboard(
            a["text"]
        )


    if name == "focus_window":

        return focus_window(
            a["title_query"]
        )


    if name == "minimize_window":

        return minimize_window(
            a["title_query"]
        )


    if name == "maximize_window":

        return maximize_window(
            a["title_query"]
        )


    if name == "restore_window":

        return restore_window(
            a["title_query"]
        )


    if name == "show_notification":

        return show_notification(
            a["title"],
            a["message"]
        )


    if name == "schedule_timer":

        return schedule_timer(
            a["seconds"],
            a["message"]
        )


    if name == "schedule_reminder_at":

        return schedule_reminder_at(
            a["local_datetime"],
            a["message"],
            a["title"]
        )


    if name == "list_scheduled_tasks":

        return list_scheduled_tasks(
            a["include_completed"],
            a["limit"]
        )


    if name == "cancel_scheduled_task":

        return cancel_scheduled_task(
            a["task_id"]
        )


    return {
        "success": False,
        "error": (
            f"Unknown tool: {name}"
        ),
    }


# ============================================================
# OPENAI LOOP
# ============================================================

def run_jarvis(
    user_input,
    previous_response_id
):

    try:

        request = {
            "model": MODEL,
            "instructions": INSTRUCTIONS,
            "tools": TOOLS,
            "input": user_input,
        }

        if previous_response_id:

            request[
                "previous_response_id"
            ] = previous_response_id

        response = (
            client.responses.create(
                **request
            )
        )

        while True:

            calls = [
                item
                for item
                in response.output
                if item.type
                == "function_call"
            ]

            if not calls:

                return {
                    "success": True,
                    "text": (
                        response.output_text
                    ),
                    "response_id": (
                        response.id
                    ),
                }

            outputs = []

            for call in calls:

                print(
                    f"[JARVIS: "
                    f"{call.name}]"
                )

                try:

                    args = json.loads(
                        call.arguments
                    )

                    result = execute_tool(
                        call.name,
                        args
                    )

                except Exception as e:

                    result = {
                        "success": False,
                        "error": str(e),
                    }

                outputs.append({
                    "type":
                        "function_call_output",
                    "call_id":
                        call.call_id,
                    "output":
                        json.dumps(
                            result,
                            ensure_ascii=False
                        ),
                })

            response = (
                client.responses.create(
                    model=MODEL,
                    instructions=INSTRUCTIONS,
                    tools=TOOLS,
                    previous_response_id=(
                        response.id
                    ),
                    input=outputs,
                )
            )

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# SPEECH OUTPUT
# ============================================================

def speak_response(
    text
):

    text = str(
        text
    ).strip()

    if not text:
        return

    if (
        len(text)
        <= VOICE_RESPONSE_MAX_CHARS
    ):

        speak(
            text
        )

        return

    shortened = (
        text[
            :VOICE_RESPONSE_MAX_CHARS
        ]
    )

    space = shortened.rfind(
        " "
    )

    if space > 500:

        shortened = (
            shortened[:space]
        )

    speak(
        shortened
        + ". The rest is in the log."
    )


# ============================================================
# LOCAL FAST PATH
# ============================================================

def seconds_from_unit(
    amount,
    unit
):

    amount = float(
        amount
    )

    unit = unit.lower()

    if unit.startswith(
        "second"
    ):
        return amount

    if unit.startswith(
        "minute"
    ):
        return (
            amount * 60
        )

    if unit.startswith(
        "hour"
    ):
        return (
            amount * 3600
        )

    return None


def local_fast_command(
    text
):

    raw = str(
        text
    ).strip()

    command = raw.lower()


    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    match = re.fullmatch(
        r"(?:set\s+)?(?:the\s+)?"
        r"volume(?:\s+to)?\s+"
        r"(\d{1,3})(?:\s*(?:%|percent))?",
        command
    )

    if match:

        value = int(
            match.group(1)
        )

        result = set_volume(
            value
        )

        if result.get(
            "success"
        ):

            return {
                "handled": True,
                "response": (
                    f"Volume set to "
                    f"{result['volume_percent']:.0f} percent."
                ),
            }


    if command in {
        "volume up",
        "turn it up",
        "louder",
        "increase volume",
    }:

        result = change_volume(
            10
        )

        return {
            "handled": True,
            "response": (
                f"Volume {result.get('volume_percent', '')} percent."
                if result.get("success")
                else "I couldn't change the volume."
            ),
        }


    if command in {
        "volume down",
        "turn it down",
        "quieter",
        "decrease volume",
    }:

        result = change_volume(
            -10
        )

        return {
            "handled": True,
            "response": (
                f"Volume {result.get('volume_percent', '')} percent."
                if result.get("success")
                else "I couldn't change the volume."
            ),
        }


    if command in {
        "mute",
        "mute audio",
        "mute the computer",
    }:

        set_mute(
            True
        )

        return {
            "handled": True,
            "response": "Muted.",
        }


    if command in {
        "unmute",
        "unmute audio",
        "unmute the computer",
    }:

        set_mute(
            False
        )

        return {
            "handled": True,
            "response": "Unmuted.",
        }


    # --------------------------------------------------------
    # MEDIA
    # --------------------------------------------------------

    if command in {
        "pause",
        "pause music",
        "pause the music",
        "pause media",
        "play",
        "play music",
        "resume",
        "resume music",
    }:

        media_play_pause()

        return {
            "handled": True,
            "response": "Done.",
        }


    if command in {
        "next",
        "next song",
        "next track",
        "skip",
        "skip song",
    }:

        media_next()

        return {
            "handled": True,
            "response": "Skipped.",
        }


    if command in {
        "previous",
        "previous song",
        "previous track",
        "go back a song",
    }:

        media_previous()

        return {
            "handled": True,
            "response": "Done.",
        }


    # --------------------------------------------------------
    # TIMERS
    # --------------------------------------------------------

    match = re.fullmatch(
        r"(?:set\s+)?(?:a\s+)?"
        r"timer(?:\s+for)?\s+"
        r"(\d+(?:\.\d+)?)\s*"
        r"(seconds?|minutes?|hours?)",
        command
    )

    if match:

        amount = float(
            match.group(1)
        )

        unit = (
            match.group(2)
        )

        seconds = seconds_from_unit(
            amount,
            unit
        )

        result = schedule_timer(
            seconds,
            (
                f"Your {amount:g} "
                f"{unit} timer is finished."
            )
        )

        if result.get(
            "success"
        ):

            return {
                "handled": True,
                "response": (
                    f"Timer set for "
                    f"{amount:g} {unit}."
                ),
            }


    # --------------------------------------------------------
    # REMIND ME IN ...
    # --------------------------------------------------------

    match = re.fullmatch(
        r"remind me in\s+"
        r"(\d+(?:\.\d+)?)\s*"
        r"(seconds?|minutes?|hours?)\s+"
        r"to\s+(.+)",
        raw,
        flags=re.IGNORECASE
    )

    if match:

        amount = float(
            match.group(1)
        )

        unit = (
            match.group(2)
        )

        message = (
            match.group(3)
            .strip()
        )

        seconds = seconds_from_unit(
            amount,
            unit
        )

        result = schedule_timer(
            seconds,
            message
        )

        if result.get(
            "success"
        ):

            return {
                "handled": True,
                "response": (
                    f"I'll remind you in "
                    f"{amount:g} {unit}."
                ),
            }


    # --------------------------------------------------------
    # CLIPBOARD
    # --------------------------------------------------------

    if command in {
        "what is on my clipboard",
        "what's on my clipboard",
        "read my clipboard",
        "read the clipboard",
    }:

        result = get_clipboard()

        if result.get(
            "success"
        ):

            value = result.get(
                "text",
                ""
            )

            if not value:

                response = (
                    "The clipboard is empty."
                )

            elif len(value) > 500:

                response = (
                    value[:500]
                    + ". The clipboard contains more text."
                )

            else:

                response = value

            return {
                "handled": True,
                "response": response,
            }


    return {
        "handled": False
    }


# ============================================================
# LOCAL META COMMANDS
# ============================================================

def meta_command(
    text
):

    command = (
        str(text)
        .strip()
        .lower()
    )

    if command in {
        "/wake",
        "wake mode",
        "standby mode",
        "go into standby",
    }:

        return {
            "type": "mode",
            "mode": "wake",
        }


    if command in {
        "/voice",
        "voice mode",
    }:

        return {
            "type": "mode",
            "mode": "voice",
        }


    if command in {
        "/text",
        "text mode",
        "keyboard mode",
    }:

        return {
            "type": "mode",
            "mode": "text",
        }


    if command in {
        "/mute",
        "mute yourself",
    }:

        return {
            "type": "speech_mute"
        }


    if command in {
        "/unmute",
        "unmute yourself",
    }:

        return {
            "type": "speech_unmute"
        }


    if command in {
        "/new",
        "/reset",
        "new conversation",
        "reset conversation",
    }:

        return {
            "type": "reset"
        }


    if command in {
        "exit",
        "quit",
        "shutdown jarvis",
        "shut down jarvis",
    }:

        return {
            "type": "shutdown"
        }


    return None


# ============================================================
# STATE
# ============================================================

previous_response_id = None

input_mode = "wake"

voice_output_enabled = True

running = True


# ============================================================
# REMINDER CALLBACK
# ============================================================

def reminder_fired(
    task
):

    print()
    print(
        f"[REMINDER] "
        f"{task['message']}"
    )
    print()

    if voice_output_enabled:

        try:

            speak(
                task["message"]
            )

        except Exception:
            pass


scheduler = JarvisScheduler(
    reminder_callback=(
        reminder_fired
    )
)

scheduler.start()


# ============================================================
# STARTUP
# ============================================================

print()
print(
    "=========================================="
)
print(
    "              JARVIS ONLINE"
)
print(
    "=========================================="
)
print()
print(
    "Local fast commands: ENABLED"
)
print(
    "Persistent reminders: ENABLED"
)
print(
    "Desktop control: ENABLED"
)
print(
    "Wake phrase: Hey Jarvis"
)
print()


try:

    load_wakeword_model()

    print(
        "JARVIS: Standing by."
    )

except Exception as e:

    print(
        "Wake word failed:",
        e
    )

    input_mode = "text"


# ============================================================
# MAIN LOOP
# ============================================================

while running:

    try:

        # ----------------------------------------------------
        # WAKE MODE
        # ----------------------------------------------------

        if input_mode == "wake":

            wake = (
                wait_for_wakeword()
            )

            if wake.get(
                "cancelled"
            ):

                input_mode = "text"

                continue

            if not wake.get(
                "success"
            ):

                continue

            result = (
                listen_and_transcribe()
            )

            if not result.get(
                "success"
            ):

                continue

            user_input = (
                result["text"]
            )

            print(
                f"You said: "
                f"{user_input}"
            )


        # ----------------------------------------------------
        # PUSH TO TALK
        # ----------------------------------------------------

        elif input_mode == "voice":

            typed = input(
                "ENTER to speak > "
            ).strip()

            if typed:

                user_input = typed

            else:

                result = (
                    listen_and_transcribe()
                )

                if not result.get(
                    "success"
                ):

                    continue

                user_input = (
                    result["text"]
                )


        # ----------------------------------------------------
        # TEXT MODE
        # ----------------------------------------------------

        else:

            user_input = input(
                "You: "
            ).strip()


        if not user_input:

            continue


        # ----------------------------------------------------
        # META COMMANDS
        # ----------------------------------------------------

        meta = meta_command(
            user_input
        )

        if meta:

            action = meta[
                "type"
            ]


            if action == "shutdown":

                running = False

                break


            if action == "mode":

                input_mode = meta[
                    "mode"
                ]

                print(
                    f"Mode: "
                    f"{input_mode}"
                )

                continue


            if action == "speech_mute":

                voice_output_enabled = False

                print(
                    "Voice output muted."
                )

                continue


            if action == "speech_unmute":

                voice_output_enabled = True

                speak(
                    "Voice output enabled."
                )

                continue


            if action == "reset":

                previous_response_id = None

                print(
                    "Conversation reset."
                )

                continue


        # ----------------------------------------------------
        # ZERO-COST LOCAL FAST COMMAND
        # ----------------------------------------------------

        fast = local_fast_command(
            user_input
        )

        if fast.get(
            "handled"
        ):

            response_text = (
                fast["response"]
            )

            print()
            print(
                f"JARVIS: "
                f"{response_text}"
            )
            print()

            if (
                input_mode
                != "text"
                and voice_output_enabled
            ):

                speak(
                    response_text
                )

            continue


        # ----------------------------------------------------
        # AI
        # ----------------------------------------------------

        result = run_jarvis(
            user_input,
            previous_response_id
        )

        if not result.get(
            "success"
        ):

            print(
                "JARVIS ERROR:",
                result.get(
                    "error"
                )
            )

            continue


        response_text = (
            result["text"]
        )

        previous_response_id = (
            result[
                "response_id"
            ]
        )


        print()
        print(
            f"JARVIS: "
            f"{response_text}"
        )
        print()


        if (
            input_mode
            != "text"
            and voice_output_enabled
        ):

            speak_response(
                response_text
            )


    except KeyboardInterrupt:

        if input_mode == "wake":

            input_mode = "text"

            print(
                "\nText mode."
            )

        else:

            print(
                "\nInterrupted."
            )


    except Exception as e:

        print(
            "JARVIS ERROR:",
            e
        )


# ============================================================
# SHUTDOWN
# ============================================================

scheduler.stop()

try:
    browser_close()
except Exception:
    pass

print(
    "JARVIS: Shutting down."
)

if voice_output_enabled:

    try:
        speak(
            "Shutting down."
        )
    except Exception:
        pass