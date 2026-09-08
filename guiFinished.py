from pathlib import Path
import time

import keyboard
import pyautogui
from openpyxl import load_workbook
from starrez_screen import locate_control, locate_controls, physical_screen_coordinates


EXCEL_FILE = Path(__file__).with_name("contactsFinal.xlsx")
REQUIRED_COLUMNS = ("First", "Last", "Email")

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
    last_name_x, _ = pyautogui.center(last_name_label)

    # Find the vertical center of the Contact row.
    print("Looking for a single Contact result row...")
    contact_statuses = list(locate_controls(
        "contact_status.png",
        region=screen_region,
        confidence=0.75,
        grayscale=True,
    ))
    if len(contact_statuses) != 1:
        raise pyautogui.ImageNotFoundException(
            f"Expected exactly one Contact row, found {len(contact_statuses)}."
        )
    contact_status = contact_statuses[0]
    _, contact_y = pyautogui.center(contact_status)

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
