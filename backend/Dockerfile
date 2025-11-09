# https://cloud.google.com/blog/topics/developers-practitioners/build-and-deploy-a-remote-mcp-server-to-google-cloud-run-in-under-10-minutes
# Use the official Python lightweight image
FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install the project into /app
COPY . /app
WORKDIR /app

# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN uv sync

EXPOSE $PORT

# Run the FastMCP server
CMD ["uv", "run", "server.py"]
