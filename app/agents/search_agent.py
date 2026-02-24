from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.tools.search import get_search_tool
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SEARCH_SYSTEM_PROMPT = """Você é um assistente de viagens especializado em buscar informações atualizadas.
Com base nos resultados de busca abaixo, responda a pergunta do cliente de forma clara e concisa.
Sempre mencione que os preços e disponibilidades podem variar e recomende confirmar diretamente com a companhia.

Resultados da busca:
{search_results}

Responda em português, de forma amigável e profissional."""

SEARCH_HUMAN_PROMPT = "Pergunta: {question}"


async def run_search_agent(question: str) -> dict:
    """
    Run the web search agent.
    Returns dict with 'answer' and 'sources'.
    """
    settings = get_settings()
    logger.info("search_agent_querying", question=question[:100])

    search_tool = get_search_tool()
    results = await search_tool.ainvoke(question)

    # Format results
    formatted = ""
    sources = []
    if isinstance(results, list):
        for i, r in enumerate(results, 1):
            if isinstance(r, dict):
                formatted += f"\n[{i}] {r.get('title', '')}\n{r.get('content', '')}\n"
                if url := r.get("url"):
                    sources.append(url)
    else:
        formatted = str(results)

    llm = ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.openai_api_key,
        temperature=0.3,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", SEARCH_SYSTEM_PROMPT),
        ("human", SEARCH_HUMAN_PROMPT),
    ])
    chain = prompt | llm | StrOutputParser()
    answer = await chain.ainvoke({"search_results": formatted, "question": question})

    logger.info("search_agent_responded", source_count=len(sources))
    return {"answer": answer, "sources": sources}