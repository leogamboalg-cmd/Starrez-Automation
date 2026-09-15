import queue
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pyautogui
from guiLauncher import AutomationLauncher


class ContactResumeTests(unittest.TestCase):
    def test_review_waits_then_skips_contact_or_cancels(self):
        for cancel in (False, True):
            with self.subTest(cancel=cancel):
                rows = [["First", "Last", "Email"], ["A", "One", "a@test"],
                        ["B", "Two", "b@test"]]
                sheet = SimpleNamespace(max_row=3, cell=lambda row, column:
                                        SimpleNamespace(value=rows[row - 1][column - 1]))
                book = SimpleNamespace(active=sheet, close=Mock())
                runner = SimpleNamespace(event_queue=queue.Queue(),
                                         website_retry=threading.Event(), cancel_run=threading.Event())
                runner.cancel_run.wait = Mock(return_value=False)
                runner._wait_for_starrez = lambda **kw: AutomationLauncher._wait_for_starrez(runner, **kw)
                with patch("guiLauncher.load_workbook", return_value=book), \
                     patch("guiLauncher.get_column_numbers", return_value=dict(First=1, Last=2, Email=3)), \
                     patch("guiLauncher.check_starrez_ready", return_value=((0, 0, 1000, 800), "")), \
                     patch("guiLauncher.locate_control", side_effect=[pyautogui.ImageNotFoundException(), Mock()]) as add, \
                     patch("guiLauncher.process_contact", side_effect=[pyautogui.ImageNotFoundException("Multiple blank contacts"), None]) as process:
                    worker = threading.Thread(target=AutomationLauncher._run_contacts,
                                              args=(runner, "unused.xlsx"), daemon=True)
                    worker.start()
                    try:
                        while runner.event_queue.get(timeout=3)[0] != "failed":
                            pass
                        self.assertTrue(worker.is_alive())
                        self.assertEqual(process.call_count, 1)
                        if cancel:
                            runner.cancel_run.set()
                        runner.website_retry.set()
                        if not cancel:
                            while runner.event_queue.get(timeout=3)[0] != "website_required":
                                pass
                            self.assertEqual(process.call_count, 1)
                            runner.website_retry.set()
                        worker.join(timeout=3)
                        self.assertFalse(worker.is_alive())
                        self.assertEqual(process.call_count, 1 if cancel else 2)
                        if not cancel:
                            self.assertEqual(process.call_args.args, ("B", "Two", "b@test"))
                            self.assertEqual(add.call_count, 2)
                            self.assertEqual(list(runner.event_queue.queue)[-1], ("complete", 2))
                        else:
                            self.assertEqual(list(runner.event_queue.queue)[-1][0], "stopped")
                        book.close.assert_called_once()
                    finally:
                        runner.cancel_run.set()
                        runner.website_retry.set()
                        worker.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
