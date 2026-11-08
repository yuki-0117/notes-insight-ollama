# 這個 Dockerfile 只打包「呼叫 Ollama 的 Python 程式」本身。
# 本地模型的部分由 docker-compose.yml 裡另一個 ollama 服務負責，
# 兩者透過內部網路溝通（app 用 OLLAMA_HOST=http://ollama:11434 連過去）。
FROM python:3.12-slim

# 安裝 uv（官方建議的安裝方式：直接把 uv 執行檔複製進來，不需要額外下載工具）
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

WORKDIR /app

# 先只複製相依套件定義，善用 Docker layer cache：
# 只要 pyproject.toml / uv.lock 沒變，之後改程式碼不用重新安裝套件
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# 再複製其餘程式碼
COPY . .
RUN uv sync --frozen

ENV PYTHONUNBUFFERED=1

# 預設直接開一個互動 shell 說明可用指令；實際執行時用
# `docker compose run --rm app uv run python -m notes_extractor run-all`
CMD ["uv", "run", "python", "-m", "notes_extractor", "--help"]
