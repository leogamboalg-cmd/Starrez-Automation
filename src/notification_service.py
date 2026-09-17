"""Windows notification delivery for pending newsletter responses."""

APP_ID = "Add New Contacts for Newsletter"
NOTIFICATION_GROUP = "newsletter-responses"


def show_pending_notification(count):
    from windows_toasts import Toast, WindowsToaster

    toaster = WindowsToaster(APP_ID)
    noun = "response is" if count == 1 else "responses are"
    toast = Toast(
        [
            "New newsletter responses",
            f"{count} new {noun} ready. Open Add New Contacts for Newsletter to process them.",
        ],
        group=NOTIFICATION_GROUP,
    )
    toaster.show_toast(toast)


def clear_pending_notifications():
    try:
        from windows_toasts import WindowsToaster

        WindowsToaster(APP_ID).remove_toast_group(NOTIFICATION_GROUP)
    except Exception:
        # Notification cleanup must never interrupt contact processing.
        pass

