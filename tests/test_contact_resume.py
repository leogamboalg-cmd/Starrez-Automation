import queue
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pyautogui
from guiLauncher import AutomationLauncher


class ContactResumeTests(unittest.TestCase):
    def test_review_waits_then_skips_contact_or_cancels(self):
        for cancel in (False, True):
            with self.subTest(cancel=cancel):
                contacts = [
                    {"id": "1", "row_number": 2, "first": "A", "last": "One",
                     "email": "a@test", "completion_time": ""},
                    {"id": "2", "row_number": 3, "first": "B", "last": "Two",
                     "email": "b@test", "completion_time": ""},
                ]
                runner = SimpleNamespace(event_queue=queue.Queue(),
                                         website_retry=threading.Event(), cancel_run=threading.Event())
                runner.cancel_run.wait = Mock(return_value=False)
                runner._wait_for_starrez = lambda **kw: AutomationLauncher._wait_for_starrez(runner, **kw)
                with patch("guiLauncher.load_contacts", return_value=contacts), \
                     patch("guiLauncher.check_starrez_ready", return_value=((0, 0, 1000, 800), "")), \
                     patch("guiLauncher.locate_control", side_effect=[pyautogui.ImageNotFoundException(), Mock()]) as add, \
                     patch("guiLauncher.process_contact", side_effect=[pyautogui.ImageNotFoundException("Multiple blank contacts"), None]) as process:
                    worker = threading.Thread(target=AutomationLauncher._run_contacts,
                                              args=(runner, Path("unused.xlsx")), daemon=True)
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
                            self.assertEqual(list(runner.event_queue.queue)[-1], ("complete", 2, 0))
                        else:
                            self.assertEqual(list(runner.event_queue.queue)[-1][0], "stopped")
                    finally:
                        runner.cancel_run.set()
                        runner.website_retry.set()
                        worker.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
