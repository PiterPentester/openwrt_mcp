# Build stage
FROM cgr.dev/chainguard/python:latest-dev AS builder

WORKDIR /app

# Install uv for dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY README.md .

# Sync dependencies to a local .venv
RUN uv sync --no-dev

# Final runtime stage
FROM cgr.dev/chainguard/python:latest

WORKDIR /app

# Copy the virtual environment and application source
COPY --from=builder /app/.venv /app/.venv
COPY main.py .

# Ensure the virtual environment's bin is in the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Chainguard images run as a non-privileged user (python) by default
# This matches best practices for security.

# Run the app directly using the python from the virtualenv
ENTRYPOINT ["python", "main.py"]
