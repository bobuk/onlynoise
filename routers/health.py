import time
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class HealthResponse(BaseModel):
    status: str = Field(..., description="The status of the service")
    time: int = Field(..., description="The time the service was checked")


@router.get("/health")
def health():
    return {"status": "ok", "time": int(time.time())}
