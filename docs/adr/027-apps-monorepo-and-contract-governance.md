# ADR-027: App-first 레포 재구성 + OpenAPI 계약 거버넌스

**Status**: Accepted — **D1 은 [ADR-030](030-apps-api-rename.md) 이 부분 대체** (2026-08-16, `apps/backend` → `apps/api`. D2~D5 는 그대로 유효)
**Date**: 2026-08-13
**관련**: CONTEXT-MAP.md §9 (Atomic Update) · `docs/architecture/directory-map.md` · ADR-008 (BE 배포 자동화) · ADR-024 (GA readiness) · `apps/web/src/lib/api-client.ts` seam (2026-07-13 리팩토링)

---

## 1. 배경

외부 LLM 과의 모노레포 아키텍처 검토(App-first Polyglot Monorepo · OpenAPI 계약 중심 통합 ·
pnpm/uv/just 네이티브 툴체인 · 단계적 Nx)를 Kairos 실태와 대조한 결과:

**이미 일치 (액션 불필요)**: uv + `uv.lock`(BE) · pnpm(FE) · BE Modular Monolith(17 모듈 = 14 도메인
+ common/core/services) · FE FSD feature-first(16 features) · 독립 배포(Vercel git 연동 + Cloud Run
`deploy.yml` paths 필터).

**실측된 갭 4건**:

1. **API 계약 거버넌스 부재** — 레포에 openapi.json export/커밋/drift 게이트 없음. schemathesis 는
   AGENTS.md 검증 표준에 명시돼 있으나 미설치(정책만 존재, TODO AD-35). `docs/api/endpoints.md`
   1,205줄 수기 명세는 2026-04-01 이후 드리프트 확정적.
2. **FE wire 타입 100% 수기** — 13개 feature `types.ts` 56개 인터페이스, 생성물 0. 실제 사고 이력:
   S28b `pageSize` camel/snake mismatch(`features/projects/api.ts` 주석 잔존), admin recall-metrics
   페이지의 snake_case `MemoryMetrics` 수기 정의. BE 카멜화가 per-model `Field(alias=)` ~20곳에
   산재해 wire 케이싱이 엔드포인트마다 다름 — 수기 타입으로는 컴파일 타임 검출 불가.
3. **루트 공통 명령 부재** — README 의 `uv run pytest -v` ≠ CI 의 `--ignore` 2개 붙은 호출.
   로컬 게이트와 CI 게이트가 다른 명령.
4. **CI 변경 감지 부재** — `test.yml` 이 매 PR 에서 BE+FE 전체 실행(5m49s~9m56s), BE-only PR 에도
   chromium 설치 + Next 부팅. concurrency 그룹 없음.

레포 레이아웃에 대한 결정 기록도 0건이었다(본 ADR 이 최초).

## 2. 결정

### D1. App-first 레이아웃 — `apps/backend` + `apps/web` (즉시)

`backend/` → `apps/backend/`, `frontend/` → `apps/web/`. `apps` 는 "프론트엔드 폴더"가 아니라
**독립 실행·빌드·배포되는 소프트웨어 단위의 집합**이다.

분류 규칙:

| 위치 | 대상 |
|---|---|
| `apps/*` | 독립 배포 애플리케이션 (backend=Cloud Run, web=Vercel) |
| `contracts/*` | 언어를 넘는 API 계약 (D2) |
| `packages/*` | 공유 라이브러리 — **동일 언어 소비자 2개 전까지 만들지 않음** (D5) |

이동은 2-commit 구조(순수 `git mv` → 경로 수정)로 rename 검출(R100)을 보존한다. 배포 측 수반
작업: `deploy.yml` paths 필터 `apps/backend/**` 갱신(누락 시 BE 배포 무음 중단), Vercel Root
Directory 대시보드 변경(`docs/guides/deployment.md` §3.1 절차).

### D2. OpenAPI 계약 거버넌스 — backend-generated, contract-governed (후속 PR)

```
FastAPI (Pydantic V2, Field alias)
   → apps/backend/scripts/export_openapi.py (in-process app.openapi(), 결정적 직렬화)
   → contracts/openapi/v1/openapi.json (커밋)
   → openapi-typescript (정확 버전 핀)
   → apps/web/src/types/api.gen.ts (커밋, 수정 금지)
```

- CI `contract-check` job 이 재생성 + `git diff --exit-code` 로 drift 차단.
- **타입만 생성, fetch 클라이언트는 생성하지 않음** — `api-client.ts` seam(2026-07-13 SSOT
  리팩토링)과 feature `api.ts` 53개 함수는 유지. 풀 클라이언트 생성은 seam 파괴 + 13개 feature
  전면 수정이라 기각.
- **점진 전환**: 기존 수기 타입 56개는 유지하고, 신규/변경 코드부터 `api.gen.ts` 사용.
  wire interface 수기 신규 작성은 금지 (AGENTS.md 규칙).
- 프로덕션의 `openapi_url=None` 게이팅(T-SEC-5)은 in-process `app.openapi()` 호출과 무관 —
  노출 차단은 유지된다.

### D3. justfile — 루트 단일 명령 진입점 (후속 PR)

`just be-test` 등 recipe 는 **CI invocation 과 문자 그대로 동일**하게 유지한다(한쪽 변경 시 동시
변경). README 명령 나열은 justfile 참조로 대체.

### D4. CI 변경 감지 + concurrency + aggregate gate (후속 PR)

- `changes` job(dorny/paths-filter)이 PR 에서 변경 경로 계산, push(main/prod)는 전체 강제 실행
  (dorny push-base 엣지케이스 회피).
- job-level `if` 로 backend-test / frontend-build / contract-check 선택 실행.
- `ci-required` aggregate job: `if: always()`, failure/cancelled 시 fail, skipped 허용.
  **workflow-level `paths:` 필터는 required check 에 사용 금지** (skip 시 check pending 잔존
  footgun). 현재 branch protection 부재(Free plan)이므로 future-proofing.
- concurrency: PR 은 `cancel-in-progress`, push 는 취소 금지(배포 인접 증거 보존).

### D5. 보류/기각 항목과 재검토 트리거

| 항목 | 판정 | 트리거 |
|---|---|---|
| oasdiff breaking-change 게이트 | 보류 | 외부/모바일 API 소비자 첫 등장. 현재는 FE·BE 가 같은 PR 원자 변경 → 생성 타입 diff + FE typecheck 이 그 역할 수행 |
| `packages/` 공유 패키지 | 보류 | 동일 언어 소비자 2개 + 변경 주기 동일 확인 |
| Nx / Turborepo | 보류 | 지속적 CI 병목(>15분) 또는 영향도 계산 수동 유지 불가 시점. D4 변경 감지를 먼저 소진 |
| 3번째 앱 (mobile/admin 분리) | 해당 없음 | PRD §9 모바일 네이티브 명시 제외(PWA 대체). admin 은 FE 내 founder 페이지 + RBAC 로 충분 |
| CODEOWNERS | 기각 | 1인 개발 (PERSONA-001) |
| pub/Dart workspace | 기각 | 모바일 앱 없음 |
| 풀 생성 API 클라이언트 | 기각 | D2 참조 — seam 파괴 비용 > 이득 |

## 3. 결과

- 레포 규칙이 단순해진다: 실행·배포 = `apps/`, 계약 = `contracts/`, 그 외 공유는 증명 후.
- 계약 드리프트(S28b 류)가 런타임 발견 → 컴파일 타임/CI 차단으로 이동.
- 로컬 게이트 = CI 게이트 (justfile 로 invocation 통일).
- 비용: 경로 참조 ~40파일 일괄 수정(frozen 문서 제외), Vercel Root Directory 1회 수동 변경,
  `.venv` 재생성. 과거 문서(dev-log, ADR 001~026, CHANGELOG)의 구 경로는 역사 기록으로 보존 —
  2026-08-13 이전 문서의 `backend/`·`frontend/` 는 각각 `apps/backend/`·`apps/web/` 으로 읽는다.
