from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas.health import DatabaseHealth, HealthResponse


def check_health(db: Session) -> HealthResponse:
    settings = get_settings()
    dialect = db.bind.dialect.name if db.bind is not None else "unknown"

    try:
        db.execute(text("SELECT 1"))
        database = DatabaseHealth(status="ok", dialect=dialect)
    except Exception:
        database = DatabaseHealth(status="error", dialect=dialect)

    overall = "ok" if database.status == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        database=database,
    )
