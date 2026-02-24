from typing import TypedDict, Optional, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.rag.vectorstore import get_vectorstore
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

FAQ_SYSTEM_PROMPT = """Você é um assistente especialista em políticas de viagem, bagagem e documentação.
Responda com base APENAS nas informações fornecidas no contexto abaixo.
Se a informação não estiver no contexto, diga honestamente que não possui essa informação específica
e sugira que o cliente entre em contato diretamente com a companhia aérea.

Contexto:
{context}

Seja preciso, amigável e profissional. Responda sempre em português."""

FAQ_HUMAN_PROMPT = "Pergunta do cliente: {question}"


def build_faq_chain():
    """Build the RAG chain for FAQ answering."""
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.openai_api_key,
        temperature=0.1,
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", FAQ_SYSTEM_PROMPT),
        ("human", FAQ_HUMAN_PROMPT),
    ])
    return prompt | llm | StrOutputParser()


async def run_faq_agent(question: str) -> dict:
    """
    Run the FAQ RAG agent.
    Returns dict with 'answer' and 'sources'.
    """
    vectorstore = get_vectorstore()
    if vectorstore is None:
        logger.warning("faq_agent_no_vectorstore")
        return {
            "answer": "Base de conhecimento ainda não carregada. Tente novamente em instantes.",
            "sources": [],
        }

    logger.info("faq_agent_querying", question=question[:100])

    # Retrieve relevant documents
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    docs = retriever.invoke(question)
    sources = list({doc.metadata.get("source", "unknown") for doc in docs})
    context = "\n\n---\n\n".join(doc.page_content for doc in docs)

    # Generate answer
    chain = build_faq_chain()
    answer = await chain.ainvoke({"context": context, "question": question})

    logger.info("faq_agent_responded", sources=sources)
    return {"answer": answer, "sources": sources}