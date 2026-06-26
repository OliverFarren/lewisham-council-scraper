from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_bins() -> dict[str, str]:
    """Placeholder — will return bin collection schedule for a given address."""
    return {"message": "bins endpoint placeholder"}
