#!/bin/bash

# Clean up any existing containers with the same name
docker rm -f web-mcp-server &> /dev/null || true

# Run the container in detached mode with the MCP server
docker run -d --name web-mcp-server --restart unless-stopped web-mcp

echo "Web-MCP server is running in Docker container 'web-mcp-server'"
echo "To connect an MCP client, use: docker exec -i web-mcp-server python -m web_mcp.fastmcp_server"
