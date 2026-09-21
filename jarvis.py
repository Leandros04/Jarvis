import base64
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


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

from memory_tools import (
    init_memory_db,
    memory_store,
    memory_search,
    memory_list,
    memory_delete,
)

from voice_tools import (
    listen_and_transcribe,
    speak,
)

from wakeword_tools import (
    wait_for_wakeword,
    load_wakeword_model,
)

from desktop_tools import (
    get_audio_status,
    set_volume,
    change_volume,
    set_mute,
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

from scheduler_tools import (
    init_scheduler_db,
    get_local_datetime,
    schedule_timer,
    schedule_reminder_at,
    list_scheduled_tasks,
    cancel_scheduled_task,
    JarvisScheduler,
)

from admin_tools import (
    get_path_info,
    create_folder,
    create_text_file,
    copy_path,
    move_path,
    rename_path,
    recycle_path,
    list_processes,
    get_process_info,
    terminate_process,
    get_machine_info,
    get_network_info,
    get_wifi_info,
    get_active_connections,
    run_powershell,
    power_action,
)


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

client = OpenAI(
    api_key=os.getenv(
        "OPENAI_API_KEY"
    )
)

MODEL = "gpt-5.5"

VOICE_RESPONSE_MAX_CHARS = 1200

CONFIRMATION_TIMEOUT_SECONDS = 90


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
                                "type":
                                    "input_text",
                                "text": (
                                    "Examine the user's "
                                    "current Windows desktop "
                                    "screenshot.\n"
                                    "Only use information "
                                    "actually visible.\n"
                                    "If locating something "
                                    "clickable, give approximate "
                                    "center pixel coordinates.\n\n"
                                    f"Question: {question}"
                                ),
                            },
                            {
                                "type":
                                    "input_image",
                                "image_url": (
                                    "data:image/png;base64,"
                                    + encoded
                                ),
                                "detail":
                                    "high",
                            },
                        ],
                    }
                ],
            )
        )

        return {
            "success": True,
            "analysis":
                response.output_text,
            "screenshot":
                str(image_path),
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# TOOL HELPER
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
            "properties":
                properties or {},
            "required":
                required or [],
            "additionalProperties":
                False,
        },
        "strict": True,
    }


# ============================================================
# TOOLS
# ============================================================

TOOLS = [

    function_tool(
        "get_system_status",
        "Get current CPU, RAM and disk usage."
    ),

    function_tool(
        "get_top_processes",
        "Get processes using the most RAM."
    ),

    function_tool(
        "get_user_paths",
        "Get standard Windows user folders."
    ),

    function_tool(
        "get_screen_info",
        "Get screen dimensions and cursor position."
    ),

    function_tool(
        "analyze_screen",
        "Visually inspect the Windows desktop.",
        {
            "question": {
                "type": "string"
            }
        },
        [
            "question"
        ],
    ),

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

    function_tool(
        "type_text",
        "Type text into the focused application.",
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


    # ========================================================
    # FILES
    # ========================================================

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
        "Search recursively for files.",
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

    function_tool(
        "get_path_info",
        "Get information about a file or folder.",
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
        "create_folder",
        "Create a new folder.",
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
        "create_text_file",
        (
            "Create a new UTF-8 text file. "
            "Existing files are not overwritten."
        ),
        {
            "path": {
                "type": "string"
            },
            "content": {
                "type": "string"
            },
        },
        [
            "path",
            "content"
        ],
    ),

    function_tool(
        "copy_path",
        (
            "Copy a file or folder without "
            "overwriting existing destinations."
        ),
        {
            "source": {
                "type": "string"
            },
            "destination": {
                "type": "string"
            },
        },
        [
            "source",
            "destination"
        ],
    ),

    function_tool(
        "move_path",
        "Move a file or folder.",
        {
            "source": {
                "type": "string"
            },
            "destination": {
                "type": "string"
            },
        },
        [
            "source",
            "destination"
        ],
    ),

    function_tool(
        "rename_path",
        "Rename a file or folder.",
        {
            "path": {
                "type": "string"
            },
            "new_name": {
                "type": "string"
            },
        },
        [
            "path",
            "new_name"
        ],
    ),

    function_tool(
        "recycle_path",
        (
            "Move a file or folder to the "
            "Windows Recycle Bin."
        ),
        {
            "path": {
                "type": "string"
            }
        },
        [
            "path"
        ],
    ),


    # ========================================================
    # BROWSER
    # ========================================================

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
        "Inspect webpage text and controls.",
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
        "Press a key on a webpage element.",
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
        "Go back one page."
    ),

    function_tool(
        "browser_forward",
        "Go forward one page."
    ),

    function_tool(
        "browser_reload",
        "Reload the current webpage."
    ),


    # ========================================================
    # MEMORY
    # ========================================================

    function_tool(
        "memory_store",
        "Store persistent memory.",
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
        "Delete persistent memory.",
        {
            "memory_id": {
                "type": "integer"
            }
        },
        [
            "memory_id"
        ],
    ),


    # ========================================================
    # AUDIO / DESKTOP
    # ========================================================

    function_tool(
        "get_audio_status",
        "Get Windows audio status."
    ),

    function_tool(
        "set_volume",
        "Set Windows master volume.",
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
        "Change Windows master volume.",
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
        "Play or pause media."
    ),

    function_tool(
        "media_next",
        "Next media track."
    ),

    function_tool(
        "media_previous",
        "Previous media track."
    ),

    function_tool(
        "media_stop",
        "Stop media."
    ),

    function_tool(
        "get_clipboard",
        "Read plaintext clipboard."
    ),

    function_tool(
        "set_clipboard",
        "Set plaintext clipboard.",
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
        "Clear clipboard."
    ),

    function_tool(
        "list_windows",
        "List open windows."
    ),

    function_tool(
        "get_active_window",
        "Get active window."
    ),

    function_tool(
        "focus_window",
        "Bring a window to the foreground.",
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


    # ========================================================
    # SCHEDULER
    # ========================================================

    function_tool(
        "get_local_datetime",
        "Get exact local computer time."
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
        "Create an exact-time reminder.",
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
        "List timers and reminders.",
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
        "Cancel a timer or reminder.",
        {
            "task_id": {
                "type": "integer"
            }
        },
        [
            "task_id"
        ],
    ),


    # ========================================================
    # PROCESS / NETWORK / ADMIN
    # ========================================================

    function_tool(
        "list_processes",
        "List running Windows processes.",
        {
            "search_term": {
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
            "search_term",
            "limit"
        ],
    ),

    function_tool(
        "get_process_info",
        "Get process information by PID.",
        {
            "pid": {
                "type": "integer"
            }
        },
        [
            "pid"
        ],
    ),

    function_tool(
        "terminate_process",
        (
            "Terminate a process. "
            "Requires local user confirmation."
        ),
        {
            "pid": {
                "type": "integer"
            },
            "force": {
                "type": "boolean"
            },
        },
        [
            "pid",
            "force"
        ],
    ),

    function_tool(
        "get_machine_info",
        "Get local machine information."
    ),

    function_tool(
        "get_network_info",
        "Get network interface information."
    ),

    function_tool(
        "get_wifi_info",
        "Get current Wi-Fi information."
    ),

    function_tool(
        "get_active_connections",
        "List active network connections.",
        {
            "limit": {
                "type": "integer"
            }
        },
        [
            "limit"
        ],
    ),

    function_tool(
        "run_powershell",
        (
            "Run PowerShell. "
            "Requires explicit local confirmation."
        ),
        {
            "command": {
                "type": "string"
            },
            "timeout": {
                "type": "integer"
            },
        },
        [
            "command",
            "timeout"
        ],
    ),

    function_tool(
        "power_action",
        (
            "Lock, shutdown, restart, sign out, "
            "or sleep the computer. "
            "Requires explicit confirmation."
        ),
        {
            "action": {
                "type": "string",
                "enum": [
                    "lock",
                    "shutdown",
                    "restart",
                    "signout",
                    "sleep"
                ]
            }
        },
        [
            "action"
        ],
    ),
]


# ============================================================
# INSTRUCTIONS
# ============================================================

INSTRUCTIONS = """
You are JARVIS, a personal AI assistant running on the user's
Windows computer.

Be concise for simple commands.

Use tools whenever real computer state or a computer action
is required.

Prefer the cheapest and most direct reliable route.

FILES

Use filesystem tools for reading, searching, creating, moving,
copying and renaming files.

Ordinary file operations refuse silent overwrites.

recycle_path moves files/folders to the Windows Recycle Bin
instead of permanently deleting them.

Direct writes to Windows and Program Files are intentionally
blocked. Deliberate system-level modifications should use
run_powershell.

PROCESSES

If the process PID is uncertain, identify it first using
list_processes.

terminate_process is confirmation-gated.

POWERSHELL / POWER

run_powershell, terminate_process and power_action are handled
by a local confirmation broker.

When one returns requires_confirmation=true, clearly describe
what is pending and tell the user to say:

"Confirm"

or:

"Cancel"

Do not claim the action happened before confirmation.

TIME

Use schedule_timer for relative timers.

Use get_local_datetime and schedule_reminder_at for specific
clock times and dates.

MEMORY

Use memory_store when the user explicitly asks you to remember
something useful long-term.

Never store passwords, API keys, tokens, card information,
recovery codes or other credentials.

BROWSER

Prefer Playwright browser tools for ordinary websites.

Do not automatically enter passwords.

Do not autonomously confirm purchases, financial transactions,
account deletion, or other high-consequence irreversible actions.

WINDOWS

Prefer structured/local tools before screen-coordinate automation.

Only use screen vision and mouse/keyboard automation when a
structured tool cannot accomplish the task.

Never claim an action succeeded unless the tool result says it did.
"""


# ============================================================
# CONFIRMATION BROKER
# ============================================================

RISKY_TOOLS = {
    "terminate_process",
    "run_powershell",
    "power_action",
}

pending_action = None


def confirmation_description(
    tool_name,
    arguments
):

    if tool_name == "terminate_process":

        mode = (
            "force kill"
            if arguments.get(
                "force"
            )
            else "terminate"
        )

        return (
            f"{mode} process PID "
            f"{arguments.get('pid')}"
        )

    if tool_name == "run_powershell":

        command = str(
            arguments.get(
                "command",
                ""
            )
        )

        if len(command) > 180:

            command = (
                command[:180]
                + "..."
            )

        return (
            f"run PowerShell: "
            f"{command}"
        )

    if tool_name == "power_action":

        return (
            f"{arguments.get('action')} "
            f"the Windows session/computer"
        )

    return tool_name


def queue_confirmation(
    tool_name,
    arguments
):

    global pending_action

    pending_action = {
        "tool_name": tool_name,
        "arguments": arguments,
        "created_at": time.time(),
        "description":
            confirmation_description(
                tool_name,
                arguments
            ),
    }

    return {
        "success": False,
        "requires_confirmation":
            True,
        "description":
            pending_action[
                "description"
            ],
        "expires_in_seconds":
            CONFIRMATION_TIMEOUT_SECONDS,
        "message": (
            "The user must explicitly "
            "say Confirm before this "
            "action executes."
        ),
    }


def get_valid_pending_action():

    global pending_action

    if pending_action is None:
        return None

    age = (
        time.time()
        - pending_action[
            "created_at"
        ]
    )

    if (
        age
        > CONFIRMATION_TIMEOUT_SECONDS
    ):

        pending_action = None

        return None

    return pending_action


def clear_pending_action():

    global pending_action

    pending_action = None


# ============================================================
# TOOL EXECUTION
# ============================================================

def execute_tool_direct(
    name,
    a
):

    no_args = {

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

        "get_machine_info":
            get_machine_info,

        "get_network_info":
            get_network_info,

        "get_wifi_info":
            get_wifi_info,
    }

    if name in no_args:

        return (
            no_args[
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
            a["clicks"]
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
            a["end_page"]
        )


    if name == "get_path_info":

        return get_path_info(
            a["path"]
        )


    if name == "create_folder":

        return create_folder(
            a["path"]
        )


    if name == "create_text_file":

        return create_text_file(
            a["path"],
            a["content"]
        )


    if name == "copy_path":

        return copy_path(
            a["source"],
            a["destination"]
        )


    if name == "move_path":

        return move_path(
            a["source"],
            a["destination"]
        )


    if name == "rename_path":

        return rename_path(
            a["path"],
            a["new_name"]
        )


    if name == "recycle_path":

        return recycle_path(
            a["path"]
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


    if name == "list_processes":

        return list_processes(
            a["search_term"],
            a["limit"]
        )


    if name == "get_process_info":

        return get_process_info(
            a["pid"]
        )


    if name == "terminate_process":

        return terminate_process(
            a["pid"],
            a["force"]
        )


    if name == "get_active_connections":

        return get_active_connections(
            a["limit"]
        )


    if name == "run_powershell":

        return run_powershell(
            a["command"],
            a["timeout"]
        )


    if name == "power_action":

        return power_action(
            a["action"]
        )


    return {
        "success": False,
        "error": (
            f"Unknown tool: {name}"
        ),
    }


def execute_tool(
    name,
    arguments
):

    if name in RISKY_TOOLS:

        return queue_confirmation(
            name,
            arguments
        )

    return execute_tool_direct(
        name,
        arguments
    )


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
                    "text":
                        response.output_text,
                    "response_id":
                        response.id,
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

                    result = (
                        execute_tool(
                            call.name,
                            args
                        )
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
# SPEECH
# ============================================================

def speak_response(text):

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
# LOCAL FAST COMMANDS
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


def local_fast_command(text):

    raw = str(
        text
    ).strip()

    command = raw.lower()


    match = re.fullmatch(
        r"(?:set\s+)?(?:the\s+)?"
        r"volume(?:\s+to)?\s+"
        r"(\d{1,3})"
        r"(?:\s*(?:%|percent))?",
        command
    )

    if match:

        result = set_volume(
            int(
                match.group(1)
            )
        )

        if result.get(
            "success"
        ):

            return {
                "handled": True,
                "response": (
                    f"Volume set to "
                    f"{result['volume_percent']:.0f} "
                    f"percent."
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
                f"Volume "
                f"{result.get('volume_percent', '')} "
                f"percent."
                if result.get(
                    "success"
                )
                else (
                    "I couldn't change "
                    "the volume."
                )
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
                f"Volume "
                f"{result.get('volume_percent', '')} "
                f"percent."
                if result.get(
                    "success"
                )
                else (
                    "I couldn't change "
                    "the volume."
                )
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


    if command in {
        "pause",
        "pause music",
        "pause the music",
        "play",
        "play music",
        "resume",
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
    }:

        media_previous()

        return {
            "handled": True,
            "response": "Done.",
        }


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

        result = schedule_timer(
            seconds_from_unit(
                amount,
                unit
            ),
            (
                f"Your {amount:g} "
                f"{unit} timer "
                f"is finished."
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


    match = re.fullmatch(
        r"remind me in\s+"
        r"(\d+(?:\.\d+)?)\s*"
        r"(seconds?|minutes?|hours?)"
        r"\s+to\s+(.+)",
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

        result = schedule_timer(
            seconds_from_unit(
                amount,
                unit
            ),
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


    return {
        "handled": False
    }


# ============================================================
# META COMMANDS
# ============================================================

def meta_command(text):

    command = (
        str(text)
        .strip()
        .lower()
        .strip(".?!")
    )


    if command in {
        "confirm",
        "yes confirm",
        "confirm it",
        "do it",
    }:

        return {
            "type":
                "confirm_pending"
        }


    if command in {
        "cancel",
        "cancel it",
        "never mind",
        "nevermind",
        "don't do it",
        "do not do it",
    }:

        return {
            "type":
                "cancel_pending"
        }


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
            "type":
                "speech_mute"
        }


    if command in {
        "/unmute",
        "unmute yourself",
    }:

        return {
            "type":
                "speech_unmute"
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

def reminder_fired(task):

    print()
    print(
        f"[REMINDER] "
        f"{task['message']}"
    )
    print()

    if voice_output_enabled:

        try:

            speak(
                task[
                    "message"
                ]
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
    "Wake phrase: Hey Jarvis"
)

print(
    "Persistent memory/reminders: ENABLED"
)

print(
    "Desktop/browser/file control: ENABLED"
)

print(
    "Network/process tools: ENABLED"
)

print(
    "Admin confirmation broker: ENABLED"
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


        else:

            user_input = input(
                "You: "
            ).strip()


        if not user_input:

            continue


        # ====================================================
        # META
        # ====================================================

        meta = meta_command(
            user_input
        )

        if meta:

            action = (
                meta["type"]
            )


            if action == "shutdown":

                running = False

                break


            if action == "mode":

                input_mode = (
                    meta["mode"]
                )

                print(
                    f"Mode: "
                    f"{input_mode}"
                )

                continue


            if action == "speech_mute":

                voice_output_enabled = (
                    False
                )

                print(
                    "Voice output muted."
                )

                continue


            if action == "speech_unmute":

                voice_output_enabled = (
                    True
                )

                speak(
                    "Voice output enabled."
                )

                continue


            if action == "reset":

                previous_response_id = (
                    None
                )

                clear_pending_action()

                print(
                    "Conversation reset."
                )

                continue


            if action == "cancel_pending":

                pending = (
                    get_valid_pending_action()
                )

                if pending:

                    description = (
                        pending[
                            "description"
                        ]
                    )

                    clear_pending_action()

                    previous_response_id = (
                        None
                    )

                    response_text = (
                        f"Cancelled: "
                        f"{description}."
                    )

                else:

                    response_text = (
                        "There is no pending "
                        "action to cancel."
                    )

                print()
                print(
                    f"JARVIS: "
                    f"{response_text}"
                )
                print()

                if (
                    input_mode != "text"
                    and voice_output_enabled
                ):

                    speak(
                        response_text
                    )

                continue


            if action == "confirm_pending":

                pending = (
                    get_valid_pending_action()
                )

                if not pending:

                    response_text = (
                        "There is no pending "
                        "action to confirm, "
                        "or it expired."
                    )

                else:

                    tool_name = (
                        pending[
                            "tool_name"
                        ]
                    )

                    args = (
                        pending[
                            "arguments"
                        ]
                    )

                    description = (
                        pending[
                            "description"
                        ]
                    )

                    clear_pending_action()

                    result = (
                        execute_tool_direct(
                            tool_name,
                            args
                        )
                    )

                    previous_response_id = (
                        None
                    )

                    if result.get(
                        "success"
                    ):

                        response_text = (
                            f"Confirmed and executed: "
                            f"{description}."
                        )

                    else:

                        error = (
                            result.get(
                                "error"
                            )
                            or result.get(
                                "stderr"
                            )
                            or "unknown error"
                        )

                        response_text = (
                            f"I tried to execute it, "
                            f"but it failed: {error}"
                        )

                print()
                print(
                    f"JARVIS: "
                    f"{response_text}"
                )
                print()

                if (
                    input_mode != "text"
                    and voice_output_enabled
                ):

                    speak(
                        response_text
                    )

                continue


        # ====================================================
        # FREE LOCAL COMMANDS
        # ====================================================

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
                input_mode != "text"
                and voice_output_enabled
            ):

                speak(
                    response_text
                )

            continue


        # ====================================================
        # AI
        # ====================================================

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
            input_mode != "text"
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