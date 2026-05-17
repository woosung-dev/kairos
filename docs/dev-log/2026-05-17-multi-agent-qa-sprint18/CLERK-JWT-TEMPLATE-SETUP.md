# Clerk JWT Template "qa-1h" 셋업 가이드 (사용자 수동, ~5분)

> Sentinel-P0 sub-agent 가 JWT 60초 TTL 로 차단됨. 60분+ TTL template 으로 해결.

## 1. Clerk dashboard 접속

https://dashboard.clerk.com → 본 프로젝트 ("creative-boxer-79") 선택

## 2. JWT Templates 메뉴

좌측 사이드바 → **Configure** → **JWT Templates** (없으면 **Sessions** → **Custom session token**)

## 3. New template

- **Template name**: `qa-1h`
- **Token lifetime**: `3600` (seconds = 1 hour)
  - 또는 더 길게 (예: `28800` = 8 hours) — multi-day QA 가능
- **Allowed clock skew**: 5 (default)
- **Claims**: 기본 (sub/sid/iss 자동 포함). 추가 claim 불필요.
- **Save**

## 4. spec 재실행

```bash
cd /Users/woosung/project/agy-project/kairos/frontend
E2E_BASE_URL=http://localhost:3000 \
  E2E_API_URL=http://localhost:8000 \
  QA_JWT_TEMPLATE=qa-1h \
  pnpm exec playwright test e2e/tests/qa-extract-credentials.spec.ts \
  --no-deps --workers=1 --reporter=list --project=chromium
```

`QA_JWT_TEMPLATE=qa-1h` 환경변수 명시. spec 이 long-TTL token 발급.

## 5. seed-credentials.env 검증

추출 후 `JWT_EXPIRES_AT` 가 현재 시각 + 1시간 이상인지 확인:
```bash
date -u  # 현재 UTC 시각
cat docs/dev-log/2026-05-17-multi-agent-qa-sprint18/seed-credentials.env | grep JWT_EXPIRES_AT
```

## 6. seed 스크립트 재실행 불필요

DB 시드 (User + Workspace + Project + Note + Chunk) 는 이미 완료. JWT 만 새로 추출.

## 7. Sentinel-P0 sub-agent 재디스패치

JWT 신선한 상태에서 다음 prompt 로 재기동:
```
plan = ~/.claude/plans/wise-hugging-newell.md
T-D1-1 Sentinel-P0 dispatch (75분 cap)
```

## 트러블슈팅

### Q. "JWT Templates" 메뉴가 안 보임
- Clerk plan 에 따라 메뉴 위치 다름. 검색: dashboard 우측 상단 검색 → "JWT" 입력
- 또는 **Sessions** → **Customize session token** → **JWT templates** sub-section

### Q. backend 가 새 template JWT 검증 실패 (401)
- 같은 issuer + JWKS 사용하므로 일반적으로 호환
- 검증 실패 시 backend log 확인:
  ```bash
  cd backend && uv run uvicorn src.main:app --reload --log-level debug
  ```
- 일반적 원인: audience claim 추가됨. backend `verify_clerk_token` 이 audience 검증 안 하도록 확인

### Q. 60초 TTL 그대로 — template 적용 안 됨
- spec 실행 시 console 에 `[clerk] template 'qa-1h' 미존재` 경고 확인
- dashboard 에 template 정확히 `qa-1h` 이름으로 저장됐는지 확인
- spec 의 `JWT_TEMPLATE` 환경변수 정확히 매치되는지 확인
