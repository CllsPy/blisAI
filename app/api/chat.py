from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import asyncio

from langchain_core.messages import HumanMessage

from app.models.schemas import ChatRequest, ChatResponse
from app.agents.orchestrator import get_graph
from app.core.logging import get_logger
from datetime import datetime

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


async def _invoke_graph(session_id: str, message: str) -> dict:
    graph = await get_graph()
    config = {"configurable": {"thread_id": session_id}}

    # Passamos apenas o delta do turno atual.
    # Campos SEM reducer (route, faq_response...) são resetados por turno — correto.
    # Campo COM reducer (messages) recebe só a nova HumanMessage — o add_messages
    # reducer ACRESCENTA ao histórico que o checkpointer restaurou do Redis.
    input_state = {
        "session_id": session_id,
        "user_message": message,
        "messages": [HumanMessage(content=message)],
        "route": None,
        "faq_response": None,
        "search_response": None,
        "faq_sources": None,
        "search_sources": None,
        "final_response": None,
        "agent_used": None,
    }
    result = await graph.ainvoke(input_state, config=config)
    return result


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Standard JSON chat endpoint."""
    logger.info("chat_request", session_id=request.session_id, message=request.message[:100])
    try:
        result = await _invoke_graph(request.session_id, request.message)
        sources = (result.get("faq_sources") or []) + (result.get("search_sources") or [])
        return ChatResponse(
            session_id=request.session_id,
            message=result.get("final_response", "Sem resposta disponível."),
            agent_used=result.get("agent_used", "orchestrator"),
            sources=sources or None,
        )
    except Exception as exc:
        logger.error("chat_error", error=str(exc), session_id=request.session_id)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(exc)}")


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """SSE streaming chat endpoint."""
    logger.info("chat_stream_request", session_id=request.session_id)

    async def event_generator():
        try:
            graph = await get_graph()
            config = {"configurable": {"thread_id": request.session_id}}
            input_state = {
                "session_id": request.session_id,
                "user_message": request.message,
                "messages": [HumanMessage(content=request.message)],
                "route": None,
                "faq_response": None,
                "search_response": None,
                "faq_sources": None,
                "search_sources": None,
                "final_response": None,
                "agent_used": None,
            }

            async for event in graph.astream_events(input_state, config=config, version="v2"):
                kind = event.get("event")
                name = event.get("name", "")

                if kind == "on_chain_end" and name == "router":
                    route = event.get("data", {}).get("output", {}).get("route", "")
                    yield f"data: {json.dumps({'type': 'status', 'content': f'Roteando para: {route}'})}\n\n"

                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

            # Final signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            logger.error("stream_error", error=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )