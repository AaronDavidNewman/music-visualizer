"""Image processing helpers. Placeholder for the app's real processing pipeline."""

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
