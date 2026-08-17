# contracts/ — API 계약 (ADR-027 D2)

`openapi/v1/openapi.json` 은 **생성물이다 — 직접 수정 금지.**

- 재생성: 루트에서 `mise run contracts` (= BE export + FE 타입 생성)
- drift 게이트: CI `contract-check` job 이 재생성 후 `git diff --exit-code` 로 차단
- 소스: `apps/api/scripts/export_openapi.py` → FastAPI `app.openapi()`
- 소비: `apps/web/src/types/api.gen.ts` (openapi-typescript)
