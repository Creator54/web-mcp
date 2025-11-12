# Web CLI Search Tool (web-mcp)

A command-line interface tool to search the web using multiple search engines (DuckDuckGo, Brave) with support for Model Context Protocol (MCP) integration and web browsing capabilities.

## Installation

### Requirements
- Python 3.8+

### Setup

```bash
# Install using uv
uv pip install -e .

# Or with pip
pip install -e .
```

## Usage

### Search Command
Basic search (defaults to DuckDuckGo):
```bash
web-search search "search query"
```

With options:
```bash
# Get 10 results
web-search search "machine learning" -n 10

# Output in JSON format
web-search search "python programming" --format json

# Output in compact JSON format
web-search search "openai" --format json-compact

# Use DuckDuckGo Lite for HTML-based search (DuckDuckGo only)
web-search search "wikipedia" --lite

# Use specific search engine (duckduckgo or brave, duckduckgo is default)
web-search search "python programming" --engine brave
```

### Browse Command
Browse a web page and extract content:
```bash
# Browse a web page
web-search browse https://example.com

# Browse with specific output format
web-search browse https://wikipedia.org --format html
```

## Examples

```bash
# Basic search (DuckDuckGo by default)
web-search search python programming

# Search with more results
web-search search "artificial intelligence" -n 8

# Get structured JSON output
web-search search "climate change" --format json -n 3

# Use Brave Search
web-search search "climate change" --engine brave -n 5

# Use DuckDuckGo Lite (HTML-based search, DuckDuckGo only)
web-search search "github" --lite -n 5

# Browse a web page
web-search browse https://en.wikipedia.org/wiki/Python_(programming_language)
```

## Dependencies

- `curl_cffi`: For making realistic browser requests with browser impersonation
- `typer`: For creating the command-line interface
- `beautifulsoup4`: For HTML parsing when using DuckDuckGo Lite
- `requests`: Fallback HTTP library
- `pydantic`: For MCP adapter type validation
- `fastmcp`: For Model Context Protocol integration
- `lxml` and `readability-lxml`: For extracting readable content from web pages

## MCP (Model Context Protocol) Integration

The tool includes MCP compatibility using fastmcp, allowing other systems (like AI agents) to use its functionality programmatically:

```python
# Using the fastmcp server
from web_mcp.fastmcp_server import search_duckduckgo_mcp, browse_web_page_mcp

# Direct function call for search (when not running as server)
result = search_duckduckgo_mcp(query="Python programming", num_results=3, format="json")
print(result)

# Direct function call for browsing (when not running as server)
result = browse_web_page_mcp(url="https://example.com", format="text")
print(result)
```

To run as an MCP server:
```bash
python -m web_mcp.fastmcp_server
```

## Brave Search API Configuration (Optional)

You can configure Brave Search with an API key for better results:

1. Get an API key from [Brave Search API Dashboard](https://api-dashboard.search.brave.com/)
2. Set the environment variable: `export BRAVE_API_KEY=your_api_key_here`

If no API key is provided, the tool automatically falls back to web scraping Brave Search results.

## License

[MIT License](./LICENSE)
