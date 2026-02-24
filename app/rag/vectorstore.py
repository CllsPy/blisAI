from pathlib import Path
from typing import Optional
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_vectorstore: Optional[FAISS] = None


def _load_documents(docs_path: str) -> list[Document]:
    """Load all .txt and .md documents from the FAQ data folder."""
    docs = []
    path = Path(docs_path)
    if not path.exists():
        logger.warning("docs_path_not_found", path=str(path))
        return docs

    for file in path.glob("**/*.txt"):
        text = file.read_text(encoding="utf-8")
        docs.append(Document(page_content=text, metadata={"source": file.name}))

    for file in path.glob("**/*.md"):
        text = file.read_text(encoding="utf-8")
        docs.append(Document(page_content=text, metadata={"source": file.name}))

    logger.info("documents_loaded", count=len(docs))
    return docs


def build_vectorstore(force_rebuild: bool = False) -> FAISS:
    """Build or load FAISS vector store."""
    global _vectorstore
    settings = get_settings()
    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )
    index_path = Path(settings.faiss_index_path)

    if not force_rebuild and index_path.exists():
        logger.info("loading_existing_faiss_index", path=str(index_path))
        _vectorstore = FAISS.load_local(
            str(index_path), embeddings, allow_dangerous_deserialization=True
        )
        return _vectorstore

    logger.info("building_faiss_index")
    documents = _load_documents(settings.docs_path)
    if not documents:
        raise ValueError(
            f"No documents found in {settings.docs_path}. "
            "Please add .txt or .md files to the docs/faq_data folder."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(documents)
    logger.info("chunks_created", count=len(chunks))

    _vectorstore = FAISS.from_documents(chunks, embeddings)
    index_path.mkdir(parents=True, exist_ok=True)
    _vectorstore.save_local(str(index_path))
    logger.info("faiss_index_saved", path=str(index_path))
    return _vectorstore


def get_vectorstore() -> Optional[FAISS]:
    return _vectorstore


def is_loaded() -> bool:
    return _vectorstore is not None