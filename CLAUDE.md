# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Blis AI is a FastAPI REST API with a LangGraph-based multi-agent system designed to answer travel-related questions. Two agents collaborate: a **FAQ agent** (RAG over local documents) and a **Search agent** (real-time web search via Tavily). An LLM-based router decides which agent(s) to invoke.

## Commands

### Run locally
```bash
# Start Redis first (required for conversation checkpointing)
docker-compose up redis -d

# Install package in editable mode (required for `app.*` imports)
pip install -e .

# Start the API server with hot reload
uvicorn app.main:app --reload
```

### Run with Docker (full stack)
```bash
docker-compose up --build
```

### Run tests
```bash
pytest                          # all tests
pytest tests/test_api.py -k "test_chat"   # single test by name
pytest -v                       # verbose output
```

All tests are fully isolated — external services (Redis, OpenAI, FAISS) are patched in `tests/conftest.py`. No real API keys needed to run tests.

### Rebuild the FAISS index
```bash
# Delete the cached index to force a rebuild on next startup
rm -rf data/faiss_index/
```

## Required Environment Variables

Copy `.env` and populate:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (used for embeddings + LLM) |
| `TAVILY_API_KEY` | Tavily API key (used for web search) |
| `REDIS_URL` | Redis connection string (default: `redis://localhost:6379`) |

Optional: `APP_ENV`, `LOG_LEVEL`, `FAISS_INDEX_PATH`, `DOCS_PATH`, `LLM_MODEL`, `EMBEDDING_MODEL`, `CHUNK_SIZE`, `CHUNK_OVERLAP`.

## Architecture

### Request Flow

```
POST /chat  →  chat.py  →  orchestrator.get_graph()
                              │
                    GraphState (TypedDict)
                              │
                           router_node   ← LLM classifies: "faq" | "search" | "both"
                          /    |    \
                    faq_node  search_node  both_node (parallel asyncio.gather)
                          \    |    /
                         consolidate_node  ← LLM merges if "both"
                              │
                            END  →  ChatResponse
```

### Key Modules

- **[app/main.py](app/main.py)** — FastAPI app factory. On startup: builds FAISS vectorstore + initializes LangGraph compiled graph (both are singletons).
- **[app/agents/orchestrator.py](app/agents/orchestrator.py)** — LangGraph `StateGraph` with `GraphState`. Holds two module-level singletons: `_compiled_graph` and `_checkpointer`. Redis checkpointer enables multi-turn conversation memory per `session_id` (thread_id). Falls back to `MemorySaver` if Redis is unavailable.
- **[app/agents/faq_agent.py](app/agents/faq_agent.py)** — RAG agent: retrieves top-4 docs from FAISS, builds context, calls LLM.
- **[app/agents/search_agent.py](app/agents/search_agent.py)** — Web search agent: calls Tavily, formats results, calls LLM.
- **[app/rag/vectorstore.py](app/rag/vectorstore.py)** — FAISS vectorstore singleton. On startup: loads from `data/faiss_index/` if it exists, otherwise builds from `.txt`/`.md` files in `docs/faq_data/` and saves to disk.
- **[app/core/config.py](app/core/config.py)** — `pydantic-settings` `Settings` class. All config is read from environment or `.env`. Default LLM: `gpt-4o-mini`, embedding: `text-embedding-3-small`.
- **[app/api/chat.py](app/api/chat.py)** — Two endpoints: `POST /chat` (JSON) and `POST /chat/stream` (SSE via `astream_events`).
- **[app/models/schemas.py](app/models/schemas.py)** — Pydantic models: `ChatRequest`, `ChatResponse`, `HealthResponse`.
- **[docs/faq_data/](docs/faq_data/)** — Source documents for the RAG knowledge base. Add `.txt` or `.md` files here and delete `data/faiss_index/` to trigger a rebuild.

### Singleton Pattern

Three module-level singletons are used for performance:
- `app.agents.orchestrator._compiled_graph` / `_checkpointer`
- `app.rag.vectorstore._vectorstore`

Tests in `conftest.py` reset all three before and after each test to prevent state leakage.

### Conversation Memory

Each request includes a `session_id`. This maps to LangGraph's `thread_id` in the checkpointer config. Redis persists state across requests within the same session.

## Testing Patterns

- `tests/conftest.py` patches `build_vectorstore`, `get_graph`, and `aioredis` so no external calls are made.
- The `client` fixture is a `fastapi.testclient.TestClient` with mocked lifespan.
- `pytest-asyncio` is configured with `asyncio_mode = auto` — no `@pytest.mark.asyncio` needed.
- Inject custom `mock_graph.ainvoke.return_value` to test different routing outcomes.
