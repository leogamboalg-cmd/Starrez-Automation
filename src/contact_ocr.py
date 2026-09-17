"""Windows OCR for resolving ambiguous blank-email Contact rows."""

import asyncio

from PIL import Image, ImageOps


def load_ocr_bindings():
    """Load OCR only when multiple blank rows need name verification."""
    from winrt.windows.graphics.imaging import (
        BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap,
    )
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage.streams import Buffer

    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise RuntimeError("No Windows OCR language is available.")
    return engine, SoftwareBitmap, BitmapPixelFormat, BitmapAlphaMode, Buffer


def ocr_bitmap(image, software_bitmap, pixel_format, alpha_mode, buffer_type):
    """Convert a PIL crop into a Windows SoftwareBitmap without disk files."""
    padded = ImageOps.expand(
        image.convert("RGB"), border=(20, 15, 20, 15), fill="white",
    )
    enlarged = padded.convert("RGBA").resize(
        (padded.width * 4, padded.height * 4), Image.Resampling.LANCZOS,
    )
    pixels = enlarged.tobytes()
    buffer = buffer_type(len(pixels))
    buffer.length = len(pixels)
    memoryview(buffer)[:] = pixels
    bitmap = software_bitmap(
        pixel_format.RGBA8, enlarged.width, enlarged.height,
        alpha_mode.STRAIGHT,
    )
    bitmap.copy_from_buffer(buffer)
    return bitmap


async def read_text(engine, crop, software_bitmap, pixel_format, alpha_mode, buffer_type):
    bitmap = ocr_bitmap(crop, software_bitmap, pixel_format, alpha_mode, buffer_type)
    try:
        result = await engine.recognize_async(bitmap)
        return " ".join(result.text.split())
    finally:
        bitmap.close()


def choose_exact_blank_row(screenshot, origin_x, origin_y, browser_region,
                           last_name_heading, email_heading, blank_rows,
                           expected_first, expected_last):
    """Return the sole OCR name match among blank rows, or refuse to choose."""
    first_name_left = last_name_heading.left + last_name_heading.width
    if not last_name_heading.left < first_name_left < email_heading.left:
        raise ValueError("The Last Name, First Name, and Email columns are out of order.")

    try:
        bindings = load_ocr_bindings()
    except (ImportError, OSError, RuntimeError) as error:
        raise ValueError(f"Windows OCR is unavailable: {error}") from error
    engine, *bitmap_types = bindings

    async def scan():
        matches = []
        for number, row_y, top, bottom in blank_rows:
            if not (origin_x <= last_name_heading.left < first_name_left
                    < email_heading.left <= origin_x + screenshot.width
                    and origin_y <= top < bottom <= origin_y + screenshot.height):
                raise ValueError(f"Contact row {number} is not fully visible.")
            if browser_region is not None:
                rx, ry, rw, rh = browser_region
                if not (rx <= last_name_heading.left < email_heading.left <= rx + rw
                        and ry <= top < bottom <= ry + rh):
                    raise ValueError(f"Contact row {number} is outside the browser.")

            def crop(left, right):
                return screenshot.crop((left - origin_x, top - origin_y,
                                        right - origin_x, bottom - origin_y))

            last = await read_text(
                engine, crop(last_name_heading.left, first_name_left), *bitmap_types,
            )
            first = await read_text(
                engine, crop(first_name_left, email_heading.left), *bitmap_types,
            )
            print(f"Contact row {number}: OCR Last Name={last!r}, First Name={first!r}.")
            if (not last or not first or "..." in last or "..." in first
                    or "…" in last or "…" in first):
                raise ValueError(f"Contact row {number} has an unreadable or cut-off name.")
            if (last.casefold() == " ".join(expected_last.split()).casefold()
                    and first.casefold() == " ".join(expected_first.split()).casefold()):
                matches.append((number, row_y))
        return matches

    try:
        matches = asyncio.run(scan())
    except (OSError, RuntimeError) as error:
        raise ValueError(f"Windows OCR could not read the Contact names: {error}") from error
    if len(matches) != 1:
        raise ValueError(
            f"OCR found {len(matches)} exact name matches among the blank-email Contact rows."
        )
    return matches[0]
