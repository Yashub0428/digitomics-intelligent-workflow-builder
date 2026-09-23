from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import SessionLocal
from app.services.llm import LLMProvider, get_llm_provider
from app.services.orchestrator import ConversationOrchestrator


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_llm_provider_dep(
    settings: Settings = Depends(get_settings),
) -> LLMProvider:
    return get_llm_provider(settings)


def get_orchestrator(
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider_dep),
) -> ConversationOrchestrator:
    return ConversationOrchestrator(
        db=db,
        llm_provider=provider,
    )
