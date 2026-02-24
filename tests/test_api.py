"""
Test suite for blisAI API endpoints and core logic.

Run with: pytest tests/ -v

Test organization:
  - TestHealth:           /health endpoint behavior
  - TestChat:             /chat endpoint behavior
  - TestSchemas:          Pydantic model validation
  - TestRouteEdge:        route_edge() pure function
  - TestConsolidateNode:  consolidate_node() branching logic
  - TestVectorstore:      is_loaded() / get_vectorstore() module state
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Health Endpoint
# =============================================================================

class TestHealth:
    """Tests for GET /health"""

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_has_required_fields(self, client):
        data = client.get("/health").json()
        assert "status" in data
        assert "version" in data
        assert "redis_connected" in data
        assert "faiss_loaded" in data

    def test_health_status_is_ok(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_redis_connected_when_redis_available(self, client):
        data = client.get("/health").json()
        assert data["redis_connected"] is True

    def test_health_redis_disconnected_when_redis_unavailable(self, set_env_vars):
        with patch("app.rag.vectorstore.build_vectorstore"), \
             patch("app.api.chat.get_graph", new_callable=AsyncMock), \
             patch("app.main.get_graph", new_callable=AsyncMock), \
             patch("app.api.health.aioredis") as mock_aioredis:

            mock_aioredis.from_url.side_effect = ConnectionError("refused")

            from app.main import app
            from fastapi.testclient import TestClient
            with TestClient(app) as c:
                data = c.get("/health").json()

        assert data["redis_connected"] is False

    def test_health_faiss_loaded_false_by_default(self, client):
        data = client.get("/health").json()
        assert data["faiss_loaded"] is False

    def test_health_faiss_loaded_true_when_vectorstore_set(self, set_env_vars):
        import app.rag.vectorstore as vs

        mock_redis_instance = AsyncMock()
        mock_redis_instance.ping = AsyncMock(return_value=True)
        mock_redis_instance.aclose = AsyncMock()

        with patch("app.rag.vectorstore.build_vectorstore"), \
             patch("app.api.chat.get_graph", new_callable=AsyncMock), \
             patch("app.main.get_graph", new_callable=AsyncMock), \
             patch("app.api.health.aioredis") as mock_aioredis:

            mock_aioredis.from_url.return_value = mock_redis_instance
            vs._vectorstore = MagicMock()

            from app.main import app
            from fastapi.testclient import TestClient
            with TestClient(app) as c:
                data = c.get("/health").json()

        assert data["faiss_loaded"] is True


# =============================================================================
# Chat Endpoint
# =============================================================================

class TestChat:
    """Tests for POST /chat"""

    def test_chat_returns_200_for_valid_request(self, client):
        resp = client.post("/chat", json={
            "session_id": "session-001",
            "message": "Qual a franquia de bagagem da LATAM?"
        })
        assert resp.status_code == 200

    def test_chat_response_contains_session_id(self, client):
        resp = client.post("/chat", json={
            "session_id": "session-abc",
            "message": "Qual a franquia de bagagem da LATAM?"
        })
        assert resp.json()["session_id"] == "session-abc"

    def test_chat_response_contains_message(self, client):
        data = client.post("/chat", json={
            "session_id": "s1",
            "message": "Qual a franquia de bagagem da LATAM?"
        }).json()
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0

    def test_chat_response_agent_used_is_valid(self, client):
        data = client.post("/chat", json={
            "session_id": "s1",
            "message": "Qual a franquia de bagagem da LATAM?"
        }).json()
        assert data["agent_used"] in ("faq", "search", "both", "orchestrator")

    def test_chat_response_sources_are_list_or_none(self, client):
        data = client.post("/chat", json={
            "session_id": "s1",
            "message": "Qual a franquia de bagagem da LATAM?"
        }).json()
        assert data.get("sources") is None or isinstance(data["sources"], list)

    def test_chat_returns_faq_agent_used(self, client):
        data = client.post("/chat", json={
            "session_id": "s1",
            "message": "Qual a franquia de bagagem da LATAM?"
        }).json()
        assert data["agent_used"] == "faq"

    def test_chat_returns_combined_sources(self, client):
        client.mock_graph.ainvoke.return_value = {
            "final_response": "Resposta combinada.",
            "agent_used": "both",
            "faq_sources": ["doc1.md"],
            "search_sources": ["https://example.com/result"],
        }
        data = client.post("/chat", json={
            "session_id": "s2",
            "message": "Voos baratos para Paris"
        }).json()
        assert "doc1.md" in data["sources"]
        assert "https://example.com/result" in data["sources"]
        assert data["agent_used"] == "both"

    def test_chat_returns_500_on_graph_error(self, client):
        client.mock_graph.ainvoke.side_effect = RuntimeError("Graph exploded")
        resp = client.post("/chat", json={
            "session_id": "s3",
            "message": "Alguma pergunta"
        })
        assert resp.status_code == 500

    def test_chat_returns_422_for_empty_message(self, client):
        resp = client.post("/chat", json={"session_id": "s1", "message": ""})
        assert resp.status_code == 422

    def test_chat_returns_422_for_missing_message(self, client):
        resp = client.post("/chat", json={"session_id": "s1"})
        assert resp.status_code == 422

    def test_chat_returns_422_for_missing_session_id(self, client):
        resp = client.post("/chat", json={"message": "Hello"})
        assert resp.status_code == 422

    def test_chat_response_has_timestamp(self, client):
        data = client.post("/chat", json={
            "session_id": "s1",
            "message": "Test"
        }).json()
        assert "timestamp" in data


# =============================================================================
# Schema Validation
# =============================================================================

class TestSchemas:
    """Tests for Pydantic model validation in app/models/schemas.py"""

    def test_chat_request_valid(self):
        from app.models.schemas import ChatRequest
        req = ChatRequest(session_id="s1", message="hello world")
        assert req.session_id == "s1"
        assert req.message == "hello world"

    def test_chat_request_empty_message_raises_validation_error(self):
        from app.models.schemas import ChatRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ChatRequest(session_id="s1", message="")

    def test_chat_request_missing_message_raises_validation_error(self):
        from app.models.schemas import ChatRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ChatRequest(session_id="s1")

    def test_chat_request_missing_session_id_raises_validation_error(self):
        from app.models.schemas import ChatRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ChatRequest(message="hello")

    def test_chat_response_valid(self):
        from app.models.schemas import ChatResponse
        resp = ChatResponse(session_id="s1", message="answer", agent_used="faq")
        assert resp.session_id == "s1"
        assert resp.agent_used == "faq"
        assert resp.sources is None

    def test_chat_response_invalid_agent_used_raises_validation_error(self):
        from app.models.schemas import ChatResponse
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ChatResponse(session_id="s1", message="x", agent_used="invalid_agent")

    def test_chat_response_timestamp_is_set_automatically(self):
        from app.models.schemas import ChatResponse
        from datetime import datetime
        resp = ChatResponse(session_id="s1", message="x", agent_used="faq")
        assert isinstance(resp.timestamp, datetime)

    def test_health_response_valid(self):
        from app.models.schemas import HealthResponse
        resp = HealthResponse(
            status="ok",
            version="1.0.0",
            redis_connected=True,
            faiss_loaded=False,
        )
        assert resp.status == "ok"
        assert resp.redis_connected is True
        assert resp.faiss_loaded is False


# =============================================================================
# route_edge Logic
# =============================================================================

class TestRouteEdge:
    """
    Tests for the pure synchronous route_edge() function.
    No external dependencies — no mocking needed.
    """

    def _make_state(self, route):
        return {
            "session_id": "test",
            "user_message": "question",
            "route": route,
            "faq_response": None,
            "search_response": None,
            "faq_sources": None,
            "search_sources": None,
            "final_response": None,
            "agent_used": None,
        }

    def test_route_faq_returns_faq_node(self):
        from app.agents.orchestrator import route_edge
        assert route_edge(self._make_state("faq")) == "faq_node"

    def test_route_search_returns_search_node(self):
        from app.agents.orchestrator import route_edge
        assert route_edge(self._make_state("search")) == "search_node"

    def test_route_both_returns_both_node(self):
        from app.agents.orchestrator import route_edge
        assert route_edge(self._make_state("both")) == "both_node"

    def test_route_unknown_defaults_to_faq_node(self):
        from app.agents.orchestrator import route_edge
        assert route_edge(self._make_state("unknown_value")) == "faq_node"

    def test_route_none_defaults_to_faq_node(self):
        from app.agents.orchestrator import route_edge
        assert route_edge(self._make_state(None)) == "faq_node"


# =============================================================================
# consolidate_node Logic
# =============================================================================

class TestConsolidateNode:
    """
    Tests for consolidate_node() branching logic.

    Three of four branches make no LLM calls:
    - faq-only  → returns immediately with agent_used="faq"
    - search-only → returns immediately with agent_used="search"
    - neither   → returns fallback with agent_used="orchestrator"

    The "both" branch calls ChatOpenAI and is tested with a patched chain.
    """

    def _make_state(self, faq_response=None, search_response=None,
                    faq_sources=None, search_sources=None):
        return {
            "session_id": "test-session",
            "user_message": "Qual a franquia de bagagem?",
            "route": "faq",
            "faq_response": faq_response,
            "search_response": search_response,
            "faq_sources": faq_sources or [],
            "search_sources": search_sources or [],
            "final_response": None,
            "agent_used": None,
        }

    async def test_faq_only_returns_faq_response(self):
        from app.agents.orchestrator import consolidate_node
        state = self._make_state(faq_response="Resposta FAQ aqui.")
        result = await consolidate_node(state)
        assert result["final_response"] == "Resposta FAQ aqui."
        assert result["agent_used"] == "faq"

    async def test_faq_only_preserves_original_state(self):
        from app.agents.orchestrator import consolidate_node
        state = self._make_state(faq_response="FAQ answer", faq_sources=["doc.md"])
        result = await consolidate_node(state)
        assert result["session_id"] == "test-session"
        assert result["faq_sources"] == ["doc.md"]

    async def test_search_only_returns_search_response(self):
        from app.agents.orchestrator import consolidate_node
        state = self._make_state(search_response="Resposta busca aqui.")
        result = await consolidate_node(state)
        assert result["final_response"] == "Resposta busca aqui."
        assert result["agent_used"] == "search"

    async def test_neither_returns_fallback_message(self):
        from app.agents.orchestrator import consolidate_node
        state = self._make_state()
        result = await consolidate_node(state)
        assert result["agent_used"] == "orchestrator"
        assert isinstance(result["final_response"], str)
        assert len(result["final_response"]) > 0

    async def test_both_responses_sets_agent_used_both(self):
        """
        When both faq and search responses exist, agent_used must be "both"
        and a LLM consolidation is triggered (patched here via RunnableLambda).
        """
        from app.agents.orchestrator import consolidate_node
        from langchain_core.runnables import RunnableLambda
        from langchain_core.messages import AIMessage

        async def fake_llm(messages):
            return AIMessage(content="Resposta consolidada.")

        with patch("app.agents.orchestrator.ChatOpenAI") as mock_llm_cls:
            mock_llm_cls.return_value = RunnableLambda(fake_llm)

            state = self._make_state(
                faq_response="Resposta FAQ.",
                search_response="Resposta busca.",
            )
            result = await consolidate_node(state)

        assert result["agent_used"] == "both"
        assert result["final_response"] == "Resposta consolidada."


# =============================================================================
# Vectorstore State
# =============================================================================

class TestVectorstore:
    """
    Tests for is_loaded() and get_vectorstore() in app/rag/vectorstore.py.
    The reset_singletons autouse fixture ensures _vectorstore=None before each test.
    """

    def test_is_loaded_returns_false_when_not_set(self):
        from app.rag.vectorstore import is_loaded
        assert is_loaded() is False

    def test_get_vectorstore_returns_none_when_not_set(self):
        from app.rag.vectorstore import get_vectorstore
        assert get_vectorstore() is None

    def test_is_loaded_returns_true_when_vectorstore_set(self):
        import app.rag.vectorstore as vs
        from app.rag.vectorstore import is_loaded
        vs._vectorstore = MagicMock()
        assert is_loaded() is True

    def test_get_vectorstore_returns_set_instance(self):
        import app.rag.vectorstore as vs
        from app.rag.vectorstore import get_vectorstore
        mock_vs = MagicMock()
        vs._vectorstore = mock_vs
        assert get_vectorstore() is mock_vs

    def test_is_loaded_returns_false_after_reset(self):
        import app.rag.vectorstore as vs
        from app.rag.vectorstore import is_loaded
        vs._vectorstore = MagicMock()
        assert is_loaded() is True
        vs._vectorstore = None
        assert is_loaded() is False
