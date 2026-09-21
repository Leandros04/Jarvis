import ctypes
from ctypes import wintypes

import pygetwindow as gw
import pyperclip

from pycaw.pycaw import AudioUtilities
from winotify import Notification


# ============================================================
# WINDOWS MEDIA KEY CONSTANTS
# ============================================================

VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.windll.user32


# ============================================================
# AUDIO
# ============================================================

def _get_speaker_device():
    return AudioUtilities.GetSpeakers()


def get_audio_status():
    try:
        device = _get_speaker_device()
        endpoint = device.EndpointVolume

        try:
            volume_percent = float(
                device.volume_percent
            )

        except Exception:
            volume_percent = (
                endpoint.GetMasterVolumeLevelScalar()
                * 100
            )

        return {
            "success": True,
            "device": getattr(
                device,
                "FriendlyName",
                "Default output device"
            ),
            "volume_percent": round(
                volume_percent,
                1
            ),
            "muted": bool(
                endpoint.GetMute()
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def set_volume(percent):
    try:
        percent = float(percent)

        percent = max(
            0.0,
            min(
                percent,
                100.0
            )
        )

        device = _get_speaker_device()
        endpoint = device.EndpointVolume

        try:
            device.volume_percent = (
                percent
            )

        except Exception:
            endpoint.SetMasterVolumeLevelScalar(
                percent / 100.0,
                None
            )

        return {
            "success": True,
            "volume_percent": round(
                percent,
                1
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def change_volume(amount):
    try:
        status = get_audio_status()

        if not status.get(
            "success"
        ):
            return status

        new_volume = (
            status[
                "volume_percent"
            ]
            + float(amount)
        )

        return set_volume(
            new_volume
        )

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def set_mute(muted):
    try:
        device = _get_speaker_device()
        endpoint = device.EndpointVolume

        endpoint.SetMute(
            1 if muted else 0,
            None
        )

        return {
            "success": True,
            "muted": bool(muted),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def toggle_mute():
    try:
        device = _get_speaker_device()
        endpoint = device.EndpointVolume

        current = bool(
            endpoint.GetMute()
        )

        endpoint.SetMute(
            0 if current else 1,
            None
        )

        return {
            "success": True,
            "muted": not current,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# MEDIA PLAYBACK
# ============================================================

def _press_media_key(
    virtual_key
):
    try:
        user32.keybd_event(
            virtual_key,
            0,
            0,
            0
        )

        user32.keybd_event(
            virtual_key,
            0,
            KEYEVENTF_KEYUP,
            0
        )

        return {
            "success": True
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def media_play_pause():
    result = _press_media_key(
        VK_MEDIA_PLAY_PAUSE
    )

    if result.get(
        "success"
    ):
        result[
            "action"
        ] = "play_pause"

    return result


def media_next():
    result = _press_media_key(
        VK_MEDIA_NEXT_TRACK
    )

    if result.get(
        "success"
    ):
        result[
            "action"
        ] = "next_track"

    return result


def media_previous():
    result = _press_media_key(
        VK_MEDIA_PREV_TRACK
    )

    if result.get(
        "success"
    ):
        result[
            "action"
        ] = "previous_track"

    return result


def media_stop():
    result = _press_media_key(
        VK_MEDIA_STOP
    )

    if result.get(
        "success"
    ):
        result[
            "action"
        ] = "stop"

    return result


# ============================================================
# CLIPBOARD
# ============================================================

def get_clipboard():
    try:
        text = pyperclip.paste()

        return {
            "success": True,
            "text": text,
            "characters": len(
                text
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def set_clipboard(text):
    try:
        text = str(
            text
        )

        pyperclip.copy(
            text
        )

        return {
            "success": True,
            "characters": len(
                text
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def clear_clipboard():
    try:
        pyperclip.copy(
            ""
        )

        return {
            "success": True
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# WINDOW INFORMATION
# ============================================================

def list_windows():
    try:
        results = []

        for window in gw.getAllWindows():

            try:
                title = (
                    window.title
                    or ""
                ).strip()

                if not title:
                    continue

                results.append({
                    "title": title,
                    "left": window.left,
                    "top": window.top,
                    "width": window.width,
                    "height": window.height,
                    "minimized": bool(
                        window.isMinimized
                    ),
                    "maximized": bool(
                        window.isMaximized
                    ),
                    "active": bool(
                        window.isActive
                    ),
                })

            except Exception:
                continue

        return {
            "success": True,
            "count": len(
                results
            ),
            "windows": results,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_active_window():
    try:
        window = (
            gw.getActiveWindow()
        )

        if window is None:
            return {
                "success": False,
                "error": (
                    "No active window "
                    "was detected."
                ),
            }

        return {
            "success": True,
            "title": (
                window.title
                or ""
            ),
            "left": window.left,
            "top": window.top,
            "width": window.width,
            "height": window.height,
            "minimized": bool(
                window.isMinimized
            ),
            "maximized": bool(
                window.isMaximized
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def _find_window(
    title_query
):
    title_query = (
        str(title_query)
        .strip()
        .lower()
    )

    if not title_query:
        return None

    windows = []

    for window in gw.getAllWindows():

        try:
            title = (
                window.title
                or ""
            ).strip()

            if not title:
                continue

            if (
                title.lower()
                == title_query
            ):
                return window

            if (
                title_query
                in title.lower()
            ):
                windows.append(
                    window
                )

        except Exception:
            continue

    if windows:
        return windows[0]

    return None


def focus_window(
    title_query
):
    try:
        window = _find_window(
            title_query
        )

        if window is None:
            return {
                "success": False,
                "error": (
                    "No window matching "
                    f"'{title_query}' was found."
                ),
            }

        if window.isMinimized:
            window.restore()

        try:
            window.activate()

        except Exception:
            hwnd = getattr(
                window,
                "_hWnd",
                None
            )

            if hwnd:
                user32.ShowWindow(
                    hwnd,
                    9
                )

                user32.SetForegroundWindow(
                    hwnd
                )

            else:
                raise

        return {
            "success": True,
            "title": window.title,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def minimize_window(
    title_query
):
    try:
        window = _find_window(
            title_query
        )

        if window is None:
            return {
                "success": False,
                "error": (
                    "Matching window "
                    "was not found."
                ),
            }

        window.minimize()

        return {
            "success": True,
            "title": window.title,
            "state": "minimized",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def maximize_window(
    title_query
):
    try:
        window = _find_window(
            title_query
        )

        if window is None:
            return {
                "success": False,
                "error": (
                    "Matching window "
                    "was not found."
                ),
            }

        window.maximize()

        return {
            "success": True,
            "title": window.title,
            "state": "maximized",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def restore_window(
    title_query
):
    try:
        window = _find_window(
            title_query
        )

        if window is None:
            return {
                "success": False,
                "error": (
                    "Matching window "
                    "was not found."
                ),
            }

        window.restore()

        return {
            "success": True,
            "title": window.title,
            "state": "restored",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# WINDOWS NOTIFICATIONS
# ============================================================

def show_notification(
    title,
    message
):
    try:
        title = str(
            title
        ).strip()

        message = str(
            message
        ).strip()

        if not title:
            title = "JARVIS"

        notification = Notification(
            app_id="JARVIS",
            title=title,
            msg=message,
        )

        notification.show()

        return {
            "success": True,
            "title": title,
            "message": message,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# TEST MODE
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "=========================================="
    )
    print(
        "       JARVIS DESKTOP TOOLS TEST"
    )
    print(
        "=========================================="
    )
    print()

    print(
        "Audio:"
    )

    print(
        get_audio_status()
    )

    print()

    print(
        "Active window:"
    )

    print(
        get_active_window()
    )

    print()

    print(
        "Clipboard:"
    )

    print(
        get_clipboard()
    )

    print()

    print(
        "Commands:"
    )

    print(
        "  volume 30"
    )
    print(
        "  louder"
    )
    print(
        "  quieter"
    )
    print(
        "  mute"
    )
    print(
        "  play"
    )
    print(
        "  next"
    )
    print(
        "  previous"
    )
    print(
        "  windows"
    )
    print(
        "  clipboard"
    )
    print(
        "  notify"
    )
    print(
        "  exit"
    )

    while True:

        command = input(
            "\nTest> "
        ).strip()

        lower = command.lower()

        if lower in {
            "exit",
            "quit"
        }:
            break

        if lower.startswith(
            "volume "
        ):

            try:
                amount = float(
                    command.split(
                        " ",
                        1
                    )[1]
                )

                print(
                    set_volume(
                        amount
                    )
                )

            except Exception as e:
                print(
                    e
                )

            continue

        if lower == "louder":

            print(
                change_volume(
                    10
                )
            )

            continue

        if lower == "quieter":

            print(
                change_volume(
                    -10
                )
            )

            continue

        if lower == "mute":

            print(
                toggle_mute()
            )

            continue

        if lower == "play":

            print(
                media_play_pause()
            )

            continue

        if lower == "next":

            print(
                media_next()
            )

            continue

        if lower == "previous":

            print(
                media_previous()
            )

            continue

        if lower == "windows":

            result = list_windows()

            if not result.get(
                "success"
            ):
                print(
                    result
                )

                continue

            for window in result[
                "windows"
            ]:

                marker = (
                    "*"
                    if window[
                        "active"
                    ]
                    else " "
                )

                print(
                    f"{marker} "
                    f"{window['title']}"
                )

            continue

        if lower == "clipboard":

            print(
                get_clipboard()
            )

            continue

        if lower == "notify":

            print(
                show_notification(
                    "JARVIS",
                    "Desktop tools are online."
                )
            )

            continue

        print(
            "Unknown test command."
        )