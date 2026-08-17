# API 문서 — 라우팅

> 이 폴더는 **규칙을 소유하지 않는다.** API 규칙은 이미 소유자가 있고, 그 옆에 있어야 지켜진다.
> 여기는 "무엇을 어디서 보나" 만 답한다.

| 알고 싶은 것 | 정본 |
|---|---|
| **실제 엔드포인트·스키마** | [`contracts/openapi/v1/openapi.json`](../../contracts/openapi/v1/openapi.json) — 생성물. 수정 금지 |
| 계약 재생성 / drift 게이트 | `mise run contracts` · `mise run contracts-check` → [`contracts/README.md`](../../contracts/README.md) ([ADR-027](../adr/027-apps-monorepo-and-contract-governance.md) D2) |
| URL prefix 규칙 (`/api/v1/workspaces/{workspace_id}/…`) 과 그 예외 | [`CONTEXT-MAP.md`](../../CONTEXT-MAP.md) **I-13** |
| DB snake_case ↔ API camelCase 직렬화 | [`CONTEXT-MAP.md`](../../CONTEXT-MAP.md) **I-16** |
| status code · 페이지네이션 · 리소스 명명 · 권한 dependency | [`apps/api/CONTEXT.md`](../../apps/api/CONTEXT.md) **§6** |
| 에러 처리 (도메인 `exceptions.py` + 전역 핸들러) | [`apps/api/CONTEXT.md`](../../apps/api/CONTEXT.md) **B-12** |
| 인증 (Bearer JWT 검증 · RBAC) | [`apps/api/src/auth/CONTEXT.md`](../../apps/api/src/auth/CONTEXT.md) |
| 도메인별 엔드포인트 책임 | [`apps/api/src/<domain>/CONTEXT.md`](../product/domains/README.md) |
| FE wire 타입 | `apps/web/src/types/api.gen.ts` — 생성물. 수기 작성 금지 (**I-22**) |
| 장기 작업 규약 (202 Accepted + polling) | [`CONTEXT-MAP.md`](../../CONTEXT-MAP.md) **I-5** |

## 로컬에서 스키마 보기

개발 환경에서는 FastAPI 가 문서를 노출한다 (프로덕션은 `openapi_url=None` 으로 차단).

```
http://localhost:8000/api/v1/docs
```

## 옛 `endpoints.md`

수기 REST 명세 `docs/api/endpoints.md`(1,209줄)는 2026-08-13 에 동결됐고
**2026-08-16 에 삭제**했다 — 계약 생성물이 정본이 된 뒤로 갱신되지 않는 두 번째 진실이었다.

```bash
git log --diff-filter=D --oneline -- docs/api/endpoints.md   # 삭제 커밋 찾기
git show <sha>^:docs/api/endpoints.md                        # 내용 복원
```
