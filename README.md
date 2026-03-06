# Web MCP

CLI tool for web search (DuckDuckGo, Brave) and browsing with MCP integration.

## Install

```bash
pip install git+https://github.com/creator54/web-mcp.git
# or
uv pip install git+https://github.com/creator54/web-mcp.git
```

## Usage

```bash
# Search (direct or subcommand)
web search "query"
web "query" -n 10 --engine brave --format json

# Browse (flag or subcommand)
web -b https://example.com
web browse https://example.com
```

## MCP Server

```bash
python -m web_mcp.fastmcp_server
```

## Docker

```bash
docker build -t web-mcp .
docker run -i web-mcp python -m web_mcp.fastmcp_server
```

## License

[MIT](./LICENSE)
