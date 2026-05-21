# Sprint 17 — Exhaustive QA Verification (2026-05-15)

> Sprint 17 통합 QA 검증 + atomic fix 루프 결과 기록.

## 컨텍스트

Sprint 14 dogfooding (2026-05-14) 이후 personal-workspace / memory recall / pgvector HNSW / halfvec / ADR-019 Phase B 누적. Sprint 17 진입 전 회귀/헬스 기준선 확보 + 사용자 명시 성공 조건 6건 검증.

**작업 브랜치**: `sprint-22/theme-provider-root` (원 계획 `sprint-17/qa-stabilize` 였으나 user 가 외부에서 theme fix 진행 중인 sprint-22 와 mingled, user 결정으로 동일 브랜치 유지)

**도구 분담**:
- gstack `/qa` Exhaustive — route traverse + 인터랙티브 매트릭스 + atomic fix-commit
- 보조: API 직접 호출 (visibility toggle, RBAC 검증)

**계획 파일**: `~/.claude/plans/noble-baking-teapot.md` (v2 — Codex 리뷰 conditional accept 반영)

## 사용자 성공 조건 결과

| ID | 조건 | 결과 | 근거 |
|---|---|---|---|
| C1 | 모든 진입점/버튼 접근 가능 | PASS (after fix) | 모든 라우트 200 traverse. /invite 500 → 200 (ISSUE-008 fix). /projects/[id] ErrorBoundary → 정상 (ISSUE-009 fix). known-incomplete (SourceAddModal toast-only, /new note/attachment placeholder) BL 등재 |
| C2 | 음성 녹음 (CaptureSheet voice + /new Record) | UI PASS | recording state machine UI 존재 (00:00 timer + 녹음 시작 button). Full mic stream e2e 는 별도 세션 (Playwright MCP fake stream) |
| C3a | /notes CRUD | PASS (after fix) | mock 제거 + BE API 연결 (ISSUE-005 fix). POST → reload → 영구 유지 검증 |
| C3b | CaptureSheet text memory | PASS | "메모를 저장했어요. AI 정리 중…" → recall query 3 결과 (의미 매칭) |
| C3c | /new Text meeting capture | PASS | meeting text capture 임. 노트 와 명시 구분 (Codex F1 정정 확인) |
| C4 | 개인 워크스페이스 | PASS (schema + 자동 생성 확인) | `type='personal'` 필드 존재. 신규 가입 시 자동 personal workspace 생성 (viewer wkddntjd 검증) |
| C5 | 공유 워크스페이스 + invite accept | PASS | owner 생성 → invite 링크 (member role) → viewer accept → team workspace 합류 (members API 검증) |
| C6 | RBAC + visibility | PASS (member 레벨) | member: content 생성 OK, settings/invites 403. visibility=private API toggle 검증. visibility 의 RAG post-filter deep test 는 별도 세션 (content 있는 project 필요) |

**전체**: 8/8 PASS (C2/C6 일부 후속 검증 별도 세션 예정)

## 발견 사항 + Fix 결과

### FIXED (3 atomic commits)

| ID | 심각도 | 제목 | Commit | 변경 파일 |
|---|---|---|---|---|
| ISSUE-005 | P1 | /notes mock 데이터 — save 가 API 미호출, reload 시 노트 사라짐 | `6791783` | `frontend/src/features/notes/components/quick-memo.tsx` |
| ISSUE-008 | P1 | /invite/[code] HTTP 500 — "No QueryClient set" | `33c9f1c` | `frontend/src/app/layout.tsx` + `frontend/src/app/(app)/layout.tsx` |
| ISSUE-009 | P1 | /projects/[id] "Rendered more hooks than during the previous render" | `ae35f53` | `frontend/src/features/projects/components/project-dashboard.tsx` |

### CLOSED (외부 fix)

| ID | 심각도 | 제목 | Commit | 비고 |
|---|---|---|---|---|
| ISSUE-001 | P3 | Console "Encountered a script tag while rendering React component" | `1e903e8` (외부) | user 평행 작업으로 해결 |

### DEFERRED (BL 등재)

| ID | 심각도 | 제목 | BL |
|---|---|---|---|
| ISSUE-002 | P2 | 5 duplicate workspaces 동일 이름 "E2E 테스트 워크스페이스" — switcher 구분 불가 | BL-035 |
| ISSUE-003 | P3 | 비 dashboard 라우트 sidebar project list 3-6s 지연 로딩 | BL-036 |
| ISSUE-004 | P3 | Google Fonts Satoshi 요청 pending (FOIT 위험) | BL-037 |
| ISSUE-006 | P1 | asyncpg.InterfaceError "connection is closed" intermittent (Neon pool stale) | BL-034 |
| ISSUE-007 | P2 | 초대 링크 생성 직후 list 미반영 (cache invalidation 누락) | BL-038 |
| ISSUE-010 | P3 | /settings 초대 탭에서 member 진입 시 빈 헤더만 노출 (명시 권한 에러 미표시) | BL-039 |

## 헬스 스코어 (Phase A.6 vs Phase D)

| 항목 | Before | After | 차이 |
|---|---|---|---|
| frontend typecheck | clean | clean | 동등 |
| frontend lint | 191 err / 2836 warn | 190 err / 2837 warn | -1 err / +1 warn (wash) |
| backend pytest (non-integration) | 108 pass | 108 pass | 동등 |
| backend pytest errors | 43 (Docker testcontainer 환경 의존) | 43 | 동등 |

회귀 0. 코드 품질 동등 이상.

## Atomic Doc Update

본 sprint 17 QA fix 3건은 모두 FE 컴포넌트/레이아웃 변경. `.ai/common/global.md` §2 matrix 기준으로 backend models/router 변경 없음 → 도메인 `CONTEXT.md` 갱신 불요. Sprint 17 검증 doc (본 파일) + `docs/TODO.md` + `docs/REFACTORING-BACKLOG.md` BL-031~036 등재로 atomic update 완료.

PR 본문 docs sync:
```
git diff --stat docs/ backend/**/CONTEXT.md CONTEXT-MAP.md
```

## 후속 액션 (Phase E 종료 후)

1. **사용자 push 승인 대기** — `git push -u origin sprint-22/theme-provider-root`
2. **별도 세션 검토 후보**:
   - C.1 음성 녹음 full e2e (Playwright MCP + fake mic stream)
   - C.3b RAG visibility=private post-filter deep test (project + content seeding)
   - BL-034 asyncpg pool stale connection 회귀 fix (Neon pool_pre_ping)
3. **PR 생성**: 별도 세션 `/ship` (현 브랜치에 theme fix + QA 3 fix 모두 포함)

## 참고

- 계획 파일: `~/.claude/plans/noble-baking-teapot.md` (v2)
- 보고서: `.gstack/qa-reports/qa-report-kairos-sprint17-2026-05-15.md`
- 스크린샷: `.gstack/qa-reports/screenshots/` (15+ 장)
- Codex 리뷰: 8 finding (4 FAIL + 4 CONCERN) + 5 missing risks → 모두 plan v2 에 반영, F2 (auto-commit) 만 user 명시 override + per-fix confirm 안전 가드
