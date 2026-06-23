# Ponytail Cleanup Checklist

- [x] 작업 브랜치 생성.
- [x] 미사용 FE wrapper/helper 파일 삭제.
- [x] frontend dependency 정리.
- [x] backend dependency 정리.
- [x] 오래된 audit/sprint 산출물과 디버그 PNG 삭제.
- [x] canonical doc 업데이트.
- [x] lockfile 갱신.
- [x] frontend typecheck 실행.
- [x] backend smoke pytest 실행.
- [x] 커밋, 푸시, draft PR 생성.

## Verification

- [x] `pnpm --dir frontend typecheck`.
- [x] `pnpm --dir frontend test`.
- [x] `uv run pytest tests/architecture tests/auth/test_jwt_verification.py tests/auth/test_jwt_cache.py tests/services/test_ai_resilience.py`.
- [x] `git diff --check`.
