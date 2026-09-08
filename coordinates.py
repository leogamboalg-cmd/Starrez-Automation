import pyautogui
import time

print("Move your mouse to find coordinates.")
print("Press Ctrl+C in this terminal to stop.\n")

try:
    while True:
        x, y = pyautogui.position()

        print(
            f"\rCurrent coordinates: x={x}, y={y}     ",
            end="",
            flush=True
        )

        time.sleep(2)

except KeyboardInterrupt:
    print("\n\nCoordinate tracker stopped.")


# GREEN PLUS = (2492, 263)
