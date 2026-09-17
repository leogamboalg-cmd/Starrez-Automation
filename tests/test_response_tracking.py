import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import response_tracking


class ResponseTrackingTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.csv_path = self.root / "responses.csv"
        with self.csv_path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "Id", "Start time", "Completion time", "Contact First Name",
                    "Contact Last Name", "Contact Email",
                ],
            )
            writer.writeheader()
            writer.writerow({
                "Id": "42",
                "Start time": "9/16/2026 1:00 PM",
                "Completion time": "9/16/2026 1:01 PM",
                "Contact First Name": "Ada",
                "Contact Last Name": "Lovelace",
                "Contact Email": "ada@example.edu",
            })
        self.state_patch = patch.object(
            response_tracking, "STATE_FILE", self.root / "state.json"
        )
        self.state_patch.start()

    def tearDown(self):
        self.state_patch.stop()
        self.temporary_directory.cleanup()

    def test_loads_forms_response_columns(self):
        contacts = response_tracking.load_csv_contacts(self.csv_path)
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]["id"], "42")
        self.assertEqual(contacts[0]["first"], "Ada")
        self.assertEqual(contacts[0]["last"], "Lovelace")
        self.assertEqual(contacts[0]["email"], "ada@example.edu")

    def test_successful_id_is_no_longer_pending(self):
        contact = response_tracking.load_csv_contacts(self.csv_path)[0]
        self.assertEqual(response_tracking.pending_contacts([contact]), [contact])
        response_tracking.mark_processed(contact)
        self.assertEqual(response_tracking.pending_contacts([contact]), [])
        saved = response_tracking.load_state()["processed_ids"]["42"]
        self.assertNotIn("email", saved)

    def test_notification_only_repeats_after_reset(self):
        contact = response_tracking.load_csv_contacts(self.csv_path)[0]
        pending = [contact]
        self.assertTrue(response_tracking.notification_needed(pending))
        response_tracking.record_notification(pending)
        self.assertFalse(response_tracking.notification_needed(pending))
        response_tracking.reset_notification_state()
        self.assertTrue(response_tracking.notification_needed(pending))

    def test_shared_response_file_comes_from_saved_settings(self):
        settings_path = self.root / "launcher_settings.json"
        selected_path = self.root / "UHS Newsletter Responses.csv"
        settings_path.write_text(
            json.dumps({"shared_response_file": str(selected_path)}),
            encoding="utf-8",
        )
        with patch.object(response_tracking, "SETTINGS_FILE", settings_path):
            self.assertEqual(
                response_tracking.get_shared_response_file(),
                selected_path,
            )


if __name__ == "__main__":
    unittest.main()
