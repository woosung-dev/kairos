# 다음 세션 프롬프트 — Sprint 28b 후속: P3 polish + 설계종속 backlog

> 아래 전체를 다음 세션 첫 메시지로 붙여넣어 시작하면 된다. 이번(2차 정검) 세션과 같은 깊이·꼼꼼함으로 진행되도록 작성했다.

---

Kairos 2차 정검(`docs/dev-log/qa/2026-05-29-uiux-edge/`)의 **잔여 P3 polish + 설계종속 backlog** 를 처리한다. 2차 정검 자체와 시급 fix(P0 secret redaction / P1 workspace_members UNIQUE / P2 4건 + inbox promote picker)는 **PR #115·#116 으로 머지 완료**(main HEAD `5ec72d1`). 이번 세션은 그때 P3/backlog 로 분류해 미룬 것들을, **재발견이 아니라 — 이미 evidence 로 근거가 잡힌 것들을 구현/결정**하는 작업이다.

## 먼저 읽을 것 (Context Sync)
1. `docs/dev-log/qa/2026-05-29-uiux-edge/bugs.md` — 백로그 + `## FIX 적용 현황`(무엇이 이미 머지됐는지) + `## 미커버`(범위 한계).
2. `docs/dev-log/qa/2026-05-29-uiux-edge/report.md` — 판정·발견 요약.
3. `CONTEXT-MAP.md`(헌법 — 도메인/visibility/invariant) · `.ai/templates/workflow.md`(Plan→Code→Test + 위험분류 + 검증 증거 표준).
4. 메모리 `project_sprint28b_uiux_edge_done`.
⚠️ 라인 번호는 #115/#116 머지 후 이동했을 수 있으니 각 파일 **재grep 후 수정**할 것.

## 환경 · 계정 (2차 정검과 동일)
- 포트 kill → `uv run --directory backend uvicorn src.main:app --port 8000`(→운영 Neon, CORS=3000) + `pnpm -C frontend dev`. BE health = `GET /api/v1/health`.
- 통합테스트 = `open -a Docker` 후 `uv run --directory backend pytest`(TestContainers, 운영 무오염).
- 테스트 계정(.env.local QA_LOCAL_*): A=d@e.com/`de`(owner) · B=a@e.com/`ae` · C=f@e.com/`fe`(신규). 라이브 테마 토글 = next-themes `localStorage['theme']='light'|'dark'`+reload.
- ⚠️ **public 전환 금지**(과거 secret 히스토리 잔존). ⚠️ **GitHub Actions 결제 한도** → CI 자체 실패하므로 **`.github/workflows/test.yml` 게이트를 로컬 재현**해 검증: ① `uv run --directory backend pytest --ignore=tests/services/test_transcription.py --ignore=tests/test_r2_cors_regression.py` ② `pnpm -C frontend test`(vitest) ③ `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY="pk_test_Y2xlcmsuZXhhbXBsZS5jb20k" NEXT_PUBLIC_API_URL="http://localhost:8000" pnpm -C frontend build` ④ security-headers: 빌드 후 `pnpm start -p 3000` + `E2E_PORT=3000 E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test --project=public-only`. 통과 시 `gh pr merge <n> --merge --admin`.
- ⚠️ **선행 운영자 작업 미완**: Clerk 대시보드 dev `CLERK_SECRET_KEY` **rotation**(노출 키 무효화) — 코드 redaction(#115)은 됐으나 라이브 키는 아직. 세션 시작 시 사용자에게 1회 확인.

## 작업 A — P3 quick-win polish (1 PR: `sprint-28c/a11y-polish`)
명확·저위험. 변경마다 verify(스샷 + console.error 0). FE 변경은 `frontend/AGENTS.md`(“이건 네가 아는 Next.js 아님”) 주의 — Next.js API 안 건드리는 className/aria/토큰 수준이면 안전.
1. **A11Y-AVATAR-LABEL** — `components/layout/header.tsx` 의 user avatar DropdownMenuTrigger 에 `aria-label`(예 "계정 메뉴") 추가. (검색바·dialog close·archive 토글·bottom-nav 는 이미 visible text/sr-only 보유 → 비대상, refuted.)
2. **A11Y-ICON-RAIL-768** — `components/layout/sidebar.tsx` collapse 시 nav 가 HTML `title=` 만 → `aria-label={item.label}` 추가 + `focus-visible` ring. 키보드 tab 으로 라이브 확인.
3. **UX-CMDK-GLYPH** — ⌘(U+2318) 가 Geist Mono 미포함 → 검색 단축키 배지 깨짐. kbd 배지에 시스템 폰트 fallback(예 `'SF Pro Text', system-ui`) 적용 또는 "⌘K"→플랫폼별 표기. `header.tsx`/`components/layout/cmd-k.tsx` 재grep.
4. **OBS-VIEWER-VISIBILITY-BTN** — `features/projects/components/project-detail.tsx`(~141-150) VisibilityBadge 가 viewer 에게도 클릭 가능 버튼으로 렌더(onClick 가드는 있으나 시각상 동작버튼). admin/owner 아니면 **비대화형 배지**로 렌더(workspace role 은 store/useMembers 에서). 라이브 = B를 viewer 로 두고 private project 상세 확인.
5. **BUG-ARCHIVED-PROJECT-LEAK (defense)** — `backend/src/projects/repository.py:~46,~68` `if status:` → status 미지정 시 archived/completed 누출. **기본 list 를 active-only** 로(또는 명시 status 요구). FE `/projects`(이미 active 전송)·사이드바 영향 확인 + 통합테스트(기본 list 가 archived 제외) 추가. ※ Channel A 테스트 `tests/qa_edge/test_data_state_s28b.py` 의 “archived 누출” 단언을 fix 에 맞게 반전.
6. **DESIGN-TOKEN-DRIFT** — 토큰 우회 하드코드를 `globals.css` var() 로: `features/rag/components/citation-badge.tsx`(#A78BFA→var(--chart-3), #FBBF24→var(--warning)) · `features/actions/components/action-kanban.tsx` priority(#F87171→var(--error)/#FBBF24→var(--warning)/#60A5FA→var(--info)) · `features/home/components/today-feed.tsx`(#FBBF24) · `globals.css ::selection{color:#fff}`. (분량 크면 5와 분리해 별도 commit.) 다크/라이트 양쪽 스샷 회귀 확인.

## 작업 B — 설계종속 backlog (각각 결정 필요 — 권고 포함, 사용자 confirm 후 진행)
1. **BUG-MEMORY-WS-FILTER** (정적, I-9 2-layer 갭) — `backend/src/memory/repository.py:55-95,139` 5 mutation 이 PK-only WHERE(workspace_id 누락), MemoryItem 에 composite FK 없음. **권고**: (소) 5 mutation 에 workspace_id WHERE 추가 + cross-ws mutation 차단 통합테스트(현재 정적 단정 → 실증). composite FK 마이그레이션(타 도메인 정합)은 옵션 후속. *결정*: 소 fix 만 vs composite FK 까지.
2. **BUG-SEARCH-CURRENT-PROJECT-NOOP** (라이브) — 글로벌 `/search` "현재 프로젝트" 탭이 scopeTab 만 바꾸고 `searchFilter.projectId` 미설정(컨텍스트 없음) → 전체와 동일. **권고**: 글로벌 search 에선 탭 **hide**(또는 "선택한 소스"처럼 "준비 중" 정직 안내). 프로젝트 picker 구현은 과함. *결정*: hide vs 안내 vs picker. `features/rag/components/search-scope.tsx`.
3. **BL-DATA-HYGIENE-SEED** (확정, ADR-022 종속) — lazy seed 가 Clerk profile 미동기 → 전 멤버 displayName "사용자"/email="". **권고**: `backend/src/auth/dependencies.py` lazy seed 시 JWT claims(email/name)로 User.display_name/email 채우기(첫 로그인). 작고 사용자체감 큼. *결정*: 지금 vs ADR-024 GA 때.

## 방식 (2차 정검과 동일 규율)
- **Plan → Code → Test**. 위험분류(workflow.md): A 대부분 Lite/Standard(FE/소 BE), B-1·B-3 은 BE/DB 인접 → Standard+(codex/agy cross-check 권장).
- 각 fix = atomic commit(헌법 §6 컨벤션, Co-Authored-By 트레일러). A 는 1 PR, B 는 결정된 것만 별도 PR.
- **검증 증거 표준**: FE = 스샷 1장 + console.error 0 / BE = pytest 요약 + (스키마변경 시) alembic dry-run. 라이브는 운영 Neon 최소쓰기(throwaway WS), 결정적은 test DB.
- **adversarial 검증 옵션**: 헤드라인 fix 는 빈컨텍스트 opus 또는 codex 로 1회 반증(이번 세션 패턴). 단 P3 규모면 과할 수 있으니 판단.
- main 머지·푸쉬는 사용자 승인(이번 세션은 사용자가 자동커밋+머지 위임했으나 standing 아님 — 재확인).

## 운영 orphan (조치 선택) 
throwaway WS **QA-EDGE-S28b** `47f0f895-7e51-4f44-af03-ab7b4d3f647c`(+멤버 B·private project·meeting 3·note) + C 개인WS 의 검증용 캡처/프로젝트들. delete-workspace endpoint 부재로 잔존(report §Cleanup ID 전수). 저가치 → delete-workspace 추가하거나 DB 정리하는 운영 sprint 때 SQL 일괄 권장.

## 성공기준
- A: quick-win 6건 fix + 로컬 CI 게이트 4종 green + 라이브 스샷, 1 PR 머지.
- B: 결정된 항목 fix + 통합테스트(memory IDOR 실증 등) + PR.
- bugs.md `FIX 적용 현황` 갱신. main green 유지. Clerk rotation 사용자 확인.
