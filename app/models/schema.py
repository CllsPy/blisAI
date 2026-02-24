from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., min_length=1, description="User message")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "user-123",
                "message": "Qual é a franquia de bagagem da LATAM?",
            }
        }


class ChatResponse(BaseModel):
    session_id: str
    message: str
    agent_used: Literal["faq", "search", "both", "orchestrator"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sources: Optional[list[str]] = None


class AgentState(BaseModel):
    session_id: str
    user_message: str
    faq_response: Optional[str] = None
    search_response: Optional[str] = None
    final_response: Optional[str] = None
    agent_used: Optional[str] = None
    sources: Optional[list[str]] = None
    route: Optional[Literal["faq", "search", "both"]] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    redis_connected: bool
    faiss_loaded: bool