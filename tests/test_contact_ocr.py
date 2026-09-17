import unittest
from unittest.mock import AsyncMock, patch

from PIL import Image
from pyscreeze import Box

import contact_ocr


class ExactBlankRowTests(unittest.TestCase):
    def choose(self, recognized_names):
        screenshot = Image.new("RGB", (500, 300), "white")
        last_heading = Box(50, 30, 90, 35)
        email_heading = Box(300, 30, 100, 30)
        rows = [(1, 150, 140, 160), (2, 200, 190, 210)]
        bindings = (object(), object(), object(), object(), object())
        with patch.object(contact_ocr, "load_ocr_bindings", return_value=bindings), \
             patch.object(contact_ocr, "read_text",
                          new=AsyncMock(side_effect=recognized_names)), \
             patch("builtins.print"):
            return contact_ocr.choose_exact_blank_row(
                screenshot, 0, 0, (0, 0, 500, 300),
                last_heading, email_heading, rows, "Leo", "Test",
            )

    def test_exact_test_is_distinct_from_test2(self):
        self.assertEqual(self.choose(["Test", "Leo", "Test2", "Leo"]), (1, 150))

    def test_duplicate_exact_names_refuse_to_choose(self):
        with self.assertRaisesRegex(ValueError, "2 exact name matches"):
            self.choose(["Test", "Leo", "Test", "Leo"])

    def test_unreadable_name_refuses_to_choose(self):
        with self.assertRaisesRegex(ValueError, "unreadable"):
            self.choose(["Test", "Leo", "", "Leo"])


if __name__ == "__main__":
    unittest.main()
