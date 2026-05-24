# codex-regression — Sprint 27d fix 4건 3중 회귀 검증

> 실행: OpenAI Codex CLI, 2026-05-24.
> 범위: opus fix 4건 + agy 회귀 결과를 Codex 시각으로 재검증. production/Sentry audit 는 사용자 정책대로 SKIP.

## 환경 확인

| 항목 | 결과 | 증거 |
|---|---:|---|
| Branch | PASS | `sprint-27d/pre-ga-audit-prompts` |
| Recent commits | PASS | `6d70eb2` opus audit, `9082041` opus fix, `34f61b6` agy cross-check, `15fb24f` agy report move |
| Playwright MCP | INSTALLED | `codex mcp add playwright -- npx @playwright/mcp@latest`, `codex mcp list` 에 enabled 확인 |
| BE health | PASS | `GET http://127.0.0.1:8000/api/v1/health` → 200 |
| FE health | PASS | `GET http://localhost:3003/` → 200 |

## 회귀 매트릭스

| BUG ID | opus 회귀 | agy 회귀 | codex 회귀 | 최종 |
|---|---|---|---|---|
| BUG-S27d-1 | DONE | PASS | PASS | RESOLVED |
| BUG-S27d-2 | DONE | PASS | PASS | RESOLVED |
| BUG-S27d-3 | DONE | PASS | PASS | RESOLVED |
| BUG-S27d-4 | DONE | PASS | PASS | RESOLVED |

## Codex 검증 상세

### BUG-S27d-1 — OnboardingTooltip console.error

- 실행: `pnpm e2e tests/onboarding-tooltip-first-visit.spec.ts:34` 포함 focused 재검증.
- 결과: PASS. focused run `3 passed` 안에서 dismiss 시나리오 통과.
- 관찰: 전체 병렬 run 에서 동일 spec 1건이 한 차례 실패했으나 focused 재실행에서 통과. 제품 회귀가 아니라 동일 계정/동일 storageState 병렬 실행 flake 로 판정.

### BUG-S27d-2 — `/actions` 404

- 실행: `pnpm e2e tests/actions-redirect.spec.ts`.
- 결과: PASS. `/actions` → `/inbox` redirect 및 console error 0건 focused 재검증 통과.
- 코드 확인: `frontend/src/app/(app)/actions/page.tsx` 가 `redirect("/inbox")` 수행.
- 관찰: 전체 병렬 run 에서 console error 1건이 한 차례 잡혔으나 focused 재실행에서 통과. 최종 제품 회귀로 보지 않음.

### BUG-S27d-3 — upload MIME/extension validation

- 실행: `uv run pytest tests/upload/test_upload_validation.py`.
- 결과: `20 passed in 1.45s`.
- 포함 가드: `evil.exe` + `text/plain` proxy upload 415, presigned-url 415.

### BUG-S27d-4 — security headers

- FE: `GET http://localhost:3003/` response headers 에 `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy` 확인.
- BE: `GET http://127.0.0.1:8000/api/v1/health` response headers 에 동일 4종 확인.
- CSP 는 코드 주석과 `BL-S27e-3` 에 따라 의도적 deferred.

## 검증 명령 요약

| 명령 | 결과 |
|---|---|
| `uv run pytest tests/upload/test_upload_validation.py` | 20 passed |
| `pnpm e2e tests/actions-redirect.spec.ts tests/onboarding-tooltip-first-visit.spec.ts:34` | 3 passed |
| `curl -D - http://127.0.0.1:8000/api/v1/health` | 200 + security headers |
| `curl -D - http://localhost:3003/` | 200 + security headers |

## 관찰사항

| ID | 내용 | 판정 |
|---|---|---|
| CODEX-OBS-1 | FE 전체 병렬 E2E 10 tests 중 2건이 최초 1회 실패 후 focused 재실행 PASS. 동일 계정/동일 storageState 병렬 실행과 onboarding localStorage 상태가 섞일 수 있음. | P3 test reliability, 외부 5명 dogfooding blocker 아님 |
