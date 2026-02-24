"""
Shared fixtures for the blisAI test suite.

All fixtures that require external services (Redis, OpenAI, FAISS)
patch those services out so tests are fully isolated.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Environment setup — must run before any app module is imported
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """
    Inject required environment variables for every test.
    pydantic_settings.BaseSettings reads env vars when Settings() is
    instantiated (inside function calls), so this must be the first
    fixture that runs.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    monkeypatch.setenv("APP_ENV", "test")


# ---------------------------------------------------------------------------
# Singleton reset — prevents state leakage between tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Reset module-level singletons before and after each test so tests are
    independent regardless of execution order.
    """
    import app.agents.orchestrator as orch
    import app.rag.vectorstore as vs

    orch._compiled_graph = None
    orch._checkpointer = None
    vs._vectorstore = None

    yield

    orch._compiled_graph = None
    orch._checkpointer = None
    vs._vectorstore = None


# ---------------------------------------------------------------------------
# FastAPI TestClient with mocked lifespan dependencies
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_graph():
    """
    A pre-configured mock LangGraph instance.
    Returns a realistic result for faq routing.
    """
    graph = AsyncMock()
    graph.ainvoke.return_value = {
        "final_response": "A franquia de bagagem da LATAM é de 23 kg.",
        "agent_used": "faq",
        "faq_sources": ["latam_bagagem.md"],
        "search_sources": [],
    }
    return graph


@pytest.fixture
def client(mock_graph):
    """
    FastAPI TestClient with all external dependencies patched out.

    Patches applied:
    - app.rag.vectorstore.build_vectorstore: prevents FAISS/OpenAI calls on startup
    - app.agents.orchestrator.get_graph: returns mock_graph instead of real graph
    - app.api.health.aioredis: prevents real Redis connection on health checks
    """
    mock_redis_instance = AsyncMock()
    mock_redis_instance.ping = AsyncMock(return_value=True)
    mock_redis_instance.aclose = AsyncMock()

    with patch("app.rag.vectorstore.build_vectorstore"), \
         patch("app.api.chat.get_graph",
               new_callable=AsyncMock,
               return_value=mock_graph), \
         patch("app.main.get_graph",
               new_callable=AsyncMock,
               return_value=mock_graph), \
         patch("app.api.health.aioredis") as mock_aioredis:

        mock_aioredis.from_url.return_value = mock_redis_instance

        from app.main import app
        from fastapi.testclient import TestClient

        with TestClient(app) as c:
            c.mock_graph = mock_graph
            yield c
