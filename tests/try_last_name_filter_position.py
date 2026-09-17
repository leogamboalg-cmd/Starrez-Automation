"""Move the mouse to the Last Name filter using two screen image anchors.

Run from the project root with: python tests/try_last_name_filter_position.py
This script only moves the mouse; it does not click or type.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import pyautogui
from PIL import Image


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from starrez_screen import (  # noqa: E402
    ASSET_DIR,
    capture_desktop,
    check_starrez_ready,
    locate_control,
    locate_controls,
    physical_screen_coordinates,
)


def image_match_score(filename, box, screenshot, origin_x, origin_y):
    """Return OpenCV's normalized grayscale similarity for a located image."""
    left = int(box.left - origin_x)
    top = int(box.top - origin_y)
    found = screenshot.crop((left, top, left + int(box.width), top + int(box.height)))
    with Image.open(ASSET_DIR / filename) as source:
        template = source.convert("RGB").resize(
            (int(box.width), int(box.height)), Image.Resampling.LANCZOS,
        )
    found_gray = cv2.cvtColor(np.asarray(found.convert("RGB")), cv2.COLOR_RGB2GRAY)
    template_gray = cv2.cvtColor(np.asarray(template), cv2.COLOR_RGB2GRAY)
    return float(cv2.matchTemplate(
        found_gray, template_gray, cv2.TM_CCOEFF_NORMED,
    )[0, 0])


def main():
    pyautogui.FAILSAFE = True

    with physical_screen_coordinates():
        region, reason = check_starrez_ready()
        if region is None:
            print(f"Could not identify the StarRez browser window: {reason}")
            return 1

        try:
            label = locate_control(
                "last_name_label.png", region=region, confidence=0.75,
                grayscale=True,
            )
            all_matches = locate_controls(
                "all.png", region=region, confidence=0.80,
                grayscale=True,
            )
        except (pyautogui.ImageNotFoundException, OSError) as error:
            print(f"Could not find a required image: {error}")
            return 1

        # The Entry Status and Location dropdowns are both to the right of
        # Last Name and directly below the table headers. Either gives the
        # filter row's Y coordinate; use the nearer one.
        candidates = [
            box for box in all_matches
            if box.left > label.left + label.width
            and label.top < box.top + box.height // 2
            < label.top + 6 * label.height
        ]
        if not candidates:
            print("Found the Last Name label, but no <All> in its filter row.")
            return 1

        dropdown = min(candidates, key=lambda box: box.left)
        x = label.left + label.width // 2
        y = dropdown.top + dropdown.height // 2
        screenshot, origin_x, origin_y = capture_desktop()
        label_score = image_match_score(
            "last_name_label.png", label, screenshot, origin_x, origin_y,
        )
        dropdown_score = image_match_score(
            "all.png", dropdown, screenshot, origin_x, origin_y,
        )
        print("\nLast Name filter position test")
        print(f"  StarRez window:     {region}")
        print(f"  Last Name label:    {label} | similarity {label_score:.1%}")
        print(f"  <All> dropdown:     {dropdown} | similarity {dropdown_score:.1%}")
        print(f"  <All> candidates:   {len(candidates)} in the filter row")
        print(f"  Mouse destination:  ({x}, {y})")
        print("  Action:             moving mouse only; no click or typing\n")
        pyautogui.moveTo(x, y, duration=0.6)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
