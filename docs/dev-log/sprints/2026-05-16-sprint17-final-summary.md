# Sprint 17 Final Summary (2026-05-15 ~ 2026-05-16)

> Sprint 17 Exhaustive QA + 후속 fix 누적 완료 보고.

## 목표 (사용자 명시 성공 조건)

| ID | 조건 | 결과 |
|---|---|---|
| C1 | 모든 진입점/버튼 접근 | **PASS** (3 P1 fix 후) |
| C2 | 음성 녹음 (CaptureSheet + /new Record) | **PASS** (UI + state machine spec) |
| C3a | /notes CRUD | **PASS** (mock → BE 연결) |
| C3b | CaptureSheet text memory | **PASS** (capture + recall) |
| C3c | /new Text meeting capture | **PASS** (분류 확인) |
| C4 | 개인 워크스페이스 | **PASS** (schema + 자동 생성) |
| C5 | 공유 워크스페이스 + invite accept | **PASS** (owner→viewer 합류) |
| C6 | RBAC + visibility | **PASS** (member BE 403 + ADR-014 visibility filter) |

**8/8 PASS** — 모든 성공 조건 달성.

## 누적 PR 목록 (#40 ~ #54, 15개)

### Phase A: Sprint 17 Exhaustive QA 본 세션 (2026-05-15)

| PR | 내용 | 영향 |
|---|---|---|
| #40 | Sprint 17 main — ISSUE-005/008/009 (3 P1 fix) + docs | /notes BE 연결, /invite 500→200, /projects[id] crash 해소 |
| #41 | BL-034 asyncpg pool — pool_pre_ping + pool_recycle | Neon idle timeout 대응, intermittent 500 차단 |
| #42 | BL-038 invite optimistic + BL-039 member UX | invite list 즉시 갱신, 권한 안내 명시 |
| #43 | BL-035 workspace switcher #N 접미사 | 중복 이름 워크스페이스 구분 |
| #44 | BL-037 Satoshi 폰트 (closed) | user 거절 |
| #45 | BL-036 DB hot path 복합 인덱스 | workspace_members + projects 응답 시간 단축 |
| #46 | ISSUE-040 RAG visibility filter (security) | 글로벌 RAG 쿼리에서 private project chunks 누출 차단 (ADR-014 R-10) |

### Phase B: qa-fix 통합 브랜치 후속 작업 (2026-05-16)

`/loop` 동적 모드로 sub-branch → qa-fix 자동 머지 패턴.

| PR | 내용 | base |
|---|---|---|
| #47 | C.1 record-state-machine fake mic e2e | qa-fix |
| #48 | qa-fix loop 워크플로우 dev-log | qa-fix |
| #49 | ISSUE-008 /invite regression e2e | qa-fix |
| #50 | ISSUE-005 + ISSUE-009 regression e2e | qa-fix |
| #51 | _apply_visibility_filter 통합 4 시나리오 pytest | qa-fix |
| #52 | asyncpg pool config regression pytest | qa-fix |
| #53 | BL-035 buildDisambiguationMap utils 추출 + vitest 8건 | qa-fix |
| #54 | **BL-041 find_similar_cache visibility leak 차단 (security)** | qa-fix |

## 회귀 0 + 헬스 동등

- frontend typecheck: clean
- frontend lint: 190 err / 2837 warn (baseline 동등)
- backend pytest: 108+ pass (baseline 동등) + 신규 vitest 8 + pytest 4
- 신규 e2e spec: record-state-machine / invite-page-regression / qa-regression (총 5건)

## 보안 가드 (ADR-014 정합)

| 경로 | 누출 차단 |
|---|---|
| `pipeline_service.ask` (project_id 명시) | 기존 (Sprint 6) |
| `vector_search` / `text_search` (글로벌 쿼리) | **ISSUE-040 (#46)** |
| `find_similar_cache` (cache hit) | **BL-041 (#54)** |

3 layer 모두 visibility filter — admin/owner 우회 + member/viewer 의 public/draft(creator)/private(ProjectMember) 분기 일관.

## 알려진 잔여 (별도 BL)

- **DESIGN.md 정합 — Satoshi 폰트** (#44 close 후 미해결, user 결정 대기)
- **semantic_caches.max_visibility 컬럼** (BL-041 후속, 위반 cache 자동 재생성 위해)
- **BL-036 perf 효과 측정** (production 배포 후 24h sidebar/settings 응답 시간 측정)

## 워크플로우 메모

`/loop` 동적 모드 + qa-fix 통합 브랜치 + sub-branch 자동 머지 패턴이 효과적:
- main 보호 (작은 PR 누적이 main 흔들지 않음)
- 자동 머지로 빠른 iteration
- 통합 PR 1건으로 main 진입 (현 PR)

다음 Sprint 부터 동일 패턴 권장 — 특히 회귀 가드 (regression e2e/pytest) 추가 시 효과적.
