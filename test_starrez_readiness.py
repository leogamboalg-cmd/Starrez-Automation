import queue
import random
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image
import pyautogui

from guiLauncher import AutomationLauncher
import starrez_screen as screen


class ReadinessTests(unittest.TestCase):
    def test_display_coordinate_context_restored_after_error(self):
        change_context = Mock(return_value=123)
        api = SimpleNamespace(SetThreadDpiAwarenessContext=change_context)
        with patch.object(screen.ctypes.windll, "user32", api):
            with self.assertRaises(RuntimeError):
                with screen.physical_screen_coordinates():
                    raise RuntimeError("Test failure")
        self.assertEqual(change_context.call_count, 2)
        self.assertEqual(change_context.call_args.args, (123,))

    def test_both_address_images_match_on_secondary_monitor(self):
        api = SimpleNamespace(GetSystemMetrics=lambda code: -1920 if code == 76 else 0)
        for filename in ("link.png", "whiteLink.png"):
            for scale in (1, 1.25):
                with self.subTest(filename=filename, scale=scale):
                    with Image.open(screen.ASSET_DIR / filename) as source:
                        template = source.convert("RGB")
                    template = template.resize((round(template.width * scale), round(template.height * scale)),
                                               Image.Resampling.LANCZOS)
                    desktop = Image.new("RGB", (1920, 1080), "#828282")
                    desktop.paste(template, (100, 50))
                    with patch.object(screen.ctypes.windll, "user32", api), \
                         patch.object(screen.ImageGrab, "grab", return_value=desktop):
                        matches = list(screen.find_address_links())
                    self.assertTrue(any(abs(box.left + 1820) <= 1 and abs(box.top - 50) <= 1
                                        for box in matches))

    def test_unrelated_screen_does_not_match(self):
        api = SimpleNamespace(GetSystemMetrics=lambda code: 0)
        with patch.object(screen.ctypes.windll, "user32", api), \
             patch.object(screen.ImageGrab, "grab", return_value=Image.new("RGB", (1000, 500), "white")):
            self.assertEqual(list(screen.find_address_links()), [])

    def test_matches_keep_negative_monitor_coordinates(self):
        template = Image.frombytes("RGB", (20, 20), random.Random(42).randbytes(1200))
        desktop = Image.new("RGB", (400, 200))
        desktop.paste(template, (30, 40))
        api = SimpleNamespace(GetSystemMetrics=lambda code: -400 if code == 76 else -100)
        # Keep real image matching; replace only screen capture and asset loading.
        real_locate = pyautogui.locateAll
        with patch.object(screen.ctypes.windll, "user32", api), \
             patch.object(screen.ImageGrab, "grab", return_value=desktop), \
             patch.object(screen.pyautogui, "locateAll",
                          side_effect=lambda path, shot, **kw: real_locate(template, shot, **kw)):
            box = screen.locate_control("green_plus.png", region=(-390, -90, 180, 180), confidence=0.99)
        self.assertEqual(tuple(box), (-370, -60, 20, 20))

    def test_missing_address_never_checks_controls(self):
        with patch.object(screen, "find_address_links", return_value=iter([])), \
             patch.object(screen, "locate_control") as locate:
            region, reason = screen.check_starrez_ready()
        self.assertIsNone(region)
        self.assertIn("address", reason)
        locate.assert_not_called()

    def test_ready_browser_on_left_monitor(self):
        region = (-1920, 0, 1920, 1080)
        with patch.object(screen, "find_address_links", return_value=iter([screen.Box(-1800, 50, 420, 32)])), \
             patch.object(screen, "window_region_at", return_value=region), \
             patch.object(screen, "locate_control") as locate:
            result, reason = screen.check_starrez_ready()
        self.assertEqual(result, region)
        self.assertEqual(reason, "")
        locate.assert_not_called()

    def test_address_detection_does_not_require_button_images(self):
        with patch.object(screen, "find_address_links", return_value=iter([screen.Box(10, 10, 420, 32)])), \
             patch.object(screen, "window_region_at", return_value=(0, 0, 1000, 800)), \
             patch.object(screen, "locate_control", side_effect=pyautogui.ImageNotFoundException):
            region, reason = screen.check_starrez_ready()
        self.assertEqual(region, (0, 0, 1000, 800))
        self.assertEqual(reason, "")

    def test_window_coordinates_use_matched_address(self):
        def fill_rectangle(handle, pointer):
            pointer._obj.left, pointer._obj.top = -1920, 0
            pointer._obj.right, pointer._obj.bottom = 0, 1080
            return True
        api = SimpleNamespace(WindowFromPoint=Mock(return_value=123),
                              GetAncestor=Mock(return_value=456),
                              GetWindowRect=Mock(side_effect=fill_rectangle))
        with patch.object(screen.ctypes.windll, "user32", api):
            region = screen.window_region_at(screen.Box(-1800, 50, 420, 32))
        self.assertEqual(region, (-1920, 0, 1920, 1080))
        point = api.WindowFromPoint.call_args.args[0]
        self.assertEqual((point.x, point.y), (-1590, 66))

    def test_address_in_page_body_is_not_used_as_browser_address(self):
        with patch.object(screen, "find_address_links", return_value=iter([
            screen.Box(100, 600, 420, 32), screen.Box(2100, 50, 420, 32)])), \
             patch.object(screen, "window_region_at", side_effect=[
                 (0, 0, 1920, 1080), (1920, 0, 1920, 1080)]):
            region, _ = screen.check_starrez_ready()
        self.assertEqual(region, (1920, 0, 1920, 1080))

    def test_green_plus_at_eighty_percent_size(self):
        with Image.open(screen.ASSET_DIR / "green_plus.png") as source:
            template = source.convert("RGB")
        size = (round(template.width * .8), round(template.height * .8))
        desktop = Image.new("RGB", (1000, 600), "#dddddd")
        desktop.paste(template.resize(size, Image.Resampling.LANCZOS), (800, 200))
        api = SimpleNamespace(GetSystemMetrics=lambda code: 0)
        with patch.object(screen.ctypes.windll, "user32", api), \
             patch.object(screen.ImageGrab, "grab", return_value=desktop):
            box = screen.locate_control("green_plus.png", region=(500, 0, 500, 600), confidence=.8)
        self.assertLessEqual(abs(box.left - 800), 1)
        self.assertLessEqual(abs(box.top - 200), 1)

    def test_confirmation_rechecks_until_ready(self):
        runner = SimpleNamespace(cancel_run=threading.Event(), website_retry=threading.Event(),
                                 event_queue=queue.Queue())
        # Skip countdown delays while preserving the explicit retry wait.
        runner.cancel_run.wait = Mock(return_value=False)
        results = []
        with patch("guiLauncher.check_starrez_ready", side_effect=[
            (None, "Open StarRez"), (None, "Still not ready"), ((0, 0, 1000, 800), "")
        ]) as check:
            worker = threading.Thread(target=lambda: results.append(
                AutomationLauncher._wait_for_starrez(runner)), daemon=True)
            worker.start()
            for expected_checks in (1, 2):
                while runner.event_queue.get(timeout=2)[0] != "website_required":
                    pass
                self.assertTrue(worker.is_alive())
                self.assertEqual(check.call_count, expected_checks)
                runner.website_retry.set()
            worker.join(timeout=2)
            self.assertFalse(worker.is_alive())
        self.assertEqual(results, [(0, 0, 1000, 800)])

    def test_cancel_releases_paused_worker(self):
        runner = SimpleNamespace(cancel_run=threading.Event(), website_retry=threading.Event(),
                                 event_queue=queue.Queue())
        results = []
        with patch("guiLauncher.check_starrez_ready", return_value=(None, "Open StarRez")):
            worker = threading.Thread(target=lambda: results.append(
                AutomationLauncher._wait_for_starrez(runner)), daemon=True)
            worker.start()
            while runner.event_queue.get(timeout=2)[0] != "website_required":
                pass
            runner.cancel_run.set()
            runner.website_retry.set()
            worker.join(timeout=2)
        self.assertEqual(results, [None])

    def test_contact_loop_preserves_progress_and_monitor_region(self):
        rows = [["First", "Last", "Email"], ["A", "One", "a@example.test"],
                ["B", "Two", "b@example.test"]]
        sheet = SimpleNamespace(max_row=3, cell=lambda row, column:
                                SimpleNamespace(value=rows[row - 1][column - 1]))
        book = SimpleNamespace(active=sheet, close=Mock())
        region = (-1920, 0, 1920, 1080)
        runner = SimpleNamespace(event_queue=queue.Queue(),
                                 _wait_for_starrez=Mock(return_value=region))
        with patch("guiLauncher.load_workbook", return_value=book), \
             patch("guiLauncher.get_column_numbers", return_value=dict(First=1, Last=2, Email=3)), \
             patch("guiLauncher.process_contact") as process:
            AutomationLauncher._run_contacts(runner, "unused.xlsx")
        self.assertEqual([call.args for call in process.call_args_list],
                         [("A", "One", "a@example.test"), ("B", "Two", "b@example.test")])
        self.assertTrue(all(call.kwargs["screen_region"] == region for call in process.call_args_list))
        self.assertEqual(runner._wait_for_starrez.call_count, 2)
        self.assertEqual(list(runner.event_queue.queue)[-1], ("complete", 2))
        book.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
