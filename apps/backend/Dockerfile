FROM python:3.12-slim

# 시스템 의존성 (ffmpeg: 카카오톡 m4a 변환용)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 의존성 먼저 설치 (캐시 활용)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# 소스 복사
COPY alembic.ini ./
COPY alembic/ alembic/
COPY src/ src/

EXPOSE 8000

# 시작 시 마이그레이션 자동 실행 → 서버 시작
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn src.main:app --host 0.0.0.0 --port 8000"]
