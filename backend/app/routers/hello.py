"""The endpoint ``GET /api/hello``.

No data processing: it answers a fixed greeting.
"""

from fastapi import APIRouter

router = APIRouter(tags=["hello"])


@router.get("/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello, world!"}
