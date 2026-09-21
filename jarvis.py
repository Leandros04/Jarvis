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

from ai_router import (
    LUNA,
    route_model,
    router_status,
    set_model_override,
    get_model_override,
)

from cost_tracker import (
    record_response,
    get_cost_summary,
    format_cost_summary,
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

VOICE_RESPONSE_MAX_CHARS = 1200

CONFIRMATION_TIMEOUT_SECONDS = 90

PROMPT_CACHE_KEY = (
    "jarvis-core-v3"
)


init_memory_db()
init_scheduler_db()


# ============================================================
# TOOL HELPER
# ============================================================

def function_tool(
    name,
    description,
    properties=None
):
    properties = (
        properties
        or {}
    )

    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties":
                properties,
            "required":
                list(
                    properties.keys()
                ),
            "additionalProperties":
                False,
        },
        "strict": True,
    }


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

        route = route_model(
            (
                "Analyze a Windows screenshot. "
                + str(question)
            )
        )

        response = (
            client.responses.create(
                model=route[
                    "model"
                ],
                reasoning={
                    "effort":
                        route[
                            "effort"
                        ]
                },
                prompt_cache_key=(
                    PROMPT_CACHE_KEY
                ),
                input=[
                    {
                        "role":
                            "user",
                        "content": [
                            {
                                "type":
                                    "input_text",
                                "text": (
                                    "Examine this Windows "
                                    "desktop screenshot. "
                                    "Only use information "
                                    "actually visible. "
                                    "If locating something "
                                    "clickable, provide "
                                    "approximate center "
                                    "coordinates.\n\n"
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

        record_response(
            response,
            route["model"],
            purpose="screen_vision",
        )

        return {
            "success": True,
            "analysis":
                response.output_text,
            "model":
                route["display"],
            "screenshot":
                str(image_path),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# TOOL DEFINITIONS
# ============================================================

TOOLS = [

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

    function_tool(
        "get_screen_info",
        "Get screen size and cursor position."
    ),

    function_tool(
        "analyze_screen",
        "Visually inspect the Windows desktop.",
        {
            "question": {
                "type": "string"
            }
        },
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
    ),

    function_tool(
        "scroll_mouse",
        "Scroll the active window.",
        {
            "amount": {
                "type": "integer"
            }
        },
    ),

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
    ),

    function_tool(
        "open_application",
        "Open an installed application.",
        {
            "app_name": {
                "type": "string"
            }
        },
    ),

    function_tool(
        "list_directory",
        "List files and folders.",
        {
            "path": {
                "type": "string"
            }
        },
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
    ),

    function_tool(
        "open_file",
        "Open a file or folder.",
        {
            "path": {
                "type": "string"
            }
        },
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
    ),

    function_tool(
        "get_path_info",
        "Get information about a path.",
        {
            "path": {
                "type": "string"
            }
        },
    ),

    function_tool(
        "create_folder",
        "Create a folder.",
        {
            "path": {
                "type": "string"
            }
        },
    ),

    function_tool(
        "create_text_file",
        (
            "Create a UTF-8 text file without "
            "silently overwriting."
        ),
        {
            "path": {
                "type": "string"
            },
            "content": {
                "type": "string"
            },
        },
    ),

    function_tool(
        "copy_path",
        "Copy a file or folder.",
        {
            "source": {
                "type": "string"
            },
            "destination": {
                "type": "string"
            },
        },
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
    ),

    function_tool(
        "recycle_path",
        "Move a path to the Recycle Bin.",
        {
            "path": {
                "type": "string"
            }
        },
    ),

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
    ),

    function_tool(
        "browser_search",
        "Search the web in Jarvis Chromium.",
        {
            "query": {
                "type": "string"
            }
        },
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
    ),

    function_tool(
        "browser_click",
        "Click a webpage J-reference.",
        {
            "ref": {
                "type": "string"
            }
        },
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
    ),

    function_tool(
        "browser_back",
        "Go back one webpage."
    ),

    function_tool(
        "browser_forward",
        "Go forward one webpage."
    ),

    function_tool(
        "browser_reload",
        "Reload the webpage."
    ),

    function_tool(
        "memory_store",
        "Store persistent local memory.",
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
    ),

    function_tool(
        "memory_delete",
        "Delete persistent memory.",
        {
            "memory_id": {
                "type": "integer"
            }
        },
    ),

    function_tool(
        "get_audio_status",
        "Get master volume and mute state."
    ),

    function_tool(
        "set_volume",
        "Set master volume percentage.",
        {
            "percent": {
                "type": "number"
            }
        },
    ),

    function_tool(
        "change_volume",
        "Increase or decrease volume.",
        {
            "amount": {
                "type": "number"
            }
        },
    ),

    function_tool(
        "set_mute",
        "Set computer mute state.",
        {
            "muted": {
                "type": "boolean"
            }
        },
    ),

    function_tool(
        "media_play_pause",
        "Play or pause current media."
    ),

    function_tool(
        "media_next",
        "Skip to next track."
    ),

    function_tool(
        "media_previous",
        "Return to previous track."
    ),

    function_tool(
        "media_stop",
        "Stop current media."
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
        "Bring a window to front.",
        {
            "title_query": {
                "type": "string"
            }
        },
    ),

    function_tool(
        "minimize_window",
        "Minimize a window.",
        {
            "title_query": {
                "type": "string"
            }
        },
    ),

    function_tool(
        "maximize_window",
        "Maximize a window.",
        {
            "title_query": {
                "type": "string"
            }
        },
    ),

    function_tool(
        "restore_window",
        "Restore a window.",
        {
            "title_query": {
                "type": "string"
            }
        },
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
    ),

    function_tool(
        "get_local_datetime",
        "Get current local computer date/time."
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
    ),

    function_tool(
        "cancel_scheduled_task",
        "Cancel a timer or reminder.",
        {
            "task_id": {
                "type": "integer"
            }
        },
    ),

    function_tool(
        "list_processes",
        "List running processes.",
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
    ),

    function_tool(
        "get_process_info",
        "Get information about a PID.",
        {
            "pid": {
                "type": "integer"
            }
        },
    ),

    function_tool(
        "terminate_process",
        "Terminate a process after confirmation.",
        {
            "pid": {
                "type": "integer"
            },
            "force": {
                "type": "boolean"
            },
        },
    ),

    function_tool(
        "get_machine_info",
        "Get machine information."
    ),

    function_tool(
        "get_network_info",
        "Get network interface information."
    ),

    function_tool(
        "get_wifi_info",
        "Get Wi-Fi information."
    ),

    function_tool(
        "get_active_connections",
        "Get active network connections.",
        {
            "limit": {
                "type": "integer"
            }
        },
    ),

    function_tool(
        "run_powershell",
        "Run PowerShell after confirmation.",
        {
            "command": {
                "type": "string"
            },
            "timeout": {
                "type": "integer"
            },
        },
    ),

    function_tool(
        "power_action",
        (
            "Lock, sleep, restart, shut down, "
            "or sign out after confirmation."
        ),
        {
            "action": {
                "type": "string",
                "enum": [
                    "lock",
                    "shutdown",
                    "restart",
                    "signout",
                    "sleep",
                ]
            }
        },
    ),
]


# ============================================================
# INSTRUCTIONS
# ============================================================

INSTRUCTIONS = """
You are JARVIS, a capable personal AI assistant running on the
user's Windows computer.

Be concise for simple commands and natural in conversation.

Use tools whenever real computer state or an action is required.

Prefer structured tools over screen/mouse automation.

Do not call unnecessary tools.

FILES

Use filesystem tools for files and folders.
Do not silently overwrite files.
Use recycle_path instead of permanent deletion.

PROCESSES / ADMIN

Identify uncertain PIDs before termination.

terminate_process, run_powershell and power_action are protected
by a local confirmation broker.

If a protected operation returns requires_confirmation=true,
explain what is pending and tell the user to say "Confirm" or
"Cancel".

Do not claim the operation occurred before confirmation.

TIME

Use schedule_timer for relative timers.
For exact clock times, get the current local time when needed and
then use schedule_reminder_at.

MEMORY

Use memory_store when the user explicitly asks to remember
something durable.

Use memory_search when a question may depend on information from
a previous Jarvis session.

Never store passwords, tokens, API keys, recovery codes or payment
credentials.

BROWSER

Prefer browser DOM tools over screen-coordinate automation.

Do not automatically enter passwords.

Do not autonomously confirm purchases, financial transactions,
account deletion, or other high-consequence irreversible actions.

GENERAL

Never invent computer state.
Never claim an action succeeded unless its tool result indicates
success.
"""


# ============================================================
# DIRECT TOOL EXECUTORS
# ============================================================

EXECUTORS = {

    "get_system_status":
        lambda a:
            get_system_status(),

    "get_top_processes":
        lambda a:
            get_top_processes(),

    "get_user_paths":
        lambda a:
            get_user_paths(),

    "get_screen_info":
        lambda a:
            get_screen_info(),

    "analyze_screen":
        lambda a:
            analyze_screen(
                a["question"]
            ),

    "move_mouse":
        lambda a:
            move_mouse(
                a["x"],
                a["y"],
                a["duration"]
            ),

    "click_mouse":
        lambda a:
            click_mouse(
                a["x"],
                a["y"],
                a["button"],
                a["clicks"]
            ),

    "scroll_mouse":
        lambda a:
            scroll_mouse(
                a["amount"]
            ),

    "type_text":
        lambda a:
            type_text(
                a["text"],
                a["interval"]
            ),

    "press_key":
        lambda a:
            press_key(
                a["key"],
                a["presses"]
            ),

    "press_hotkey":
        lambda a:
            press_hotkey(
                a["keys"]
            ),

    "list_applications":
        lambda a:
            list_applications(
                a["search_term"]
            ),

    "open_application":
        lambda a:
            open_application(
                a["app_name"]
            ),

    "list_directory":
        lambda a:
            list_directory(
                a["path"]
            ),

    "find_files":
        lambda a:
            find_files(
                a["search_term"],
                a["root"]
            ),

    "open_file":
        lambda a:
            open_file(
                a["path"]
            ),

    "read_file":
        lambda a:
            read_file(
                a["path"],
                a["max_chars"],
                a["start_page"],
                a["end_page"],
            ),

    "get_path_info":
        lambda a:
            get_path_info(
                a["path"]
            ),

    "create_folder":
        lambda a:
            create_folder(
                a["path"]
            ),

    "create_text_file":
        lambda a:
            create_text_file(
                a["path"],
                a["content"]
            ),

    "copy_path":
        lambda a:
            copy_path(
                a["source"],
                a["destination"]
            ),

    "move_path":
        lambda a:
            move_path(
                a["source"],
                a["destination"]
            ),

    "rename_path":
        lambda a:
            rename_path(
                a["path"],
                a["new_name"]
            ),

    "recycle_path":
        lambda a:
            recycle_path(
                a["path"]
            ),

    "browser_open":
        lambda a:
            browser_open(),

    "browser_navigate":
        lambda a:
            browser_navigate(
                a["url"]
            ),

    "browser_search":
        lambda a:
            browser_search(
                a["query"]
            ),

    "browser_current_page":
        lambda a:
            browser_current_page(),

    "browser_inspect":
        lambda a:
            browser_inspect(
                a["max_elements"],
                a["max_text_chars"]
            ),

    "browser_click":
        lambda a:
            browser_click(
                a["ref"]
            ),

    "browser_fill":
        lambda a:
            browser_fill(
                a["ref"],
                a["text"]
            ),

    "browser_press":
        lambda a:
            browser_press(
                a["ref"],
                a["key"]
            ),

    "browser_back":
        lambda a:
            browser_back(),

    "browser_forward":
        lambda a:
            browser_forward(),

    "browser_reload":
        lambda a:
            browser_reload(),

    "memory_store":
        lambda a:
            memory_store(
                a["category"],
                a["key"],
                a["value"]
            ),

    "memory_search":
        lambda a:
            memory_search(
                a["query"],
                a["limit"]
            ),

    "memory_list":
        lambda a:
            memory_list(
                a["category"],
                a["limit"]
            ),

    "memory_delete":
        lambda a:
            memory_delete(
                a["memory_id"]
            ),

    "get_audio_status":
        lambda a:
            get_audio_status(),

    "set_volume":
        lambda a:
            set_volume(
                a["percent"]
            ),

    "change_volume":
        lambda a:
            change_volume(
                a["amount"]
            ),

    "set_mute":
        lambda a:
            set_mute(
                a["muted"]
            ),

    "media_play_pause":
        lambda a:
            media_play_pause(),

    "media_next":
        lambda a:
            media_next(),

    "media_previous":
        lambda a:
            media_previous(),

    "media_stop":
        lambda a:
            media_stop(),

    "get_clipboard":
        lambda a:
            get_clipboard(),

    "set_clipboard":
        lambda a:
            set_clipboard(
                a["text"]
            ),

    "clear_clipboard":
        lambda a:
            clear_clipboard(),

    "list_windows":
        lambda a:
            list_windows(),

    "get_active_window":
        lambda a:
            get_active_window(),

    "focus_window":
        lambda a:
            focus_window(
                a["title_query"]
            ),

    "minimize_window":
        lambda a:
            minimize_window(
                a["title_query"]
            ),

    "maximize_window":
        lambda a:
            maximize_window(
                a["title_query"]
            ),

    "restore_window":
        lambda a:
            restore_window(
                a["title_query"]
            ),

    "show_notification":
        lambda a:
            show_notification(
                a["title"],
                a["message"]
            ),

    "get_local_datetime":
        lambda a:
            get_local_datetime(),

    "schedule_timer":
        lambda a:
            schedule_timer(
                a["seconds"],
                a["message"]
            ),

    "schedule_reminder_at":
        lambda a:
            schedule_reminder_at(
                a["local_datetime"],
                a["message"],
                a["title"]
            ),

    "list_scheduled_tasks":
        lambda a:
            list_scheduled_tasks(
                a["include_completed"],
                a["limit"]
            ),

    "cancel_scheduled_task":
        lambda a:
            cancel_scheduled_task(
                a["task_id"]
            ),

    "list_processes":
        lambda a:
            list_processes(
                a["search_term"],
                a["limit"]
            ),

    "get_process_info":
        lambda a:
            get_process_info(
                a["pid"]
            ),

    "terminate_process":
        lambda a:
            terminate_process(
                a["pid"],
                a["force"]
            ),

    "get_machine_info":
        lambda a:
            get_machine_info(),

    "get_network_info":
        lambda a:
            get_network_info(),

    "get_wifi_info":
        lambda a:
            get_wifi_info(),

    "get_active_connections":
        lambda a:
            get_active_connections(
                a["limit"]
            ),

    "run_powershell":
        lambda a:
            run_powershell(
                a["command"],
                a["timeout"]
            ),

    "power_action":
        lambda a:
            power_action(
                a["action"]
            ),
}


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
    name,
    args
):
    if name == "terminate_process":

        return (
            "force kill"
            if args.get(
                "force"
            )
            else "terminate"
        ) + (
            f" process PID "
            f"{args.get('pid')}"
        )

    if name == "run_powershell":

        command = str(
            args.get(
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

    if name == "power_action":

        return (
            f"{args.get('action')} "
            f"the computer/session"
        )

    return name


def queue_confirmation(
    name,
    args
):
    global pending_action

    pending_action = {
        "tool_name":
            name,
        "arguments":
            args,
        "created_at":
            time.time(),
        "description":
            confirmation_description(
                name,
                args
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
    }


def get_pending():
    global pending_action

    if pending_action is None:
        return None

    if (
        time.time()
        - pending_action[
            "created_at"
        ]
        > CONFIRMATION_TIMEOUT_SECONDS
    ):
        pending_action = None

        return None

    return pending_action


def clear_pending():
    global pending_action

    pending_action = None


def execute_direct(
    name,
    args
):
    executor = EXECUTORS.get(
        name
    )

    if executor is None:

        return {
            "success": False,
            "error": (
                f"Unknown tool: {name}"
            ),
        }

    return executor(
        args
    )


def execute_tool(
    name,
    args
):
    if name in RISKY_TOOLS:

        return queue_confirmation(
            name,
            args
        )

    return execute_direct(
        name,
        args
    )


# ============================================================
# MODEL / OPENAI LOOP
# ============================================================

def create_response(
    model,
    effort,
    **kwargs
):
    response = (
        client.responses.create(
            model=model,
            reasoning={
                "effort":
                    effort
            },
            prompt_cache_key=(
                PROMPT_CACHE_KEY
            ),
            **kwargs
        )
    )

    return response


def run_jarvis(
    user_input,
    previous_response_id
):
    try:
        route = route_model(
            user_input
        )

        model = route[
            "model"
        ]

        effort = route[
            "effort"
        ]

        print(
            f"[MODEL: "
            f"{route['display']} | "
            f"{route['source']} | "
            f"{route['reason']}]"
        )

        request = {
            "instructions":
                INSTRUCTIONS,
            "tools":
                TOOLS,
            "input":
                user_input,
        }

        if previous_response_id:

            request[
                "previous_response_id"
            ] = previous_response_id

        try:
            response = (
                create_response(
                    model,
                    effort,
                    **request
                )
            )

        except Exception:
            # If a cross-model previous response ever
            # causes a compatibility issue, recover
            # instead of breaking Jarvis.
            if previous_response_id:

                request.pop(
                    "previous_response_id",
                    None
                )

                response = (
                    create_response(
                        model,
                        effort,
                        **request
                    )
                )

            else:
                raise

        record_response(
            response,
            model,
            purpose="assistant",
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
                    "model":
                        route[
                            "display"
                        ],
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
                        "success":
                            False,
                        "error":
                            str(e),
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
                create_response(
                    model,
                    effort,
                    instructions=(
                        INSTRUCTIONS
                    ),
                    tools=TOOLS,
                    previous_response_id=(
                        response.id
                    ),
                    input=outputs,
                )
            )

            record_response(
                response,
                model,
                purpose="tool_followup",
            )

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# SPEECH
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

    text = text[
        :VOICE_RESPONSE_MAX_CHARS
    ]

    space = text.rfind(
        " "
    )

    if space > 500:
        text = text[
            :space
        ]

    speak(
        text
        + ". The rest is in the log."
    )


# ============================================================
# ZERO-COST LOCAL COMMANDS
# ============================================================

def _seconds(
    amount,
    unit
):
    amount = float(
        amount
    )

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

    return (
        amount * 3600
    )


def local_fast_command(
    text
):
    raw = str(
        text
    ).strip()

    command = (
        raw.lower()
        .strip(".?!")
    )


    # API COST

    if command in {
        "/cost",
        "api cost",
        "api usage",
        "how much have i spent",
        "how much has jarvis cost",
        "what has jarvis cost",
    }:

        return {
            "handled": True,
            "response":
                format_cost_summary(
                    30
                ),
        }


    # ROUTER STATUS

    if command in {
        "/router",
        "router status",
        "what model are you using",
        "what ai model are you using",
    }:

        status = router_status()

        ollama = status[
            "ollama"
        ]

        return {
            "handled": True,
            "response": (
                f"Model mode is "
                f"{status['override']}. "
                f"Local Ollama router is "
                f"{'online' if ollama.get('available') else 'offline'}. "
                f"The default cloud model "
                f"is GPT-5.6 Luna."
            ),
        }


    # VOLUME

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
        "louder",
        "turn it up",
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
            ),
        }


    if command in {
        "volume down",
        "quieter",
        "turn it down",
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


    # MEDIA

    if command in {
        "pause",
        "pause music",
        "pause the music",
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
    }:

        media_previous()

        return {
            "handled": True,
            "response": "Done.",
        }


    # TIMER

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

        unit = match.group(
            2
        )

        result = schedule_timer(
            _seconds(
                amount,
                unit
            ),
            (
                f"Your {amount:g} "
                f"{unit} timer "
                f"is finished."
            ),
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


    # REMIND ME IN

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

        unit = match.group(
            2
        )

        message = (
            match.group(3)
            .strip()
        )

        result = schedule_timer(
            _seconds(
                amount,
                unit
            ),
            message,
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

def meta_command(
    text
):
    command = (
        str(text)
        .strip()
        .lower()
        .strip(".?!")
    )


    if command in {
        "/auto",
        "automatic model",
        "auto model",
    }:
        return {
            "type": "model",
            "mode": "auto",
        }


    if command in {
        "/luna",
        "use luna",
    }:
        return {
            "type": "model",
            "mode": "luna",
        }


    if command in {
        "/terra",
        "use terra",
    }:
        return {
            "type": "model",
            "mode": "terra",
        }


    if command in {
        "/sol",
        "use sol",
    }:
        return {
            "type": "model",
            "mode": "sol",
        }


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
# REMINDERS
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

status = router_status()

print(
    "Model router: AUTO"
)

print(
    "Default AI: GPT-5.6 Luna"
)

print(
    "Local Qwen router: "
    + (
        "ONLINE"
        if status[
            "ollama"
        ].get(
            "available"
        )
        else "OFFLINE - fallback router active"
    )
)

print(
    "API cost tracking: ENABLED"
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

            action = meta[
                "type"
            ]


            if action == "shutdown":

                running = False
                break


            if action == "model":

                set_model_override(
                    meta["mode"]
                )

                previous_response_id = (
                    None
                )

                response_text = (
                    f"Model mode set to "
                    f"{meta['mode']}."
                )

                print(
                    f"JARVIS: "
                    f"{response_text}"
                )

                if (
                    input_mode != "text"
                    and voice_output_enabled
                ):
                    speak(
                        response_text
                    )

                continue


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

                clear_pending()

                print(
                    "Conversation reset."
                )

                continue


            if action == "cancel_pending":

                pending = get_pending()

                if pending:

                    description = (
                        pending[
                            "description"
                        ]
                    )

                    clear_pending()

                    response_text = (
                        f"Cancelled: "
                        f"{description}."
                    )

                else:

                    response_text = (
                        "There is no pending "
                        "action to cancel."
                    )

                print(
                    f"JARVIS: "
                    f"{response_text}"
                )

                if (
                    input_mode != "text"
                    and voice_output_enabled
                ):
                    speak(
                        response_text
                    )

                continue


            if action == "confirm_pending":

                pending = get_pending()

                if not pending:

                    response_text = (
                        "There is no pending "
                        "action to confirm, "
                        "or it expired."
                    )

                else:

                    clear_pending()

                    result = (
                        execute_direct(
                            pending[
                                "tool_name"
                            ],
                            pending[
                                "arguments"
                            ],
                        )
                    )

                    previous_response_id = (
                        None
                    )

                    if result.get(
                        "success"
                    ):

                        response_text = (
                            "Confirmed and executed: "
                            + pending[
                                "description"
                            ]
                            + "."
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
                            f"The confirmed action "
                            f"failed: {error}"
                        )

                print(
                    f"JARVIS: "
                    f"{response_text}"
                )

                if (
                    input_mode != "text"
                    and voice_output_enabled
                ):
                    speak(
                        response_text
                    )

                continue


        # ====================================================
        # FREE LOCAL FAST PATH
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


        previous_response_id = (
            result[
                "response_id"
            ]
        )

        response_text = (
            result[
                "text"
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