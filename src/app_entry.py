"""Entry point that keeps scheduled checks lightweight."""

import sys


if "--check-notifications" in sys.argv:
    from notification_checker import main
else:
    from guiLauncher import main


if __name__ == "__main__":
    main()
