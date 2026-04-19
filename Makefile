.PHONY: check format lint test docker-build docker-run docker-scan

# Use uv if installed, otherwise default to direct tool calls
UV_CMD := $(shell command -v uv >/dev/null 2>&1 && echo "uv run " || echo "")

check: format lint test

format:
	$(UV_CMD)ruff format .
	$(UV_CMD)ruff check --fix .

lint:
	$(UV_CMD)ruff check .
	$(UV_CMD)bandit -r . -c "pyproject.toml" 2>/dev/null || $(UV_CMD)bandit -r main.py

test:
	$(UV_CMD)pytest -v tests/

docker-build:
	docker build -t openwrt-mcp .

docker-run:
	docker run -d \
		--name openwrt-mcp \
		-e OPENWRT_HOST=$$OPENWRT_HOST \
		-e OPENWRT_USER=$$OPENWRT_USER \
		-e OPENWRT_PASSWORD=$$OPENWRT_PASSWORD \
		openwrt-mcp

docker-scan: docker-build
	@DOCKER_HOST=$$(docker context inspect --format '{{.Endpoints.docker.Host}}' 2>/dev/null || echo "unix:///var/run/docker.sock") grype docker:openwrt-mcp
