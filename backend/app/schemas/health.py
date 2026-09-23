from typing import Literal

from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    status: Literal["ok", "error"]
    dialect: str


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app_name: str
    version: str
    environment: str
    llm_provider: str = Field(..., description="Configured provider name; unused until LLM phase")
    llm_model: str
    database: DatabaseHealth
