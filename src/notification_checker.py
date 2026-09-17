"""Short-lived, invisible scheduled check for new response IDs."""

from notification_service import show_pending_notification
from response_tracking import (
    get_shared_response_file,
    load_csv_contacts,
    notification_needed,
    pending_contacts,
    record_notification,
)


def main():
    shared_response_file = get_shared_response_file()
    if not shared_response_file.is_file():
        return
    try:
        pending = pending_contacts(load_csv_contacts(shared_response_file))
        if notification_needed(pending):
            show_pending_notification(len(pending))
            record_notification(pending)
    except Exception:
        # OneDrive can briefly lock or replace the CSV while synchronizing.
        # The next scheduled check will retry.
        return


if __name__ == "__main__":
    main()
