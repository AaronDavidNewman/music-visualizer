"""Image processing helpers. Placeholder for the app's real processing pipeline.

Order of operations:
    1. Open the bytes as an image with Pillow - ``image_info()``.
    2. Read its format, mode, width and height - ``image_info()`` - a dictionary of four entries.
    3. A file that Pillow cannot identify is refused with ``InvalidImageError``.
"""

import io

from PIL import Image, UnidentifiedImageError


class InvalidImageError(ValueError):
    pass


def image_info(data: bytes) -> dict[str, int | str]:
    try:
        with Image.open(io.BytesIO(data)) as img:
            return {
                "format": img.format or "unknown",
                "mode": img.mode,
                "width": img.width,
                "height": img.height,
            }
    except UnidentifiedImageError as exc:
        raise InvalidImageError("Not a valid image file") from exc
