# Kairos 심층 전수 검토 — 종합 보고서 (2026-06-01)

> 범위: 전체 코드(FE Vercel 베스트프랙티스 + BE FastAPI 최신 스펙) + 전체 화면/기능 라이브 + UI/UX 정적 + 로드맵 잔여 항목.
> 방법: Workflow 75-agent fan-out(review→adversarial verify) + Playwright MCP 라이브 + context7 스펙 baseline + ui-ux-pro-max/vercel-react-best-practices 기준.
> 환경: 로컬 풀스택(FE :3000 / BE :8000 / Neon), owner `d@e.com`. main HEAD `8026754`. 검토 전용 read-only(수정은 §6 별도).

---

## 1. 종합 결론

| 영역 | 상태 | 근거 |
|------|------|------|
| **핵심 기능 동작** | 🟢 양호 | 회의 capture→요약/액션/날짜정규화, RAG SSE+출처, inbox 적재, feedback, 모바일 — 라이브 전부 PASS, console errors 0 |
| **BE 코드 (FastAPI 스펙)** | 🟡 견고하나 결함 산재 | lifespan/Pydantic V2/exec 패턴 대체로 준수. 단 **P0 1건**(notes BG 세션) + P1 8건(캐시 stale, 500 노출, circuit breaker) |
| **FE 코드 (Vercel 베스트프랙티스)** | 🟡 개선 여지 큼 | React Query/FSD 구조 양호. 단 dead code 3쌍, re-render(셀렉터 미사용) 다수, hydration flicker, dead provider 중첩 |
| **UI/UX** | 🟡 토큰 정합 이슈 집중 | **라이트 모드 대비 미달(전역)**, 이모지 아이콘 광범위, dark: 변형 무효, RAG 마크다운 미렌더 |
| **로드맵 진척** | 🟢 예상보다 앞섬 | "미구현"으로 알려진 다수 기능이 이미 구현됨. 진짜 잔여 52건(대부분 부채/하드닝) |

**총 발견 345건**: P0 **1** / P1 48 / P2 124 / P3 172 (+ 잘 구현된 점 217건). 트랙별 BE 110 · FE 117 · UIUX 118.

가장 큰 한 줄 요약 — **"동작은 한다. 정합성·일관성·로딩 UX가 약하다."** 신규/핵심 기능 버그는 적고, 부채성(토큰 일관성·re-render·dead code·로딩 가드) 항목이 다수다.

---

## 2. P0 — 즉시 조치 (1건)

### P0-1 · notes create/update 임베딩 BG task가 닫힌 세션 사용 (Sprint 9 버그 재발)
- **위치**: `backend/src/notes/dependencies.py:36-44` + `notes/router.py:91-93,119-120`
- **내용**: `get_note_pipeline_service`가 request-scoped 세션으로 pipeline 생성 → `BackgroundTasks`는 응답 후(세션 close 후) 실행 → `embed_note_async`가 닫힌 세션으로 DB 호출 → **임베딩 조용히 실패 → 노트가 RAG/검색에서 누락**. meetings는 이미 `session_factory`로 해결됨(meetings/dependencies.py:41-50), notes의 promote도 fresh 세션. **유독 create/update만 누락**. 테스트가 pipeline을 통째 mock(test_notes_api.py:56-61)해 미검출. 메모리 `project_sprint9_audio_fix`와 동일 클래스.
- **조치**: meetings 패턴으로 통일(session_factory 주입 + BG 내부 `async with session_factory()`) + 실 DB 회귀 테스트. → **§6에서 수정**.

---

## 3. P1 핵심 (48건 중 대표) — 우선 처리 권장

### BE (8건)
| ID | 위치 | 요지 |
|----|------|------|
| auth-cache | `auth/dependencies.py:69,241` | `invalidate_user_cache` 호출자 0건 → onboarding step 최대 60s stale |
| auth-claim | `auth/dependencies.py:177` | `verify_clerk_token`이 sub 외 claim 폐기 → 신규 user name/email이 항상 fallback("사용자"/"") **[Clerk JWT Template 의존 확인 필요]** |
| projects-500 | `projects/service.py:181-207` | ProjectMember 중복 추가 → IntegrityError 미처리 → **500**(409여야) |
| notes-stale | `notes/router.py:119` | project_id-only update 시 EmbeddingChunk.project_id stale → RAG 범위 필터 오류 |
| inbox-IB5 | `inbox/service.py:115-132` | meeting 재분류 시 `uq_meeting_project` UNIQUE 위반 → **500**(IB-5 idempotent 불변식 위반) |
| **main-500** | `main.py:161-168` | validation handler가 `jsonable_encoder` 없이 직렬화 → custom field_validator ValueError 시 **422 대신 500**. `POST /rag/ask {"question":"a"}`로 재현 |
| svc-breaker | `services/ai_processing.py:163` | RAG 스트리밍 circuit breaker가 mid-stream 실패 미집계 + 타 경로 카운터 오염 |
| svc-blocking | `services/chunked_transcription.py:113` | async 내 동기 파일 I/O(~19MB) → event loop 블로킹 |

### FE (15건 중 대표)
| ID | 위치 | 요지 |
|----|------|------|
| **header-404** | `components/layout/header.tsx:146-156` | 계정 드롭다운 '설정'이 존재하지 않는 `/workspace/{wid}/settings`로 이동 → **404 + full reload** |
| auth-provider | `app/(auth)/layout.tsx:5-13` | ThemeProvider/QueryProvider/Toaster 이중 중첩 → QueryClient 분리 + Toaster 중복 |
| sidebar-overfetch | `components/layout/sidebar.tsx:298` | inbox 배지 1개 위해 목록 전체 fetch + 클라 필터(페이지 초과 시 부정확) |
| breakpoint-flicker | `components/layout/panel-layout.tsx:19` | useBreakpoint 첫 렌더 항상 desktop → 모바일 진입 시 사이드바 깜빡임 (라이브 F-LIVE-2 정합) |
| dash-rehydrate | `features/projects/.../project-dashboard.tsx:118` | Zustand persist 리하이드레이션 윈도우에 로딩 대신 false-error 화면 (라이브 F-LIVE-2 정합) |
| rag-store | `features/rag/hooks.ts:16` | useRagStream 셀렉터 미사용 → SSE 토큰마다 cmd-k 포함 전 소비자 re-render |
| rag-scroll | `features/rag/.../rag-chat.tsx:76` | 매 토큰 smooth scrollIntoView → 스크롤 떨림 |
| dead-code | home/today-feed, notes/note-editor·note-list, actions/action-kanban·action-list | import 0건 dead code (라이브 F-LIVE-3 /actions 정합) |
| ui-store | `store/ui.ts:26` | useUIStore 셀렉터 미사용 → layout 골격 동시 re-render |
| api-multipart | `lib/api-client.ts:14` | Content-Type 강제 → multipart 헬퍼 2곳 복제 |

### UI/UX (25건 중 대표)
| ID | 위치 | 요지 |
|----|------|------|
| **light-muted** | `globals.css:150` | 라이트 `--text-muted #9E9EA6 = 2.55:1` (WCAG AA 미달). nav 라벨·캡션 전역 사용. 다크는 S28b에서 고쳤으나 라이트 방치 — **여러 에이전트 독립 발견** |
| landing-muted | `globals.css:260` | landing 다크 `--text-muted #5C5C63 = 2.98:1` (루트 #7A7A82와 불일치) |
| dark-variant | `globals.css:5` | `@custom-variant dark (.dark *)`인데 앱은 `data-theme` 토글 → **shadcn `dark:` 유틸 전부 무효**(hover/disabled 피드백 손실) |
| **rag-markdown** | `features/rag/.../rag-chat.tsx:125` | RAG 답변 마크다운 미렌더(`###`/`**` raw 노출, 렌더러 의존성 없음). 라이브 F-LIVE-1 |
| emoji-icons | inbox/meetings/projects/sources/rag/memory 전반 | 이모지를 구조 아이콘으로 사용 → DESIGN.md "emoji 금지 SVG만" 위반(lucide 이미 사용 중). 라이브 F-LIVE-5 |
| project-card-css | `features/projects/.../project-card.tsx:56` | `var(--status)20` 무효 CSS → status 배지 배경 투명 |
| accent-fg | notes 버튼 4곳 | accent 버튼이 `color: var(--background)` → 라이트 대비 미달(`--accent-foreground`여야) |
| signup-token | `(auth)/sign-up/.../page.tsx:18` | `--accent-bd` 미정의 토큰 → 베타 박스 border 미렌더 |

> P2/P3 296건은 토큰 하드코딩, 인라인 스타일, 추가 re-render, async-blocking 보조 경로, 작은 a11y(touch target/aria) 등. 전체 raw는 워크플로우 산출물(`tasks/wyzfixgo4.output`) 및 `/tmp/audit-*.json` 참조.

---

## 4. 라이브 검증 (트랙 C1) 요약

핵심 기능 **전부 PASS** — 상세 `live-findings.md`. AI 파이프라인(회의→요약+액션+날짜정규화), RAG(벡터+SSE+출처), inbox 적재, feedback, 모바일 반응형, landing 이미지, sign-in 모두 정상, 전 라우트 console errors 0.

**정정 사항(추측 아닌 재현)**:
- `GEMINI_API_KEY`는 **유효**(라이브 회의 처리 성공) → backlog `BL-S27c-2`(invalid)는 **stale**.
- inbox empty state·`/actions` route·landing 이미지·Promotion·음성메모 등 "미구현/결함"으로 알려진 항목 다수가 **이미 구현/해소됨**.

---

## 5. 로드맵/Phase 잔여 항목 (dev 단독 가능)

> ⚠️ Promotion 액션·음성메모 ingest·/actions route·failed-copy·inbox empty state·RAG 신선도 라벨·is_active 컬럼은 **이미 구현 확인 → 제외**. 아래는 코드 미존재 또는 carry 중 dev 가능 항목만.

**총 52건** (feature 10 · refactor 18 · perf 8 · hardening 10 · test 6). 전체 표는 `/tmp/audit-roadmap.json`. 우선순위 높은 것:

### 기능 (신규/개선)
- **BL-S27c-4 (P2,M)** Meeting 실패 후 retry — 동일 R2 audio reprocess endpoint + FE retry 버튼 (현재 '다시 업로드'만)
- **BL-NEW-RAG-SOURCE-SELECT (P2,M)** RAG 회의/노트 단위 검색범위 선택 (단, Power persona demand 미증명)
- **PRD-PDF-export (P3,M)** 회의/노트 PDF 내보내기 (MD/JSON은 구현됨)
- **ADR-007-L3 (P2,L)** 프로젝트 인사이트 컴파일 (회의 N건→지식문서 자동생성) — 큰 scope, paid 신호 후 권장
- BL-S27-3 AdminAccessAudit · BL-S27-1 is_active 토글 · BL-019 recall sparkline · BL-016 promote 라벨

### 성능 (P1 우선)
- **BL-S27e-C-PERF1 (P1,S)** R2/AI client singleton (매 호출 재생성 제거)
- **BL-S27e-C-PERF-r2-3 (P1,S)** RAG hybrid search 병렬 await (latency 직결)
- **BL-S27e-C-PERF1-list (P1,M)** list endpoint count+rows 쿼리 통합 (5 도메인)
- **BL-S27e-C-PERF3 (P1,M)** upload streaming (RAM 전량 적재 → Cloud Run OOM 완화)

### 하드닝 (P1 우선)
- **BL-S27e-A-SEC5 (P1,M)** audit_events 테이블 + invite/member hook
- **BL-S27e-A-SEC6 (P1,S)** rate-limit (slowapi RAG≤30/min, upload≤10/min)
- BL-013/049 alembic FK ondelete + production-scale guard · BL-S27e-3 CSP · BL-S27e-H 의존성 upper-bound

### 리팩토링·테스트
- **BL-S27e-F-ARCH (P2)** audit 도메인 분리 / core↔common cycle / OnboardingService DI / LazySeedService
- BL-001 meeting status commit 단일화 · BL-007/008/009/012/028 memory 모듈 정리 · BL-062 timezone-aware 전환(L, risk 높음)
- BL-011 memory 커버리지 보강 · BL-048 endpoint 전수 forward · BL-S27e-E test

### 외부 조치 필요 (dev 단독 불가, 11건) — 참고
Clerk Production 발급 · Sentry DSN · Cloud Run min-instance · **production 백엔드 재배포(crash-loop 인시던트)** · production DB cleanup · Clerk 키 rotation · F4 외부 인터뷰 · 외부 user 모집 · GitHub Actions 결제 복구. (~~GEMINI 재발급~~ = 이미 유효, 제외)

---

## 6. 즉시 수정 (P0 + 안전 quick-win)

> 본 검토에서 직접 수정한 항목(working tree, 커밋/푸시 미실행 — 별도 승인 필요).

### 수정 완료 (9건)

| # | 심각도 | 항목 | 파일 | 수정 내용 |
|---|--------|------|------|-----------|
| 1 | **P0** | notes BG 임베딩 닫힌 세션 | `notes/pipeline_service.py`·`dependencies.py` | `embed_note_async`가 `session_factory`로 fresh 세션 생성(meetings 패턴) + 회귀 테스트 갱신 |
| 2 | P1 | validation handler 500 | `main.py` | `exc.errors()` → `jsonable_encoder(exc.errors())` (custom validator ValueError 시 422 정상) |
| 3 | P2 | /me onboarding 필드 누락 | `auth/service.py` | `to_response`에 onboardingStep/onboardedAt 보강(camelCase 유지로 FE 회귀 회피) |
| 4 | P1 | 계정 '설정' 404 | `components/layout/header.tsx` | `window.location.href=/workspace/{wid}/settings` → `router.push("/settings")` |
| 5 | P1 | (auth) provider 이중 중첩 | `app/(auth)/layout.tsx` | ThemeProvider/QueryProvider/Toaster 제거 → children passthrough |
| 6 | P1 | project-card 무효 CSS | `features/projects/.../project-card.tsx` | `var(--x)20` → `color-mix(... 12% ...)` (배지 배경 렌더) |
| 7 | P1 | sign-up border 미렌더 | `app/(auth)/sign-up/.../page.tsx` | 미정의 `--accent-bd` → `color-mix(var(--accent) 25%)` |
| 8 | P1 | 라이트/landing 대비 미달 | `app/globals.css` | 라이트 `--text-muted #9E9EA6→#71717A`(4.6:1) + landing 다크 `#5C5C63→#7A7A82` |
| 9 | atomic | DESIGN.md 토큰 정합 | `DESIGN.md` | Text Muted 라이트/다크 표 갱신(다크 #5C5C63 stale 정정 포함) |

### 검증 결과
- **BE**: `pytest` **537 passed** (회귀 0 — P0 fix로 깨진 `test_embed_note_async_idempotent`를 fresh-session 패턴 + chunk-count 검증으로 갱신).
- **FE**: `pnpm typecheck` 에러 0 / `pnpm build` exit 0.
- **라이브**: sign-up 베타 박스 border 렌더 확인(`color(srgb … / 0.25)`), 라이트 `--text-muted` = `#71717a` HMR 반영 확인. (header/project-card는 build + 동일 color-mix 패턴 라이브로 보증, RBAC 재로그인 라이브는 미실행 — 3일 전 fullsweep 커버.)

### 미수정 — 보고서 권고 (사용자 판단 필요)
- **dead code 삭제** (TodayFeed+useActivityFeed / NoteEditor·NoteList+미사용 tiptap 의존성 / ActionKanban·ActionList) — 삭제는 surgical/dormant 정책상 사용자 확인 후.
- **RAG 마크다운 렌더링** (F-LIVE-1) — react-markdown+remark-gfm 도입 + citation 통합(의존성 추가·검증 필요, 단순 수정 아님).
- **이모지 아이콘 → lucide 일괄 교체** (inbox/meetings/projects/sources/rag/memory) — 광범위 + EmptyState prop 시그니처 변경 동반.
- **Tailwind `dark:` 변형 data-theme 정합** (globals.css:5) — shadcn 다크 상태 회귀 검증 필요.
- **landing 라이트 `--text-muted`(globals.css:205)** — landing 별도 테마/배경이라 대비 측정 후 별도.
- 그 외 BE P1(auth 캐시 stale/claim drop, projects/inbox 500, circuit breaker)·FE re-render(셀렉터 미사용)는 §3 참조 — 단건 수정보다 묶음 처리 권장.
