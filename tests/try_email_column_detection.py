"""Inspect Contact-row Email cells and optionally point to blank rows.

Run from the project root: python tests/try_email_column_detection.py
To move the mouse over each blank row: python tests/try_email_column_detection.py --move
Neither mode clicks or types.
"""

import sys
import time
from pathlib import Path

import pyautogui


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from guiFinished import email_cell_contains_text  # noqa: E402
from starrez_screen import (  # noqa: E402
    capture_desktop,
    check_starrez_ready,
    locate_control,
    locate_controls,
    physical_screen_coordinates,
)


def center_y(box):
    return box.top + box.height // 2


def main():
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] != "--move"):
        print("Usage: python tests/try_email_column_detection.py [--move]")
        return 2
    move_to_blank_rows = len(sys.argv) == 2
    pyautogui.FAILSAFE = True
    with physical_screen_coordinates():
        region, reason = check_starrez_ready()
        if region is None:
            print(f"Could not identify the StarRez browser window: {reason}")
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
            print(f"Could not find a required image: {error}")
            return 1

        email_candidates = [
            box for box in email_matches
            if box.left > last_name.left + last_name.width
            and abs(center_y(box) - center_y(last_name))
            <= max(box.height, last_name.height)
        ]
        if not email_candidates:
            print("Could not find the Email heading beside Last Name.")
            return 1
        email = min(email_candidates, key=lambda box: box.left)

        room_candidates = [
            box for box in room_matches
            if box.left > email.left + email.width // 2
            and abs(center_y(box) - center_y(email))
            <= max(box.height, email.height)
        ]
        if not room_candidates:
            print("Could not find the Room heading beside Email.")
            return 1
        room = min(room_candidates, key=lambda box: box.left)

        # Use the Email heading's span, stopping sooner if Room begins there.
        # This keeps the Room cell's left border out of the image crop.
        left, right = email.left, min(email.left + email.width, room.left)
        if right <= left + email.width // 2:
            print("Email and Room headings overlap; cannot inspect the column safely.")
            return 1

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
            print("No Contact rows were found beneath the headings.")
            return 1

        screenshot, origin_x, origin_y = capture_desktop()
        print("\nEmail column detection test (read-only)")
        print(f"  StarRez window: {region}")
        print(f"  Email heading:  {email}")
        print(f"  Room heading:   {room}")
        print(f"  Email X range:  [{left}, {right})")
        print(f"  Contact rows:   {len(rows)}\n")

        blank_positions = []
        for number, row in enumerate(rows, start=1):
            y = center_y(row)
            top, bottom = y - row.height // 2, y + row.height // 2
            if not (origin_x <= left < right <= origin_x + screenshot.width
                    and origin_y <= top < bottom <= origin_y + screenshot.height
                    and region[0] <= left < right <= region[0] + region[2]
                    and region[1] <= top < bottom <= region[1] + region[3]):
                print(f"  Row {number}: area is outside the captured desktop")
                continue
            cell = screenshot.crop((left - origin_x, top - origin_y,
                                    right - origin_x, bottom - origin_y))
            has_text = email_cell_contains_text(cell)
            result = "text detected" if has_text else "blank"
            print(f"  Row {number}: rectangle ({left}, {top}, {right}, {bottom})"
                  f" | {result}")
            if not has_text:
                blank_positions.append((number, last_name.left + last_name.width // 2, y))

        if move_to_blank_rows:
            if not blank_positions:
                print("\nNo blank Contact rows were found; mouse was not moved.")
            else:
                print(f"\nMoving over {len(blank_positions)} blank Contact row(s).")
                for index, (number, x, y) in enumerate(blank_positions):
                    print(f"  Row {number}: moving to Last Name link at ({x}, {y})")
                    pyautogui.moveTo(x, y, duration=0.6)
                    if index + 1 < len(blank_positions):
                        time.sleep(2)
                print("No clicks, typing, or StarRez changes were made.")
        else:
            print("\nNo mouse movement, clicks, typing, or StarRez changes were made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
