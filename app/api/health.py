from fastapi import APIRouter
import redis.asyncio as aioredis
from app.core.config import get_settings
from app.rag.vectorstore import is_loaded
from app.models.schemas import HealthResponse
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    settings = get_settings()
    redis_ok = False
    try:
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception as exc:
        logger.warning("redis_health_failed", error=str(exc))

    return HealthResponse(
        status="ok",
        version=settings.app_version,
        redis_connected=redis_ok,
        faiss_loaded=is_loaded(),
    )