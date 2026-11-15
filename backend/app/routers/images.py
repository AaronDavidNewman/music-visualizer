"""The endpoint ``POST /api/images/info``, which reports the format, mode and size of an uploaded image.

No data processing: this module only reads the upload (refused above the size limit) and calls
``services/image_processing.image_info()``.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import settings
from ..services.image_processing import InvalidImageError, image_info

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/info")
async def get_image_info(file: UploadFile = File(...)) -> dict[str, int | str]:
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File too large")
    try:
        return image_info(data)
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
