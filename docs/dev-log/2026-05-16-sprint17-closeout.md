# Sprint 17 Closeout (2026-05-15 ~ 2026-05-16)

> Sprint 17 Exhaustive QA + /loop qa-fix 통합 브랜치 워크플로우 종결 보고서.

## 결과 — 8/8 PASS

| ID | 조건 | 최종 |
|---|---|---|
| C1 | 모든 진입점/버튼 접근 가능 | **PASS** |
| C2 | 음성 녹음 (UI + state machine) | **PASS** |
| C3a | /notes CRUD (BE 연결) | **PASS** |
| C3b | CaptureSheet text memory | **PASS** |
| C3c | /new Text meeting capture (note 와 분리 확인) | **PASS** |
| C4 | 개인 워크스페이스 (schema + 자동 생성) | **PASS** |
| C5 | 공유 워크스페이스 + invite accept (dual user) | **PASS** |
| C6 | RBAC + visibility (member BE 403 + ADR-014) | **PASS** |

## PR 누적 — 19 PR / 2일

### Phase A — Sprint 17 본 세션 (2026-05-15)

| PR | 내용 |
|---|---|
| #39 | theme: ThemeProvider root layout (user 평행) |
| #40 | Sprint 17 main — ISSUE-005/008/009 (3 P1) + docs |
| #41 | BL-034 asyncpg pool_pre_ping + pool_recycle |
| #42 | BL-038 invite optimistic + BL-039 member UX |
| #43 | BL-035 workspace switcher #N |
| #44 | BL-037 Satoshi Fontshare (user 거절 → BL-045 로 carry-over) |
| #45 | BL-036 hot path 복합 인덱스 |
| #46 | **ISSUE-040 RAG visibility filter** (security) |
| #56 | Sprint 17 통합 PR (qa-fix → main rollup #1) |

### Phase B — qa-fix 후속 loop (2026-05-16)

| PR | 내용 |
|---|---|
| #47 | C.1 record state machine fake mic e2e |
| #48 | loop 워크플로우 dev-log |
| #49 | ISSUE-008 invite regression e2e |
| #50 | ISSUE-005 + ISSUE-009 regression e2e |
| #51 | _apply_visibility_filter 통합 4 시나리오 pytest |
| #52 | asyncpg pool config regression pytest |
| #53 | buildDisambiguationMap utils 추출 + vitest 8건 |
| #54 | **BL-041 find_similar_cache visibility leak** (security) |
| #55 | Sprint 17 mid-summary doc |
| #57 | PR #56 CI 실패 3건 fix |
| #58 | /new note placeholder → /notes redirect CTA |
| #59 | **BL-042 semantic_caches.max_visibility 컬럼** (fast path) |
| #60 | BL-041+042 cache visibility 통합 시나리오 4 pytest |
| #61 | qa-fix → main rollup #2 |
| #62 | vector_search visibility 통합 4 pytest |
| #63 | deploy.yml --cpu-boost --no-cpu-throttling |
| #64 | e2e 잡 BE warm-up guard |
| #65 | **e2e 잡 local BE (Postgres service container) 전환** |
| #66 | alembic step 의 BE secret env 보강 |
| #67 | qa-regression 자체 시드 + meeting-upload heavy skip |
| #61 final | qa-fix → main rollup #3 (모든 후속 포함) |

## 핵심 outcome

### 1. **보안 3-layer (ADR-014 정합)**

```
Layer 1: pipeline_service.ask (project_id 지정 시) — 기존 (Sprint 6)
Layer 2: vector_search / text_search (글로벌 쿼리) — PR #46 ISSUE-040 (Sprint 17 신규)
Layer 3: find_similar_cache (cache hit) — PR #54 BL-041 (Sprint 17 신규)
        ↳ fast path: max_visibility 컬럼 — PR #59 BL-042 (Sprint 17 신규)
```

3 layer 모두 동일 visibility 규칙 — admin/owner 우회 + member/viewer 의 public / draft(creator) / private(ProjectMember) 분기.

### 2. **성능 최적화**

- BL-034: asyncpg pool_pre_ping → intermittent 500 차단
- BL-036: workspace_members + projects 복합 인덱스 → seq scan → index scan
- BL-042: cache fast path → public-only cache 검증 query 1회 절감

### 3. **회귀 가드 인프라**

- e2e Playwright spec 5 신규 (record / invite / qa-regression / cache_visibility 등)
- pytest integration 8 신규 (visibility filter / cache visibility / vector search visibility)
- vitest 8 신규 (buildDisambiguationMap)
- 총 **21 신규 regression test**

### 4. **운영 자립 (CI/CD)**

- e2e 잡을 **prod Cloud Run BE 의존 → local BE (Postgres service container)** 로 전환
- alembic upgrade head + uvicorn 부팅 + Playwright full chain CI 안에서 자체 실행
- Cloud Run cold start 503 의존 해소 (--cpu-boost 도 보강)
- meeting-upload heavy spec 은 `E2E_RUN_HEAVY=true` 환경만 (별도 nightly job BL-043)

## /loop 워크플로우 평가

### 좋았던 점

- **main 보호**: 작은 sub-branch 머지가 main 흔들지 않음
- **빠른 iteration**: sub-branch auto-merge 로 빠른 누적
- **통합 PR 1건으로 main 진입**: review 부담 분산

### 어려웠던 점

- **chicken-and-egg**: deploy.yml 변경은 main merge 후에야 적용 → 1차 rollup 머지 후 CI 더 깨짐
- **local 검증 부재**: e2e spec 들 local 안 돌리고 CI 에 의존 → 환경 의존성 검출 늦음
- **prod BE 의존 해소까지 다단계**: warm-up guard → cpu-boost → local BE 3단계 거침

### 다음 Sprint 에 적용할 lessons

1. **e2e 신규 spec 추가 시 local-first 검증 강제** — playwright local 1회 통과 후 commit
2. **CI/infra 변경은 PR 별도 + 빠른 머지** — feature 머지와 묶이면 chicken-and-egg
3. **qa-fix 통합 브랜치 패턴 유지** — main 보호 + auto-merge 빠름 + 통합 PR review 가능

## 잔여 BL (Sprint 18 후보)

| BL | 우선순위 | 설명 |
|---|---|---|
| BL-043 | P2 | meeting-upload nightly e2e job 분리 + R2 cleanup |
| BL-044 | P1 | SourceAddModal 실제 attachment upload 구현 (BE source 도메인 신설) |
| BL-045 | P3 | DESIGN.md Satoshi 폰트 정합 결정 |
| BL-040 production verify | P2 | RAG visibility filter production 측정 (member 토큰으로 private 미노출 confirm) |
| BL-036 production verify | P2 | hot path 인덱스 효과 측정 (sidebar 2-4s → <500ms 목표) |

## Sprint 18 준비 제안

후보 우선순위:
1. **BL-044 SourceAddModal upload** (P1) — 실제 사용자 워크플로우 누락 보완
2. **ADR-019 Phase B verify** (Sprint 15 carry-over) — Gemini 3.1-flash-lite 정착 확인
3. **production observability** — Cloud Run logs 분석 dashboard / Sentry 도입 검토
4. **mobile 반응형 검증** — 본 세션 데스크탑 only QA 였음

## 산출물

- `~/.claude/plans/noble-baking-teapot.md` v2 — Codex 리뷰 반영 plan
- `.gstack/qa-reports/qa-report-kairos-sprint17-2026-05-15.md` — Phase B QA 보고서
- `docs/dev-log/2026-05-15-sprint17-qa-verification.md` — Phase A 검증 doc
- `docs/dev-log/2026-05-16-sprint17-qa-fix-loop.md` — Phase B 중간 진행
- `docs/dev-log/2026-05-16-sprint17-final-summary.md` — qa-fix 통합 직전 summary
- `docs/dev-log/2026-05-16-sprint17-closeout.md` — 본 문서 (최종 종결)
- `docs/REFACTORING-BACKLOG.md` — BL-034~045 (resolved 마크 + 신규)

Sprint 18 진입 준비 완료.
