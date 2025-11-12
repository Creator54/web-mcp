"""
MCP (Model Context Protocol) server for web search using multiple engines
"""

from fastmcp import FastMCP
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum
import json


class OutputFormat(str, Enum):
    text = "text"
    json = "json"
    json_compact = "json-compact"


# Create the MCP server
mcp = FastMCP("Web Search Tool 🌐")


def _perform_search(query: str, num_results: int = 5, format: OutputFormat = OutputFormat.text, search_engine: str = "duckduckgo"):
    """
    Internal function to perform the actual search
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
        if results:
            formatted_result = f"Search results for: {query} ({search_engine})\n\n"
            for i, result in enumerate(results, 1):
                title = result.get('title', 'No title')
                link = result.get('link', '')
                snippet = result.get('snippet', '')
                
                formatted_result += f"{i}. {title}\n"
                formatted_result += f"   {link}\n"
                if snippet:
                    formatted_result += f"   {snippet}\n"
                formatted_result += "\n"
            return {"text_output": formatted_result}
        else:
            return {"text_output": "No results found or error occurred."}


def _perform_browse(url: str, format: OutputFormat = OutputFormat.text):
    """
    Internal function to perform the actual browsing
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


@mcp.tool
def search(query: str = Field(..., description="The search query to execute on the web"),
           num_results: int = Field(5, ge=1, le=20, description="Number of results to return (1-20)"),
           format: OutputFormat = Field(OutputFormat.text, description="Output format"),
           search_engine: str = Field("duckduckgo", description="Search engine to use: duckduckgo or brave")) -> dict:
    """
    Search the web and return results
    """
    return _perform_search(query, num_results, format, search_engine)





@mcp.tool
def browse(url: str = Field(..., description="The URL to browse and extract content from"),
           format: OutputFormat = Field(OutputFormat.text, description="Output format for the page content")) -> dict:
    """
    Browse a web page and extract its content
    """
    return _perform_browse(url, format)


# Make the internal functions available for direct use if needed
def search_duckduckgo_mcp(query: str, num_results: int = 5, format: str = "json") -> dict:
    """
    Direct function to perform search without using the MCP decorator
    """
    format_enum = OutputFormat(format)
    return _perform_search(query, num_results, format_enum)


def browse_web_page_mcp(url: str, format: str = "text") -> dict:
    """
    Direct function to browse a web page without using the MCP decorator
    """
    format_enum = OutputFormat(format)
    return _perform_browse(url, format_enum)


if __name__ == "__main__":
    mcp.run()