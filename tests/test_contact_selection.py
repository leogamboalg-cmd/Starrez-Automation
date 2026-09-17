from contextlib import ExitStack
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw
from pyscreeze import Box
import pyautogui

import guiFinished as runner
from starrez_screen import ASSET_DIR


class ContactSelectionTests(unittest.TestCase):
    def setUp(self):
        with Image.open(ASSET_DIR / "last_name_label.png") as image:
            self.label_size = image.size

    def fixture(self, emails, origin=(0, 0), scale=1, duplicate=False):
        ox, oy = origin
        label = Box(ox + 50, oy + 30,
                    round(self.label_size[0] * scale), round(self.label_size[1] * scale))
        email_heading = Box(ox + 300, oy + 30, round(107 * scale), round(32 * scale))
        room_heading = Box(ox + 430, oy + 30, round(105 * scale), round(27 * scale))
        screenshot = Image.new("RGB", (1100, 500), "white")
        draw = ImageDraw.Draw(screenshot)
        rows = []
        for index, email in enumerate(emails):
            y = 150 + 50 * index
            draw.rectangle((0, y - 20, 1099, y + 20), fill="#f1f1f1" if index % 2 else "white")
            if email:
                draw.text((310, y - 5),
                          email, fill="#124b97")
            draw.text((440, y - 5), "Room 101", fill="#124b97")
            rows.append(Box(ox + 850, oy + y - 10, 55, 20))
        if duplicate and rows:
            row = rows[0]
            rows.insert(1, Box(row.left + 1, row.top + 1, row.width, row.height))
        return label, email_heading, room_heading, rows, screenshot, (ox, oy, 1100, 500)

    def select(self, emails, first_name=None, last_name=None, **kwargs):
        label, email_heading, room_heading, rows, screenshot, region = self.fixture(emails, **kwargs)
        matches = {"email.png": [email_heading], "room.png": [room_heading],
                   "contact_status.png": rows}
        with patch.object(runner, "locate_controls", side_effect=lambda name, **_: matches[name]), \
             patch.object(runner, "capture_desktop", return_value=(screenshot, region[0], region[1])), \
             patch.object(runner.pyautogui, "failSafeCheck"), \
             patch("builtins.print"):
            return runner.select_blank_contact_row(
                label, screen_region=region,
                first_name=first_name, last_name=last_name,
            )

    def test_selects_only_blank_email_among_matching_contacts(self):
        self.assertEqual(self.select(["one@example.test", "", "two@example.test"])[1], 200)

    def test_single_blank_row_does_not_use_ocr(self):
        with patch.object(runner, "choose_exact_blank_row") as choose:
            self.assertEqual(self.select([""], first_name="Leo", last_name="Test")[1], 150)
        choose.assert_not_called()

    def test_room_text_does_not_fill_blank_email(self):
        self.assertEqual(self.select([""])[1], 150)

    def test_single_contact_with_existing_email_is_rejected(self):
        with self.assertRaisesRegex(pyautogui.ImageNotFoundException,
                                    "^No Contact row with a blank email was found\\.$"):
            self.select(["already@example.test"])

    def test_no_contact_rows_uses_required_message(self):
        with self.assertRaisesRegex(pyautogui.ImageNotFoundException,
                                    "^No Contact row with a blank email was found\\.$"):
            self.select([])

    def test_multiple_blank_rows_are_rejected(self):
        with self.assertRaisesRegex(pyautogui.ImageNotFoundException, "Multiple Contact rows"):
            self.select(["", "filled@example.test", ""])

    def test_multiple_blank_rows_use_exact_name_fallback(self):
        with patch.object(runner, "choose_exact_blank_row", return_value=(3, 250)) as choose:
            self.assertEqual(self.select(["", "filled@example.test", ""],
                                         first_name="Leo", last_name="Test")[1], 250)
        self.assertEqual(choose.call_args.args[-2:], ("Leo", "Test"))

    def test_unclear_ocr_still_refuses_to_choose(self):
        with patch.object(runner, "choose_exact_blank_row",
                          side_effect=ValueError("OCR could not identify a unique name")):
            with self.assertRaisesRegex(pyautogui.ImageNotFoundException, "Refusing to guess"):
                self.select(["", ""], first_name="Leo", last_name="Test")

    def test_overlapping_matches_are_one_row(self):
        self.assertEqual(self.select(["", "filled@example.test"], duplicate=True)[1], 150)

    def test_negative_monitor_origin_and_scaled_columns(self):
        x, y = self.select(["filled@example.test", ""], origin=(-1200, -50), scale=.8)
        self.assertEqual(y, 150)
        self.assertEqual(x, -1150 + round(self.label_size[0] * .8) // 2)

    def test_blank_and_text_cells_in_both_themes(self):
        for background, foreground in (("#f1f1f1", "#124b97"), ("#242424", "#cccccc")):
            with self.subTest(background=background):
                cell = Image.new("RGB", (250, 20), background)
                self.assertFalse(runner.email_cell_contains_text(cell))
                ImageDraw.Draw(cell).text((5, 3), "person@example.test", fill=foreground)
                self.assertTrue(runner.email_cell_contains_text(cell))

    def test_two_noise_pixels_do_not_make_a_blank_cell_filled(self):
        cell = Image.new("RGB", (250, 20), "white")
        cell.putpixel((1, 1), (0, 0, 0))
        cell.putpixel((200, 10), (0, 0, 0))
        self.assertFalse(runner.email_cell_contains_text(cell))

    def test_offscreen_cell_is_not_treated_as_blank(self):
        label, email_heading, room_heading, rows, screenshot, region = self.fixture([""])
        matches = {"email.png": [email_heading], "room.png": [room_heading],
                   "contact_status.png": rows}
        with patch.object(runner, "locate_controls", side_effect=lambda name, **_: matches[name]), \
             patch.object(runner, "capture_desktop", return_value=(screenshot, 0, 0)), \
             patch.object(runner.pyautogui, "failSafeCheck"), \
             patch("builtins.print"):
            with self.assertRaisesRegex(pyautogui.ImageNotFoundException, "not fully visible"):
                runner.select_blank_contact_row(label, screen_region=(0, 0, 400, 500))

    def test_missing_email_heading_is_rejected(self):
        label, _, room_heading, rows, _, region = self.fixture([""])
        matches = {"email.png": [], "room.png": [room_heading],
                   "contact_status.png": rows}
        with patch.object(runner, "locate_controls", side_effect=lambda name, **_: matches[name]), \
             patch.object(runner.pyautogui, "failSafeCheck"):
            with self.assertRaisesRegex(pyautogui.ImageNotFoundException, "Email column heading"):
                runner.select_blank_contact_row(label, screen_region=region)

    def test_emergency_stop_propagates(self):
        label, _, _, _, _, _ = self.fixture([""])
        with patch.object(runner.pyautogui, "failSafeCheck", side_effect=pyautogui.FailSafeException):
            with self.assertRaises(pyautogui.FailSafeException):
                runner.select_blank_contact_row(label)

    def test_process_clicks_selected_last_name_then_keeps_email_workflow(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(runner, "locate_control", return_value=Box(10, 10, 40, 20)))
            stack.enter_context(patch.object(runner, "locate_controls", return_value=[Box(100, 40, 32, 12)]))
            select = stack.enter_context(patch.object(runner, "select_blank_contact_row", return_value=(123, 456)))
            stack.enter_context(patch.object(runner.time, "sleep"))
            stack.enter_context(patch("builtins.print"))
            actions = {name: stack.enter_context(patch.object(runner.pyautogui, name))
                       for name in ("moveTo", "click", "hotkey", "press", "write")}
            region = (-1920, 0, 1920, 1080)
            runner.process_contact("First", "Last", "new@example.test", screen_region=region)
            actions["moveTo"].assert_any_call(30, 46, duration=0.5)
            select.assert_called_once_with(Box(10, 10, 40, 20), region, "First", "Last")
            actions["click"].assert_any_call(123, 456)
            self.assertEqual(actions["write"].call_args_list[-1].args, ("new@example.test",))
            actions["press"].assert_any_call("tab", presses=19)


if __name__ == "__main__":
    unittest.main()
