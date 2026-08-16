FROM python:3.12-slim

# 시스템 의존성 (ffmpeg: 카카오톡 m4a 변환용)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# uv 설치 — 태그 고정. :latest 면 같은 커밋이 서로 다른 uv 로 빌드될 수 있다.
# 0.10.4 = 로컬 개발 머신과 동일 버전 (uv.lock revision 3 생성 버전).
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /usr/local/bin/uv

WORKDIR /app

# 의존성 먼저 설치 (캐시 활용)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# venv 실행 파일을 직접 호출한다. `uv run` 은 매 실행마다 환경 동기화를 시도해
# non-root 사용자에서 캐시 쓰기 권한 문제를 만든다.
ENV PATH="/app/.venv/bin:$PATH"

# 소스 복사
COPY alembic.ini ./
COPY alembic/ alembic/
COPY src/ src/
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

RUN useradd -r -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 마이그레이션은 compose 의 one-shot `migrate` 서비스가 담당한다 (docker-entrypoint.sh 주석 참조).
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["api"]
