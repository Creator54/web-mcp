"""
MCP (Model Context Protocol) server for web search using multiple engines
"""

from fastmcp import FastMCP
from pydantic import Field
from enum import Enum


class OutputFormat(str, Enum):
    text = "text"
    json = "json"
    json_compact = "json-compact"


# Create the MCP server
mcp = FastMCP("Web Search Tool 🌐")


@mcp.tool
def search(query: str = Field(..., description="The search query to execute on the web"),
           num_results: int = Field(5, ge=1, le=20, description="Number of results to return (1-20)"),
           format: OutputFormat = Field(OutputFormat.text, description="Output format"),
           search_engine: str = Field("duckduckgo", description="Search engine to use: duckduckgo or brave")) -> dict:
    """
    Search the web and return results
    """
    from web_mcp.cli import search_duckduckgo, search_duckduckgo_lite, search_brave

    # Perform search based on selected engine
    if search_engine.lower() == 'brave':
        results = search_brave(query, num_results)
    else:  # default to duckduckgo
        # Try the main API method first
        results = search_duckduckgo(query, num_results)
        
        # If no results from API, fall back to lite method
        if not results:
            results = search_duckduckgo_lite(query, num_results)

    search_result = {
        "query": query,
        "results": results,
        "count": len(results),
        "engine": search_engine
    }
    
    if format == OutputFormat.json:
        return search_result
    elif format == OutputFormat.json_compact:
        return results
    else:  # text format
        from web_mcp.cli import format_search_results
        return {"text_output": format_search_results(results, query, search_engine)}


@mcp.tool
def browse(url: str = Field(..., description="The URL to browse and extract content from"),
           format: OutputFormat = Field(OutputFormat.text, description="Output format for the page content")) -> dict:
    """
    Browse a web page and extract its content
    """
    from web_mcp.cli import browse_web_page
    
    result = browse_web_page(url, format.value)
    
    if 'error' in result:
        return {"error": result['error']}
    
    if format == OutputFormat.text:
        return {
            "title": result['title'],
            "url": result['url'],
            "content": result['content']
        }
    else:  # html format
        return {
            "title": result['title'],
            "url": result['url'],
            "html_content": result['content']
        }


if __name__ == "__main__":
    mcp.run()