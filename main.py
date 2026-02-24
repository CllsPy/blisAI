from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.rag.vectorstore import build_vectorstore
from app.agents.orchestrator import get_graph
from app.api import chat, health

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    logger.info("app_starting", env=settings.app_env, version=settings.app_version)

    try:
        build_vectorstore()
        logger.info("vectorstore_ready")
    except Exception as exc:
        logger.error("vectorstore_failed", error=str(exc))

    try:
        await get_graph()
        logger.info("graph_ready")
    except Exception as exc:
        logger.error("graph_failed", error=str(exc))

    yield

    logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Multi-agent AI system for travel agencies — Blis AI",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(chat.router)

    return app


app = create_app()