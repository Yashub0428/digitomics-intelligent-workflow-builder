from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.health import HealthResponse
from app.services.health import check_health

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness and configuration check",
)
def health(db: Session = Depends(get_db)) -> JSONResponse:
    payload = check_health(db)
    status_code = 200 if payload.status == "ok" else 503
    return JSONResponse(status_code=status_code, content=payload.model_dump())
