from pathlib import Path
import time

import keyboard
import numpy as np
import pyautogui
from openpyxl import load_workbook
from PIL import Image
from starrez_screen import (
    capture_desktop, locate_control, locate_controls, physical_screen_coordinates,
)


EXCEL_FILE = Path(__file__).with_name("contactsFinal.xlsx")
REQUIRED_COLUMNS = ("First", "Last", "Email")

# Email cell INTERIOR, measured from the LEFT edge of last_name_label.png.
# These are starting layout values: calibrate them to your StarRez columns.
# Leave cell borders/padding outside this range. Values use the saved label's
# pixel scale; the detected label size scales them for other display settings.
EMAIL_COLUMN_LEFT_OFFSET = 250
EMAIL_COLUMN_RIGHT_OFFSET = 550
EMAIL_CELL_HALF_HEIGHT = 10
EMAIL_BACKGROUND_CONTRAST = 30  # RGB channel difference from the cell background.
EMAIL_MIN_VISIBLE_PIXELS = 3    # Ignore at most two isolated noisy pixels.

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3


def get_column_numbers(sheet):
    """Return the Excel column number for each required heading."""
    headings = {
        str(cell.value).strip().lower(): cell.column
        for cell in sheet[1]
        if cell.value is not None
    }

    missing = [
        heading
        for heading in REQUIRED_COLUMNS
        if heading.lower() not in headings
    ]
    if missing:
        raise ValueError(
            "The Excel file is missing these columns: "
            + ", ".join(missing)
        )

    return {
        heading: headings[heading.lower()]
        for heading in REQUIRED_COLUMNS
    }


def email_cell_contains_text(cell_image):
    """Detect visible marks against the cell's own background; no OCR required."""
    pixels = np.asarray(cell_image.convert("RGB"), dtype=np.int16)
    if pixels.size == 0:
        raise pyautogui.ImageNotFoundException("The Email cell could not be inspected.")
    # Each row may have a different background (striping, selection, dark mode).
    background = np.median(pixels.reshape(-1, 3), axis=0)
    contrast = np.max(np.abs(pixels - background), axis=2)
    return np.count_nonzero(contrast >= EMAIL_BACKGROUND_CONTRAST) >= EMAIL_MIN_VISIBLE_PIXELS


def select_blank_contact_row(last_name_label, screen_region=None):
    """Return the unique Contact row with a visually blank Email cell."""
    pyautogui.failSafeCheck()
    contact_statuses = list(locate_controls(
        "contact_status.png", region=screen_region,
        confidence=0.75, grayscale=True,
    ))
    # A single word can produce several overlapping template matches. Treat
    # those as one row, while preserving distinct rows in top-to-bottom order.
    rows = []
    for status in sorted(contact_statuses, key=lambda box: (box.top, box.left)):
        if status.top <= last_name_label.top + last_name_label.height:
            continue  # Exclude matches above the results table.
        center_y = status.top + status.height // 2
        if any(abs(center_y - (row.top + row.height // 2))
               <= max(2, min(status.height, row.height) // 2) for row in rows):
            continue
        rows.append(status)
    print(f"Found {len(rows)} Contact row(s).")
    if not rows:
        raise pyautogui.ImageNotFoundException("No Contact row with a blank email was found.")

    with Image.open(Path(__file__).with_name("last_name_label.png")) as reference:
        scale_x = last_name_label.width / reference.width
        scale_y = last_name_label.height / reference.height
    left = round(last_name_label.left + EMAIL_COLUMN_LEFT_OFFSET * scale_x)
    right = round(last_name_label.left + EMAIL_COLUMN_RIGHT_OFFSET * scale_x)
    half_height = max(2, round(EMAIL_CELL_HALF_HEIGHT * scale_y))
    if not 0 < EMAIL_COLUMN_LEFT_OFFSET < EMAIL_COLUMN_RIGHT_OFFSET:
        raise pyautogui.ImageNotFoundException("Check the Email column offset constants before continuing.")
    if right >= min(row.left for row in rows):
        raise pyautogui.ImageNotFoundException(
            "The Email inspection area overlaps Entry Status. Check the Email column offset constants.")

    screenshot, origin_x, origin_y = capture_desktop()
    blank_rows = []
    for number, status in enumerate(rows, start=1):
        pyautogui.failSafeCheck()
        row_y = status.top + status.height // 2
        top, bottom = row_y - half_height, row_y + half_height
        # Never let Pillow pad an off-screen crop with black pixels: that could
        # turn an unseen cell into an apparently blank one.
        visible = (origin_x <= left < right <= origin_x + screenshot.width
                   and origin_y <= top < bottom <= origin_y + screenshot.height)
        if screen_region is not None:
            rx, ry, rw, rh = screen_region
            visible = visible and rx <= left < right <= rx + rw and ry <= top < bottom <= ry + rh
        if not visible:
            raise pyautogui.ImageNotFoundException(
                f"The Email cell for Contact row {number} is not fully visible. "
                "Check the Email column offsets and browser window.")
        if any(other is not status and top <= other.top + other.height // 2 < bottom
               for other in rows):
            raise pyautogui.ImageNotFoundException(
                "The Email inspection area spans multiple rows. Reduce EMAIL_CELL_HALF_HEIGHT.")
        cell = screenshot.crop((left - origin_x, top - origin_y,
                                right - origin_x, bottom - origin_y))
        has_email = email_cell_contains_text(cell)
        print(f"Contact row {number} (y={row_y}): "
              + ("Email contains visible text." if has_email else "Email is visually blank."))
        if not has_email:
            blank_rows.append((number, row_y))

    if not blank_rows:
        raise pyautogui.ImageNotFoundException("No Contact row with a blank email was found.")
    if len(blank_rows) > 1:
        raise pyautogui.ImageNotFoundException(
            f"Multiple Contact rows with blank emails were found ({len(blank_rows)}). Refusing to guess.")
    number, row_y = blank_rows[0]
    last_name_x = last_name_label.left + last_name_label.width // 2
    print(f"Selected blank Contact row {number}: Last Name link at x={last_name_x}, y={row_y}.")
    return last_name_x, row_y


@physical_screen_coordinates()
def process_contact(first_name, last_name, email, screen_region=None):
    """Run the original StarRez GUI workflow for one contact."""
    print("Looking for the green plus button...")
    green_button = locate_control(
        "green_plus.png",
        region=screen_region,
        confidence=0.80,
    )
    if green_button is None:
        raise pyautogui.ImageNotFoundException(
            "Green plus button was not found."
        )

    button_x, button_y = pyautogui.center(green_button)
    print(f"Button found at x={button_x}, y={button_y}")

    pyautogui.moveTo(
        button_x,
        button_y,
        duration=0.6,
        tween=pyautogui.easeInOutQuad,
    )
    pyautogui.click()

    print("Green plus button clicked.")
    print("Entering the contact's title and name...")
    time.sleep(0.2)
    pyautogui.press("tab")
    pyautogui.press("space")
    pyautogui.press("down", presses=16, interval=0.05)
    pyautogui.press("enter")
    pyautogui.press("tab", presses=2)
    pyautogui.write(first_name, interval=0.05)
    pyautogui.press("tab")
    pyautogui.write(last_name, interval=0.05)
    pyautogui.press("tab", presses=10)
    pyautogui.press("enter")
    print("Initial contact form submitted; waiting 6 seconds...")
    time.sleep(6)

    print("Looking for the last-name search area...")
    area = locate_control(
        "last_name_area.png",
        region=screen_region,
        confidence=0.75,
    )

    if area is None:
        raise pyautogui.ImageNotFoundException(
            "Last Name label was not found."
        )

    x = area.left + area.width // 2
    y = area.top + area.height + 42

    pyautogui.moveTo(x, y, duration=0.5)
    pyautogui.click()

    # Clear the existing last name
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("backspace")
    print("Search area found; entering last name and first name...")
    pyautogui.write(last_name, interval=0.05)
    time.sleep(0.2)
    pyautogui.press("tab")
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("backspace")
    pyautogui.write(first_name, interval=0.05)
    time.sleep(7)

    # Find the horizontal center of the Last Name column.
    print("Looking for the Last Name column label...")
    last_name_label = locate_control(
        "last_name_label.png",
        region=screen_region,
        confidence=0.75,
        grayscale=True,
    )
    if last_name_label is None:
        raise pyautogui.ImageNotFoundException(
            "Last Name column label was not found."
        )
    print("Checking Contact rows for a blank Email cell...")
    last_name_x, contact_y = select_blank_contact_row(last_name_label, screen_region)

    # Same column as Last Name, same row as Contact.
    print("Contact row found; opening it and entering the email...")
    pyautogui.click(last_name_x, contact_y)
    time.sleep(1)
    pyautogui.press("tab", presses=5)
    time.sleep(0.1)
    pyautogui.press("down", presses=4)
    time.sleep(0.1)
    pyautogui.press("enter")
    time.sleep(0.5)
    pyautogui.press("tab", presses=4)
    time.sleep(0.1)
    pyautogui.press("enter")
    time.sleep(0.5)
    pyautogui.press("tab", presses=19)
    time.sleep(0.1)
    pyautogui.write(email, interval=0.05)
    time.sleep(0.1)
    pyautogui.press("tab", presses=3)
    time.sleep(0.1)
    pyautogui.press("enter")
    time.sleep(2)
    print("Email form submitted; looking for the Cancel button...")
    cancel_button = locate_control(
        "cancel_button.png",
        region=screen_region,
        confidence=0.80,
    )
    if cancel_button is None:
        raise pyautogui.ImageNotFoundException(
            "Cancel plus button was not found."
        )

    button_x, button_y = pyautogui.center(cancel_button)
    print(f"Cancel button found at x={button_x}, y={button_y}")

    pyautogui.moveTo(
        button_x,
        button_y,
        duration=0.6,
        tween=pyautogui.easeInOutQuad,
    )
    pyautogui.click()
    print("Cancel button clicked.")
    time.sleep(2)
    # Return to the main search page for the next Excel row.
    print("Looking for the Main button...")
    final_check = locate_control(
        "main.png",
        region=screen_region,
        confidence=0.75,
        grayscale=True,
    )
    if final_check is None:
        raise pyautogui.ImageNotFoundException(
            "Main button was not found."
        )
    main_x, main_y = pyautogui.center(final_check)
    pyautogui.click(main_x, main_y)
    print("Main button clicked; returning to the starting page...")
    time.sleep(6)


def main():
    if not EXCEL_FILE.exists():
        print(f"Excel file not found: {EXCEL_FILE}")
        print("Create contacts.xlsx with columns: First, Last, Email")
        return

    workbook = load_workbook(EXCEL_FILE, read_only=True, data_only=True)
    sheet = workbook.active

    try:
        columns = get_column_numbers(sheet)

        print(f"Loaded contacts from: {EXCEL_FILE}")
        print("Open StarRez, then press RIGHT SHIFT for each contact.")
        print("Move the mouse to the top-left corner for emergency stop.")

        row_number = 2
        completed = 0
        skipped = 0
        keyboard.wait("right shift")
        # Intentionally use a while loop to process every Excel row.
        while row_number <= sheet.max_row:
            first_value = sheet.cell(
                row=row_number,
                column=columns["First"],
            ).value
            last_value = sheet.cell(
                row=row_number,
                column=columns["Last"],
            ).value
            email_value = sheet.cell(
                row=row_number,
                column=columns["Email"],
            ).value

            first_name = str(first_value or "").strip()
            last_name = str(last_value or "").strip()
            email = str(email_value or "").strip()

            if not first_name and not last_name and not email:
                print(f"Skipping blank Excel row {row_number}.")
                skipped += 1
                row_number += 1
                continue

            if not first_name or not last_name or not email:
                print(
                    f"Skipping row {row_number}: First, Last, and Email "
                    "are all required."
                )
                skipped += 1
                row_number += 1
                continue

            print(
                f"Ready for row {row_number}: "
                f"{first_name} {last_name} ({email})"
            )
            print("Press RIGHT SHIFT to process this contact.")

            print("RIGHT SHIFT detected. Starting contact...")
            time.sleep(1)

            try:
                process_contact(first_name, last_name, email)
                completed += 1
                print(f"Finished row {row_number}.")
            except pyautogui.ImageNotFoundException as error:
                skipped += 1
                error_text = str(error) or "No error message was provided."
                print(
                    f"Could not finish row {row_number}: "
                    f"{type(error).__name__}: {error_text}"
                )

            row_number += 1

        print(
            f"All rows checked. Completed: {completed}; "
            f"skipped/failed: {skipped}."
        )
    finally:
        workbook.close()


if __name__ == "__main__":
    try:
        main()
    except pyautogui.FailSafeException:
        print("Emergency stop triggered by moving the mouse top-left.")
    except KeyboardInterrupt:
        print("Stopped by user.")
    except (OSError, ValueError) as error:
        print(f"Unable to start: {error}")
