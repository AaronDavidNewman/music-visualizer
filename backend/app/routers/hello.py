from fastapi import APIRouter

router = APIRouter(tags=["hello"])


@router.get("/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello, world!"}
