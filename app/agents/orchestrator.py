"""
Orchestrator Agent — LangGraph-based multi-agent orchestration.

Graph flow:
  START → router → [faq_node | search_node | both (parallel)] → consolidate → END
"""
from typing import TypedDict, Optional, Literal, Annotated
import asyncio

from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.agents.faq_agent import run_faq_agent
from app.agents.search_agent import run_search_agent
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─── State ────────────────────────────────────────────────────────────────────

class GraphState(TypedDict):
    session_id: str
    # Histórico acumulado via reducer — o checkpointer persiste isso entre turnos
    messages: Annotated[list[BaseMessage], add_messages]
    user_message: str          # mensagem do turno atual (conveniência para os nós)
    route: Optional[Literal["faq", "search", "both"]]
    faq_response: Optional[str]
    search_response: Optional[str]
    faq_sources: Optional[list[str]]
    search_sources: Optional[list[str]]
    final_response: Optional[str]
    agent_used: Optional[str]


# ─── Routing ─────────────────────────────────────────────────────────────────

ROUTER_PROMPT = """Você é um roteador de perguntas de viagem. Classifique a pergunta abaixo em UMA das categorias:

- "faq": perguntas sobre políticas de bagagem, documentação, check-in, regras de voo, franquias, animais, itens proibidos
- "search": perguntas sobre preços atuais, disponibilidade de voos, notícias recentes, novidades de companhias
- "both": perguntas que precisam tanto de políticas quanto de informações em tempo real

Responda APENAS com uma dessas palavras: faq, search, both

Pergunta: {question}"""


async def router_node(state: GraphState) -> GraphState:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.openai_api_key,
        temperature=0,
    )
    prompt = ChatPromptTemplate.from_messages([("human", ROUTER_PROMPT)])
    chain = prompt | llm | StrOutputParser()
    route_raw = await chain.ainvoke({"question": state["user_message"]})
    route = route_raw.strip().lower()
    if route not in ("faq", "search", "both"):
        route = "faq"

    logger.info("router_decision", route=route, session_id=state["session_id"])
    return {**state, "route": route}


def route_edge(state: GraphState) -> Literal["faq_node", "search_node", "both_node"]:
    mapping = {
        "faq": "faq_node",
        "search": "search_node",
        "both": "both_node",
    }
    return mapping.get(state["route"], "faq_node")


# ─── Agent Nodes ──────────────────────────────────────────────────────────────

async def faq_node(state: GraphState) -> GraphState:
    result = await run_faq_agent(state["user_message"])
    return {**state, "faq_response": result["answer"], "faq_sources": result["sources"]}


async def search_node(state: GraphState) -> GraphState:
    result = await run_search_agent(state["user_message"])
    return {**state, "search_response": result["answer"], "search_sources": result["sources"]}


async def both_node(state: GraphState) -> GraphState:
    faq_result, search_result = await asyncio.gather(
        run_faq_agent(state["user_message"]),
        run_search_agent(state["user_message"]),
    )
    return {
        **state,
        "faq_response": faq_result["answer"],
        "faq_sources": faq_result["sources"],
        "search_response": search_result["answer"],
        "search_sources": search_result["sources"],
    }


# ─── Consolidation ───────────────────────────────────────────────────────────

CONSOLIDATE_PROMPT = """Você é um assistente de viagens. Consolide as respostas abaixo em uma única resposta coesa para o cliente.
Seja claro, amigável e profissional. Remova redundâncias. Responda em português.

{content}

Pergunta original: {question}"""


async def consolidate_node(state: GraphState) -> GraphState:
    settings = get_settings()

    faq = state.get("faq_response")
    search = state.get("search_response")

    if faq and search:
        content = f"Informação da base de conhecimento:\n{faq}\n\nInformação da busca em tempo real:\n{search}"
        agent_used = "both"
    elif faq:
        # add_messages reducer vai ACRESCENTAR ao histórico existente no checkpoint
        return {**state, "final_response": faq, "agent_used": "faq",
                "messages": [AIMessage(content=faq)]}
    elif search:
        return {**state, "final_response": search, "agent_used": "search",
                "messages": [AIMessage(content=search)]}
    else:
        fallback = "Não foi possível encontrar uma resposta. Por favor, tente novamente."
        return {
            **state,
            "final_response": fallback,
            "agent_used": "orchestrator",
            "messages": [AIMessage(content=fallback)],
        }

    llm = ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.openai_api_key,
        temperature=0.2,
    )
    prompt = ChatPromptTemplate.from_messages([("human", CONSOLIDATE_PROMPT)])
    chain = prompt | llm | StrOutputParser()
    final = await chain.ainvoke({"content": content, "question": state["user_message"]})

    # Grava a resposta consolidada no histórico — o checkpointer persiste isso no Redis
    return {**state, "final_response": final, "agent_used": agent_used,
            "messages": [AIMessage(content=final)]}


# ─── Graph Builder ────────────────────────────────────────────────────────────

def build_graph(checkpointer) -> StateGraph:
    graph = StateGraph(GraphState)

    graph.add_node("router", router_node)
    graph.add_node("faq_node", faq_node)
    graph.add_node("search_node", search_node)
    graph.add_node("both_node", both_node)
    graph.add_node("consolidate", consolidate_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", route_edge, {
        "faq_node": "faq_node",
        "search_node": "search_node",
        "both_node": "both_node",
    })
    graph.add_edge("faq_node", "consolidate")
    graph.add_edge("search_node", "consolidate")
    graph.add_edge("both_node", "consolidate")
    graph.add_edge("consolidate", END)

    return graph.compile(checkpointer=checkpointer)


# ─── Compiled Graph Singleton ─────────────────────────────────────────────────

_compiled_graph = None
_checkpointer = None


async def get_graph():
    global _compiled_graph, _checkpointer
    if _compiled_graph is not None:
        return _compiled_graph

    settings = get_settings()
    try:
        _checkpointer = AsyncRedisSaver(redis_url=settings.redis_url)
        await _checkpointer.asetup()
        logger.info("checkpointer_redis_connected")
    except Exception as exc:
        logger.warning("redis_unavailable_fallback_memory", error=str(exc))
        _checkpointer = MemorySaver()

    _compiled_graph = build_graph(_checkpointer)
    return _compiled_graph