#!/bin/sh
# Kairos Backend 컨테이너 엔트리포인트 (ADR-028)
#
# role 로 분기한다 — 마이그레이션과 앱 기동을 한 프로세스에 묶지 않는 것이 목적.
# 묶으면 restart:unless-stopped 와 결합해 마이그레이션 실패가 무한 재시작 루프가 되고,
# "마이그레이션 실패"와 "앱 크래시"를 로그에서 구분할 수 없다 (2026-06-30 prod crash-loop).
set -e

ROLE="${1:-api}"

case "$ROLE" in
  migrate)
    echo "[entrypoint] alembic upgrade head"
    exec alembic upgrade head
    ;;
  api)
    echo "[entrypoint] uvicorn (workers=1)"
    # --workers 를 늘리지 말 것. ai_resilience 의 circuit breaker 와 auth 의 JWT/User 캐시가
    # in-process 싱글턴이라 multi-worker 는 상태를 워커별로 파편화한다.
    exec uvicorn src.main:app --host 0.0.0.0 --port 8000
    ;;
  *)
    exec "$@"
    ;;
esac
