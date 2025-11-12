FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies needed for curl_cffi and other packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    build-essential \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libz-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project requirements
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copy project
COPY . .

# Expose port for MCP server (if needed in the future)
EXPOSE 8000

# Default command to run the MCP server
CMD ["python", "-m", "web_mcp.fastmcp_server"]