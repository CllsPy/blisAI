from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import BaseTool
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_search_tool(max_results: int = 5) -> BaseTool:
    """Return a configured Tavily search tool."""
    settings = get_settings()
    tool = TavilySearchResults(
        max_results=max_results,
        tavily_api_key=settings.tavily_api_key,
        description=(
            "Useful for searching real-time information about flight prices, "
            "airline policies, travel news, visa requirements, and current events."
        ),
    )
    logger.info("search_tool_initialized", provider="tavily", max_results=max_results)
    return tool