# syntax=docker/dockerfile:1.7

# ── builder: venv 만 만들고 버린다 ────────────────────────────────────────
# 단일 스테이지였을 때 uv 바이너리(45.5MB)와 /root/.cache/uv 가 최종 이미지에
# 그대로 남았다 (2026-08-30 `docker history` 실측).
FROM python:3.12-slim AS builder

# uv 설치 — 태그 고정. :latest 면 같은 커밋이 서로 다른 uv 로 빌드될 수 있다.
# 0.10.4 = 로컬 개발 머신과 동일 버전 (uv.lock revision 3 생성 버전).
# ★이 라인은 `mise run toolchain-check` 가 grep 으로 검사한다 (mise.toml [tools] uv 와 대조).
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /usr/local/bin/uv

# ★WORKDIR 은 런타임 스테이지와 같아야 한다. venv 는 절대경로에 묶여 있어서
#   /app/.venv 로 만든 것을 다른 경로에 놓으면 shebang 이 깨진다.
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-cache

# ── runtime: ffmpeg + venv + 소스 ─────────────────────────────────────────
FROM python:3.12-slim

# 시스템 의존성 (ffmpeg: 카카오톡 m4a 변환용)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# WORKDIR 이 만드는 /app 은 root 소유가 된다. 단일 스테이지 시절 `chown -R /app` 이
# 부수적으로 맞춰 주던 것이라, 행동 동등성을 위해 여기서 명시적으로 만든다 (빈 디렉터리 = 4KB).
RUN useradd -r -u 1001 appuser && install -d -o appuser -g appuser /app

WORKDIR /app

# ★`chown -R /app` 을 쓰지 않는다. 메타데이터만 바꿔도 overlayfs copy-up 이 일어나
#   venv(163MB) 가 통째로 새 레이어에 재복제됐다 — 206MB 짜리 순수 낭비 레이어였다.
#   COPY --chown 은 복사하면서 소유권을 정하므로 추가 레이어가 생기지 않는다.
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser alembic/ alembic/
COPY --chown=appuser:appuser src/ src/
COPY --chown=appuser:appuser --chmod=755 docker-entrypoint.sh ./

# venv 실행 파일을 직접 호출한다. `uv run` 은 매 실행마다 환경 동기화를 시도해
# non-root 사용자에서 캐시 쓰기 권한 문제를 만든다.
ENV PATH="/app/.venv/bin:$PATH"

USER appuser

EXPOSE 8000

# 마이그레이션은 compose 의 one-shot `migrate` 서비스가 담당한다 (docker-entrypoint.sh 주석 참조).
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["api"]
