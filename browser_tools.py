import atexit
from pathlib import Path
from urllib.parse import quote_plus, urlparse

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


# ============================================================
# GLOBAL BROWSER STATE
# ============================================================

_playwright = None
_context = None
_page = None


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _profile_directory():
    path = (
        Path.home()
        / "Jarvis"
        / "browser_profile"
    )

    path.mkdir(
        parents=True,
        exist_ok=True
    )

    return path


def _ensure_browser():
    global _playwright
    global _context
    global _page

    if _context is not None:
        try:
            if _page is None or _page.is_closed():
                pages = _context.pages

                if pages:
                    _page = pages[-1]
                else:
                    _page = _context.new_page()

            return _page

        except Exception:
            _context = None
            _page = None

    _playwright = sync_playwright().start()

    profile = _profile_directory()

    _context = (
        _playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            accept_downloads=True,
            no_viewport=True,
            args=[
                "--start-maximized",
            ],
        )
    )

    pages = _context.pages

    if pages:
        _page = pages[0]
    else:
        _page = _context.new_page()

    return _page


def _normalize_url(url):
    url = url.strip()

    if not url:
        raise ValueError(
            "URL cannot be empty."
        )

    if "://" not in url:
        url = "https://" + url

    parsed = urlparse(url)

    if parsed.scheme not in {
        "http",
        "https",
    }:
        raise ValueError(
            "Only http:// and https:// URLs "
            "are supported."
        )

    return url


def _active_page():
    global _page

    page = _ensure_browser()

    try:
        pages = _context.pages

        if pages:
            # Prefer the newest visible tab.
            for candidate in reversed(pages):
                if not candidate.is_closed():
                    _page = candidate
                    break

    except Exception:
        pass

    return _page or page


def _page_summary(page):
    return {
        "title": page.title(),
        "url": page.url,
    }


# ============================================================
# BROWSER LIFECYCLE
# ============================================================

def browser_open():
    try:
        page = _ensure_browser()

        return {
            "success": True,
            **_page_summary(page),
            "message": (
                "Browser is running."
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def browser_close():
    global _playwright
    global _context
    global _page

    try:
        if _context is not None:
            _context.close()

        if _playwright is not None:
            _playwright.stop()

        _context = None
        _page = None
        _playwright = None

        return {
            "success": True,
        }

    except Exception as e:
        _context = None
        _page = None
        _playwright = None

        return {
            "success": False,
            "error": str(e),
        }


atexit.register(browser_close)


# ============================================================
# NAVIGATION
# ============================================================

def browser_navigate(url):
    try:
        page = _active_page()

        url = _normalize_url(
            url
        )

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        return {
            "success": True,
            **_page_summary(page),
        }

    except PlaywrightTimeoutError:
        try:
            page = _active_page()

            return {
                "success": True,
                **_page_summary(page),
                "warning": (
                    "Page navigation timed out, "
                    "but the page may still have loaded."
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def browser_search(query):
    try:
        page = _active_page()

        search_url = (
            "https://www.google.com/search?q="
            + quote_plus(query)
        )

        page.goto(
            search_url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        return {
            "success": True,
            "query": query,
            **_page_summary(page),
        }

    except PlaywrightTimeoutError:
        try:
            return {
                "success": True,
                "query": query,
                **_page_summary(
                    _active_page()
                ),
                "warning": (
                    "Search navigation timed out."
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def browser_back():
    try:
        page = _active_page()

        page.go_back(
            wait_until="domcontentloaded",
            timeout=15000,
        )

        return {
            "success": True,
            **_page_summary(page),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def browser_forward():
    try:
        page = _active_page()

        page.go_forward(
            wait_until="domcontentloaded",
            timeout=15000,
        )

        return {
            "success": True,
            **_page_summary(page),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def browser_reload():
    try:
        page = _active_page()

        page.reload(
            wait_until="domcontentloaded",
            timeout=15000,
        )

        return {
            "success": True,
            **_page_summary(page),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def browser_current_page():
    try:
        page = _active_page()

        return {
            "success": True,
            **_page_summary(page),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# PAGE INSPECTION
# ============================================================

def browser_inspect(
    max_elements=80,
    max_text_chars=12000
):
    try:
        page = _active_page()

        max_elements = max(
            10,
            min(
                int(max_elements),
                150
            )
        )

        max_text_chars = max(
            1000,
            min(
                int(max_text_chars),
                30000
            )
        )

        try:
            body_text = page.locator(
                "body"
            ).inner_text(
                timeout=5000
            )

        except Exception:
            body_text = ""

        if len(body_text) > max_text_chars:
            body_text = (
                body_text[
                    :max_text_chars
                ]
                + "\n...[truncated]"
            )

        selector = (
            "a, "
            "button, "
            "input, "
            "textarea, "
            "select, "
            "[role='button'], "
            "[role='link'], "
            "[role='textbox'], "
            "[contenteditable='true']"
        )

        locator = page.locator(
            selector
        )

        try:
            count = locator.count()
        except Exception:
            count = 0

        elements = []
        ref_number = 1

        for index in range(
            min(
                count,
                max_elements * 4
            )
        ):
            if len(elements) >= max_elements:
                break

            element = locator.nth(
                index
            )

            try:
                if not element.is_visible():
                    continue

                tag = element.evaluate(
                    "(el) => el.tagName.toLowerCase()"
                )

                element_type = (
                    element.get_attribute(
                        "type"
                    )
                    or ""
                )

                text = ""

                try:
                    text = (
                        element.inner_text(
                            timeout=500
                        )
                        or ""
                    )

                except Exception:
                    pass

                text = (
                    text.strip()
                    .replace(
                        "\n",
                        " "
                    )
                )

                if len(text) > 160:
                    text = (
                        text[:160]
                        + "..."
                    )

                aria_label = (
                    element.get_attribute(
                        "aria-label"
                    )
                    or ""
                )

                placeholder = (
                    element.get_attribute(
                        "placeholder"
                    )
                    or ""
                )

                name = (
                    element.get_attribute(
                        "name"
                    )
                    or ""
                )

                href = (
                    element.get_attribute(
                        "href"
                    )
                    or ""
                )

                ref = (
                    f"J{ref_number}"
                )

                element.evaluate(
                    """
                    (el, ref) => {
                        el.setAttribute(
                            'data-jarvis-ref',
                            ref
                        );
                    }
                    """,
                    ref,
                )

                elements.append({
                    "ref": ref,
                    "tag": tag,
                    "type": element_type,
                    "text": text,
                    "aria_label": aria_label,
                    "placeholder": placeholder,
                    "name": name,
                    "href": (
                        href[:500]
                        if href
                        else ""
                    ),
                })

                ref_number += 1

            except Exception:
                continue

        return {
            "success": True,
            **_page_summary(page),
            "page_text": body_text,
            "interactive_elements": elements,
            "element_count": len(elements),
            "instruction": (
                "Use the J-ref values with "
                "browser_click, browser_fill, "
                "or browser_press."
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================
# ELEMENT INTERACTION
# ============================================================

def _get_ref_locator(ref):
    page = _active_page()

    ref = ref.strip().upper()

    if not ref.startswith("J"):
        raise ValueError(
            "Invalid browser element reference."
        )

    locator = page.locator(
        f'[data-jarvis-ref="{ref}"]'
    )

    if locator.count() == 0:
        raise ValueError(
            f"Element {ref} is no longer available. "
            "Inspect the page again."
        )

    return page, locator.first


def browser_click(ref):
    try:
        page, element = (
            _get_ref_locator(
                ref
            )
        )

        text = ""

        try:
            text = (
                element.inner_text(
                    timeout=500
                )
                or ""
            ).strip()

        except Exception:
            pass

        element.click(
            timeout=10000
        )

        try:
            page.wait_for_timeout(
                500
            )
        except Exception:
            pass

        return {
            "success": True,
            "clicked": ref,
            "element_text": text[:200],
            **_page_summary(page),
            "instruction": (
                "Inspect the page again before "
                "making another visual decision."
            ),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def browser_fill(
    ref,
    text
):
    try:
        page, element = (
            _get_ref_locator(
                ref
            )
        )

        element_type = (
            element.get_attribute(
                "type"
            )
            or ""
        ).lower()

        if element_type == "password":
            return {
                "success": False,
                "error": (
                    "Jarvis does not fill password "
                    "fields automatically. Enter the "
                    "password manually, then continue."
                ),
                "sensitive_field": True,
            }

        element.fill(
            text,
            timeout=10000,
        )

        return {
            "success": True,
            "filled": ref,
            "characters": len(text),
            **_page_summary(page),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def browser_press(
    ref,
    key
):
    try:
        page, element = (
            _get_ref_locator(
                ref
            )
        )

        element.press(
            key,
            timeout=10000,
        )

        try:
            page.wait_for_timeout(
                500
            )
        except Exception:
            pass

        return {
            "success": True,
            "element": ref,
            "key": key,
            **_page_summary(page),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }