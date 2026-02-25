from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal
from datetime import datetime, timezone


class ChatRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "session_id": "user-123",
            "message": "Qual é a franquia de bagagem da LATAM?",
        }
    })

    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., min_length=1, description="User message")


class ChatResponse(BaseModel):
    session_id: str
    message: str
    agent_used: Literal["faq", "search", "both", "orchestrator"]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sources: Optional[list[str]] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    redis_connected: bool
    faiss_loaded: bool