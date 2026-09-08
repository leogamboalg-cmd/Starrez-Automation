"""Recognize StarRez and locate controls on any Windows monitor."""

import ctypes
from contextlib import contextmanager
from ctypes import wintypes
from pathlib import Path

import cv2
import numpy as np
import pyautogui
from pyscreeze import Box, ImageNotFoundException as ScreenImageNotFound
from PIL import Image, ImageGrab


STARREZ_URL = "https://cpp.starrezhousing.com/StarRezWeb/main/directory#"
ASSET_DIR = Path(__file__).resolve().parent
ADDRESS_CONFIDENCE = 0.70
IMAGE_SCALES = (1.0, 0.9, 1.1, 0.8, 1.2, 1.25, 1.5, 1.75, 2.0, 2 / 3)


@contextmanager
def physical_screen_coordinates():
    """Keep Windows lookups and mouse operations in screenshot pixel units."""
    set_context = getattr(ctypes.windll.user32, "SetThreadDpiAwarenessContext", None)
    previous = None
    if set_context is not None:
        set_context.argtypes = [wintypes.HANDLE]
        set_context.restype = wintypes.HANDLE
        previous = set_context(wintypes.HANDLE(-4))  # PER_MONITOR_AWARE_V2
    try:
        yield
    finally:
        if previous:
            set_context(previous)


@physical_screen_coordinates()
def capture_desktop():
    user32 = ctypes.windll.user32
    return (ImageGrab.grab(all_screens=True),
            user32.GetSystemMetrics(76), user32.GetSystemMetrics(77))


def find_address_links(diagnostics=None):
    """Match either address-bar theme, allowing common display scaling sizes."""
    screenshot, origin_x, origin_y = capture_desktop()
    haystack = cv2.cvtColor(np.array(screenshot.convert("RGB")), cv2.COLOR_RGB2GRAY)
    loaded = False
    candidates = []
    for filename in ("link.png", "whiteLink.png"):
        try:
            with Image.open(ASSET_DIR / filename) as image:
                template = image.convert("RGB")
        except OSError:
            continue
        loaded = True
        for scale in IMAGE_SCALES:
            size = (round(template.width * scale), round(template.height * scale))
            if size[0] > screenshot.width or size[1] > screenshot.height:
                continue
            resized = template if scale == 1 else template.resize(size, Image.Resampling.LANCZOS)
            needle = cv2.cvtColor(np.array(resized), cv2.COLOR_RGB2GRAY)
            scores = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)
            if diagnostics is not None:
                diagnostics["best_score"] = max(diagnostics.get("best_score", 0), float(scores.max()))
            # Rank matches rather than accepting the first text found on a screen.
            for _ in range(5):
                _, score, _, (left, top) = cv2.minMaxLoc(scores)
                if score < ADDRESS_CONFIDENCE:
                    break
                candidates.append((score, Box(left + origin_x, top + origin_y, *size)))
                # Suppress neighboring matches of this same address.
                scores[max(0, top - size[1] // 2):top + size[1] // 2 + 1,
                       max(0, left - size[0] // 2):left + size[0] // 2 + 1] = -1
    if not loaded:
        raise OSError("Add link.png or whiteLink.png to the app's folder so we can recognize the StarRez address.")
    for _, box in sorted(candidates, key=lambda item: item[0], reverse=True):
        yield box


@physical_screen_coordinates()
def window_region_at(box):
    """Find the window containing a visible address, regardless of monitor/focus."""
    # ImageGrab uses physical pixels. WindowFromPoint/GetWindowRect must use
    # the same coordinate space on machines with mixed display scaling.
    user32 = ctypes.windll.user32
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    point = wintypes.POINT(box.left + box.width // 2, box.top + box.height // 2)
    handle = user32.WindowFromPoint(point)
    if not handle:
        return None
    handle = user32.GetAncestor(handle, 2)  # GA_ROOT
    rectangle = wintypes.RECT()
    if not handle or not user32.GetWindowRect(handle, ctypes.byref(rectangle)):
        return None
    return (rectangle.left, rectangle.top,
            rectangle.right - rectangle.left, rectangle.bottom - rectangle.top)


def locate_controls(filename, region=None, **options):
    """Return matches in desktop coordinates, including negative monitor offsets."""
    screenshot, origin_x, origin_y = capture_desktop()
    if region is not None:
        left, top, width, height = region
        # Intersect the browser with the connected desktop.
        right = min(left + width, origin_x + screenshot.width)
        bottom = min(top + height, origin_y + screenshot.height)
        left, top = max(left, origin_x), max(top, origin_y)
        if right <= left or bottom <= top:
            return []
        screenshot = screenshot.crop((left - origin_x, top - origin_y,
                                      right - origin_x, bottom - origin_y))
        origin_x, origin_y = left, top
    matches = []
    with Image.open(ASSET_DIR / filename) as source:
        template = source.convert("RGB")
    for scale in IMAGE_SCALES:
        size = (round(template.width * scale), round(template.height * scale))
        if size[0] > screenshot.width or size[1] > screenshot.height:
            continue
        needle = template if scale == 1 else template.resize(size, Image.Resampling.LANCZOS)
        try:
            matches = list(pyautogui.locateAll(needle, screenshot, **options))
        except (pyautogui.ImageNotFoundException, ScreenImageNotFound):
            continue
        if matches:
            break
    return [Box(box.left + origin_x, box.top + origin_y,
                         box.width, box.height) for box in matches]


def locate_control(filename, region=None, **options):
    matches = locate_controls(filename, region=region, **options)
    if not matches:
        raise pyautogui.ImageNotFoundException(f"Could not find {filename} on screen.")
    return matches[0]


def check_starrez_ready():
    """Recognize the visible StarRez address and return its window bounds."""
    address_found = False
    diagnostics = {}
    try:
        for box in find_address_links(diagnostics):
            address_found = True
            region = window_region_at(box)
            # Text in a chat/page is not an address bar. Require a match in the
            # top browser-toolbar area, inside the window containing the text.
            if (region is not None
                    and region[0] <= box.left
                    and box.left + box.width <= region[0] + region[2]
                    and region[1] <= box.top
                    and box.top + box.height <= region[1] + max(120, box.height * 5)):
                return region, ""
    except OSError as error:
        return None, f"We couldn't check the screen images. {error}"
    if address_found:
        return None, "We found the StarRez address, but couldn't identify its window. Bring your browser to the front and try again."
    score_note = ""
    if "best_score" in diagnostics:
        score_note = (f" Best image match: {diagnostics['best_score']:.0%}; "
                      f"needed: {ADDRESS_CONFIDENCE:.0%}.")
    return None, ("We couldn't match the StarRez address image. Open the Main directory page "
                  "on either monitor and keep the full browser address bar visible."
                  + score_note)
