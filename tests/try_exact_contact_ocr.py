"""Use Windows OCR on the current StarRez screen, then point to Leo Test.

Run from the project root: python tests/try_exact_contact_ocr.py
This does not open a browser, click, type, or change any contact.
"""

import asyncio
import sys
from pathlib import Path

import pyautogui


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
for dependency_dir in (".ocr_deps", ".ocr_deps_streams"):
    local_dependency = Path(__file__).resolve().parent / dependency_dir
    if local_dependency.is_dir():
        sys.path.insert(0, str(local_dependency))

from contact_ocr import load_ocr_bindings, read_text  # noqa: E402
from guiFinished import email_cell_contains_text  # noqa: E402
from starrez_screen import (  # noqa: E402
    capture_desktop,
    check_starrez_ready,
    locate_control,
    locate_controls,
    physical_screen_coordinates,
)


TARGET_FIRST = "leo"
TARGET_LAST = "test"


def center_y(box):
    return box.top + box.height // 2


async def inspect_rows(engine, screenshot, origin_x, origin_y, rows,
                       last_name, email, room, region,
                       software_bitmap, pixel_format, alpha_mode, buffer_type):
    # The First Name column starts after the saved Last Name heading image.
    # Short test names fit inside that heading's width; longer clipped names
    # will fail the exact match rather than being guessed.
    first_name_left = last_name.left + last_name.width
    email_left = email.left
    email_right = min(email.left + email.width, room.left)
    if not (last_name.left < first_name_left < email_left < email_right):
        raise ValueError("The detected name and Email columns are out of order.")

    results = []
    for number, row in enumerate(rows, start=1):
        y = center_y(row)
        top, bottom = y - row.height // 2, y + row.height // 2
        if not (origin_x <= last_name.left < first_name_left < email_right
                <= origin_x + screenshot.width
                and origin_y <= top < bottom <= origin_y + screenshot.height
                and region[0] <= last_name.left < email_right <= region[0] + region[2]
                and region[1] <= top < bottom <= region[1] + region[3]):
            raise ValueError(f"Contact row {number} is not fully visible.")

        def crop(left, right):
            return screenshot.crop((left - origin_x, top - origin_y,
                                    right - origin_x, bottom - origin_y))

        has_email = email_cell_contains_text(crop(email_left, email_right))
        if has_email:
            results.append((number, y, "", "", False))
            continue
        last_text = await read_text(
            engine, crop(last_name.left, first_name_left),
            software_bitmap, pixel_format, alpha_mode, buffer_type,
        )
        first_text = await read_text(
            engine, crop(first_name_left, email_left),
            software_bitmap, pixel_format, alpha_mode, buffer_type,
        )
        results.append((number, y, last_text, first_text, True))
    return results


def main():
    try:
        engine, software_bitmap, pixel_format, alpha_mode, buffer_type = load_ocr_bindings()
    except (ImportError, OSError, RuntimeError):
        print("Windows OCR bindings are missing. Install these Python packages:")
        print("  winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging "
              "winrt-Windows.Storage.Streams")
        return 1

    pyautogui.FAILSAFE = True
    with physical_screen_coordinates():
        region, reason = check_starrez_ready()
        if region is None:
            print(f"Could not identify StarRez: {reason}")
            return 1
        try:
            last_name = locate_control(
                "last_name_label.png", region=region,
                confidence=0.75, grayscale=True,
            )
            email_matches = locate_controls(
                "email.png", region=region, confidence=0.80, grayscale=True,
            )
            room_matches = locate_controls(
                "room.png", region=region, confidence=0.80, grayscale=True,
            )
            contact_matches = locate_controls(
                "contact_status.png", region=region,
                confidence=0.75, grayscale=True,
            )
        except (pyautogui.ImageNotFoundException, OSError) as error:
            print(f"Could not find a required screen image: {error}")
            return 1

        email_candidates = [
            box for box in email_matches
            if box.left > last_name.left + last_name.width
            and abs(center_y(box) - center_y(last_name))
            <= max(box.height, last_name.height)
        ]
        if not email_candidates:
            print("Email heading was not found beside Last Name.")
            return 1
        email = min(email_candidates, key=lambda box: box.left)
        room_candidates = [
            box for box in room_matches
            if box.left > email.left + email.width // 2
            and abs(center_y(box) - center_y(email))
            <= max(box.height, email.height)
        ]
        if not room_candidates:
            print("Room heading was not found beside Email.")
            return 1
        room = min(room_candidates, key=lambda box: box.left)

        rows = []
        for box in sorted(contact_matches, key=lambda item: item.top):
            if box.top <= max(email.top + email.height, room.top + room.height):
                continue
            if box.left <= room.left:
                continue
            if any(abs(center_y(box) - center_y(other))
                   <= max(2, min(box.height, other.height) // 2) for other in rows):
                continue
            rows.append(box)
        if not rows:
            print("No Contact rows were found. Mouse was not moved.")
            return 1

        screenshot, origin_x, origin_y = capture_desktop()
        try:
            results = asyncio.run(inspect_rows(
                engine, screenshot, origin_x, origin_y, rows,
                last_name, email, room, region,
                software_bitmap, pixel_format, alpha_mode, buffer_type,
            ))
        except (RuntimeError, ValueError) as error:
            print(f"Could not inspect the rows: {error}")
            return 1

        print("\nCurrent-screen OCR test for Leo Test")
        for number, y, last, first, blank in results:
            if blank:
                print(f"  Row {number} (y={y}): blank Email; "
                      f"Last Name={last!r}, First Name={first!r}")
            else:
                print(f"  Row {number} (y={y}): Email filled")

        blank_rows = [row for row in results if row[4]]
        if any(not row[2] or not row[3] or "..." in row[2] or "..." in row[3]
               for row in blank_rows):
            print("At least one blank-email name was unreadable or cut off. "
                  "Mouse was not moved.")
            return 1
        matches = [row for row in blank_rows
                   if row[2].casefold() == TARGET_LAST
                   and row[3].casefold() == TARGET_FIRST]
        if len(matches) != 1:
            print(f"Found {len(matches)} exact Leo Test rows with blank Email; "
                  "expected one. Mouse was not moved.")
            return 1

        number, y, _, _, _ = matches[0]
        x = last_name.left + last_name.width // 2
        print(f"Moving mouse to row {number}, Last Name link at ({x}, {y}).")
        pyautogui.moveTo(x, y, duration=0.6)
        print("No click, typing, or StarRez change was made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
