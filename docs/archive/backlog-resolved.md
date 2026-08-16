# 리팩토링 백로그 — 해소분 아카이브 (2026-08-16 분할)

> **역사 기록이다 — 소급 수정하지 않는다.** 경로 표기 `apps/backend/` 는 `apps/api/` 로 읽는다 (ADR-030 D2).
> 해소 사유(closure rationale)는 재발 방지 근거로 계속 인용되므로 삭제하지 않고 여기 보존한다.
> 미해소 BL 은 [`../REFACTORING-BACKLOG.md`](../REFACTORING-BACKLOG.md) 에 남아 있다.

---

## BL-QA0617-C — notes embedding-status `chunkCount` 오집계 (승격 노트) ✅ **반증 (코드 버그 아님, 2026-06-17 stacked PR)**

**결론**: Implementer 어드버서리얼 조사 + 실파이프라인 재현 결과 **코드 정상**. `_bg_promote_embed_note`(`notes/service.py:433,451`)가 복제 chunk에 `source_id=new_note_id` 설정, `count_note_chunks`(`notes/repository.py:108-116`)도 `source_id == note_id` 필터 → 두 컬럼 일치, 실파이프라인 promote 시 count=2 정상 반환. 라이브에서 본 `chunkCount:0`은 **probe 타이밍 아티팩트**(getEmbeddingStatus는 FE 미사용 — 직접 API 폴링이 BG copy commit 전/소스 id 대상으로 실행). **회귀 가드 테스트만 추가**(`test_promote_note_with_chunks_copy_reports_chunk_count` — 가설된 source_id 회귀를 방지). 코드 변경 없음.

## BL-QA0617-D — 동시 invite-accept → 500 (graceful 처리 부재) ✅ **FIXED (2026-06-17 stacked PR)**

**근거**: 2026-06-17 팀 QA(QA-0617-D). 동일 사용자가 같은 초대 코드로 accept를 **동시 2건** 호출 시 하나가 **HTTP 500**(`accept_invite` 의 `find_member` pre-check 후 `add_member` INSERT — 둘 다 pre-check 통과 → 하나가 `uq_workspace_member` UNIQUE 위반 → 미처리 IntegrityError). 라이브 재현 `[500,200]`, membership=1.
**fix**: `WorkspaceRepository.add_member` 를 `INSERT ... ON CONFLICT (workspace_id,user_id) DO NOTHING RETURNING` 로 race-safe 화(`WorkspaceMember|None` 반환). `accept_invite`/`service.add_member` 가 None → `MemberAlreadyExistsError`(409). pre-check는 fast path 유지, ON CONFLICT가 race backstop. flush+except 금지(`feedback_asyncpg_greenlet_precheck`). 실DB 동시성 회귀 테스트(`test_accept_invite_concurrent.py`: 동시 2건 → 1 ok + 1 MemberAlreadyExistsError, 500/IntegrityError/MissingGreenlet 0, membership=1).

## BL-QA0617-E — `PersonalWorkspaceProtected` 메시지 조사 플레이스홀더 ✅ **FIXED (2026-06-17 stacked PR)**

**근거**: 2026-06-17 팀 QA(QA-0617-E). I-19 차단 메시지 "초대**을(를)** 수행할 수 없습니다" — `{action}을(를)` 템플릿이 한국어 받침 조사 미처리. **fix**: `_object_particle(word)` 헬퍼(Hangul `(ord(last)-0xAC00)%28 != 0` → 받침有 "을"/無 "를", 비-Hangul "를" fallback) — `exceptions.py:41`. 메시지 → "개인 워크스페이스에는 초대를 수행할 수 없습니다". 단위 테스트 9 케이스(`test_exceptions_particle.py`).

## BL-QA0617-F — 멤버 목록 API `email` 빈 문자열 ✅ **반증 (코드 버그 아님, seed 데이터, 2026-06-17 stacked PR)**

**결론**: `invite_service.py:list_members` 는 이미 `"email": user.email if user else None` 로 User.email 직렬화 — 직렬화 경로 정상. 라이브 빈 email 은 **lazy-seed 유저의 실제 seed 데이터**(`auth/dependencies.py` 가 Clerk JWT email claim 부재 시 `email=""`). 코드가 실 User.email(빈 값 포함)을 정직하게 반환 — fabricate 금지. **가드 테스트만 추가**(`test_list_members_email.py` — User.email 와이어링 lock-in). 진짜 데이터 위생 이슈는 [[project_sprint28_fullsweep_qa_done]] BL-DATA-HYGIENE-SEED(Clerk JWT 템플릿) 소관(GA 연기).

---

## BL-S27c-8 — A11Y PopoverTrigger nativeButton 3 page 공통 ★ (P1) ✅ **이미 해소 (Sprint 27d BUG-S27d-1)**

**현 상태**: Dashboard / Projects / CmdK 진입 시 console error `Base UI: A component that acts as a button expected a native <button> because the nativeButton prop is true`. OnboardingTooltip 의 PopoverTrigger render prop 에 non-button.

**목표**: PopoverTrigger 의 `nativeButton` prop=false 또는 render slot 에 native `<button>` 전달.

**해소 확인 (Sprint 28d, 2026-05-29)**: `components/onboarding/onboarding-tooltip.tsx:123` 에 `nativeButton={false}` 이미 적용 (BUG-S27d-1 fix, Sprint 27d). backlog 미갱신이던 stale 항목 — Sprint 28d 코드 재확인 + grep 결과 다른 PopoverTrigger 사용처 없음.

---

## BL-S27c-12 — logout 시 `localStorage.kairos-workspace` clear ★★ (P1, Wave 4 발견) ✅ **완료 (Sprint 28d, 2026-05-29)**

**현 상태**: Clerk `signOut()` 후에도 `localStorage.kairos-workspace.activeWorkspaceId` 가 이전 user 의 workspace_id 잔존. 다른 user login 시 stale ID 사용 → cross-tenant API 호출 → 403 → UI 에 "워크스페이스 멤버가 아닙니다" 표시.

**증상**: Sprint 27c Wave 4 verify 중 재현 — Account #3 logout → Account #1 login 후 /new 페이지 진입 시 `1fcb8cf6-...` (Account #3 workspace) 호출 → 403. dashboard 는 graceful fallback (`/workspaces` list 후 retry) 동작, 다른 페이지는 fallback X.

**Fix 후보**: (a) Clerk `<SignOutButton onSignOutComplete>` hook 에 `localStorage.removeItem('kairos-workspace')` (b) Zustand persist onRehydrate 에 user_id verification 가드 (c) `kairos-workspace` 의 user_id 도 함께 저장 + activeWorkspaceId 와 비교.

**근거**: Sprint 27c Wave 4 audit `WAVE-4-VERIFIED.md`.

**해소 (Sprint 28d, 2026-05-29)**: 후보 (a)+(c) 조합. ① 정상 logout 경로는 `88eb306` 이 `onSelect→onClick` 정합으로 이미 동작(`setActiveWorkspaceId("")` + `queryClient.clear()`). ② 비-드롭다운 경로(세션만료/계정전환) 방어로 store 에 `ownerUserId` + `ensureOwner(userId)` 추가 — user id 만 비교해 워크스페이스 목록과 무관(race-free), `panel-layout.tsx` 에서 mount 시 호출 → 다른 user 면 stale `activeWorkspaceId` 즉시 초기화. 비어있으면 첫 워크스페이스 self-heal. 단위테스트 3건(`store.test.ts`).

---

## BL-S27e-1 — RAG latency p95 < 5s 목표 + 모니터링 (Sprint 27d carry) ★ (P3) ✅ **종결 (2026-07-05 — p50 목표 달성 / p95 꼬리는 쿼리-플랜 아님 수용)**

**2026-07-05 후속 (PERF-r2-6 + r2-7 구현, branch `sprint/stage2-perf-r2`)** — n=20 cold, `scripts/rag_timing_bench.py` 8필드 계측 (enrich/commit 분해 추가):

| stage | before p50 | after p50 | before p95 | after p95 |
|---|---|---|---|---|
| vector | 1,672 | **1,350** | 2,346 | **2,196** |
| text | 201 | 192 | 248 | 248 |
| enrich | 1,700 | **194** | 3,048 | **230** |
| commit | 200 | 190 | 220 | 200 |
| llm | 2,530 | 2,465 | 3,157 | 3,302 |
| **total** | **6,776** | **4,742** | **10,364** | **6,485** |

- **PERF-r2-7 (enrich — 최대 레버)**: 분해 계측이 원인을 재지정. 잔여 ~1,000ms 는 commit(1 RTT, 190ms)이 아니라 **enrich(1,700ms)**. 근본 원인 = `find_chunks_by_ids` 가 미사용 `embedding`(halfvec 1536) 컬럼까지 fetch/역직렬화(TOAST detoast) → 같은 커넥션 실측 full=3,450ms vs trim=194ms(μs 간격, RTT 아닌 데이터 증명). `defer(EmbeddingChunk.embedding)` 로 SELECT 제외 → enrich p50 1,700→194 / p95 3,048→230. ("배치/왕복 합침" 가설이 아니라 컬럼 트림이 실제 해법.)
- **PERF-r2-6 (vector)**: SET LOCAL 3문 → 단일 set_config(...,true)×3. vector p50 1,672→1,350 (~2 RTT). bench 는 time_range 로 cache skip → 헬퍼 1회만 계측; 프로덕션(무필터)은 cache lookup+vector = 헬퍼 2회 → RTT 4회 절감(bench보다 큼).
- **판정**: total p50 6,776→**4,742 (p50 목표 <5s 달성)** / p95 10,364→**6,485 (-37%, 여전히 >5s 미달)**. 개선이 시간대 노이즈 아님 — 내가 건드린 vector/enrich 2 구간만 이동, text/commit/llm 무변.

**종결 근거 — vector EXPLAIN ANALYZE (2026-07-05, 실 Neon)**: 실 production 쿼리(visibility EXISTS 절 + set_config 3종)를 (a)visibility 포함 (b)미포함 으로 `EXPLAIN (ANALYZE, BUFFERS)` 비교. 최다 청크 workspace(L2=60) 기준:

| | Execution (cold) | Execution (warm, median n=5) |
|---|---|---|
| FULL (w/ visibility EXISTS) | 33.8ms | 0.25ms |
| BASE (HNSW only) | 33.6ms | 0.53ms |
| **visibility 포스트필터 비용** | **≈ +0.2ms** | **노이즈 수준** |

→ HNSW 스캔(<35ms cold, <1ms warm) 도 visibility EXISTS(~0.2ms) 도 **p95 병목 아님**. vector p95 2,196ms 는 쿼리-플랜 비용이 아니라 **Neon 커넥션 cold + 왕복 오버헤드**(주 왕복은 PERF-r2-6 에서 이미 절감). **값싼 쿼리-레벨 win 없음** → 종결. (caveat: 현 데이터량 L2=60 소규모 — 데이터가 크게 늘어 HNSW 스캔 자체가 계측되면 재개.)

**잔여 p95 = LLM 스트리밍(p95 3,302) + Neon cold 커넥션 수용.** min-instances=1(BL-S27c-9)은 cold-start 제거로 p95 개선하나 **상시 인스턴스 비용 = 비용 결정(엔지니어링 제외)**. LLM first-token 체감·Sentry perf 분포는 별도 트랙.

**근거**: Sprint 27d opus audit BUG-S27d-6 (P3) + 2026-07-05 Stage 2 재평가 + PERF-r2-6/7 + 본 세션 EXPLAIN 실측.

---

## BL-S27e-2 — 사이드바 nav flicker 디버깅 (Sprint 27d carry) ★ (P3) ✅ **완료 (Sprint 28d, 2026-05-29)**

**현 상태**: Sprint 27d opus audit (agent-5 일반사용자) `/notes` 진입 시 사이드바 일부 nav link 가 일시 미표시 → 곧 정상 복원. useEffect dependency 또는 SWR cache hydration 타이밍 이슈 추정.

**목표**: render order 분석 + initial render 시 nav skeleton 또는 SSR-hydration 동기화.

**근거**: Sprint 27d opus audit BUG-S27d-7 (P3). 기능 손실 0, 시각 잡음.

**해소 (Sprint 28d, 2026-05-29)**: 루트코즈 = `sidebar.tsx` NAV_BOTTOM(`/notes`·`/new`, `requiresWrite`)이 `hasRole("member")` 로 필터되는데 `workspaceRole` 은 persist 제외(매 세션 `useSyncWorkspaceRole` 의 members API 로딩 후 설정) → 로딩 윈도우엔 null → 항목 숨김 → 역할 해결 후 등장 = flicker. fix = 역할 미해결(null)이면 낙관적 노출(쓰기 권한은 서버 강제, nav 가시성은 UX), viewer 로 확정될 때만 숨김. 다수(owner/member) 케이스 flicker 제거.

---

## BL-S27e-4 — FE CI 실패 재분류 (tiptap dep + Nightly Gemini key) ★ (P3)

**⚠️ Sprint 27e Round 2 재분류** (2026-05-25, TEST-r2-2): "병렬 E2E flake 2 spec" 가설 false. 실제 fail 은 (a) `frontend-build` 단계 tiptap useEditor overload type error (CI run 26389145626 — Round 1 PR #109 의 tiptap 4개 직접 의존성 3.22.0 vs transitive 3.23.6 peer 충돌, 이미 commit 2195c8b 으로 해소) + (b) Nightly `meeting-upload.spec.ts` GEMINI_API_KEY=fake (환경 결함). **flake 아닌 코드/환경 결함**.

**현 상태 (재분류 후)**:
- (a) tiptap dep: Round 1 PR #109 commit 2195c8b 으로 RESOLVED (`@tiptap/* 3.23.6` 통일)
- (b) Nightly Gemini key: 사용자 task — Nightly Heavy E2E workflow secrets 점검 필요

**Round 1 cited 가설 (stale)**: storageState 단일 공유 + onboarding localStorage race — Sprint 27d codex audit CODEX-OBS-1 의 추정. Round 2 의 CI history 재검증 (`gh run list --workflow=test.yml --limit 30 since 2026-05-21`) 결과 main 가지 5/5 PASS / flake rate 0% — 추정 false 확정.

**근거**: Sprint 27e Round 2 test-coverage-findings-r2.md §3 CI flake 정량. P3 유지.

---

## BL-S27e-5 — project delete 콘텐츠 FK 정책 ★ (P2) ✅ **완료 (2026-07-05, `sprint/bl-s27e-5-project-delete-fk`)**

**결정 (사용자 승인)**: 성격별 분리. 마이그레이션 0건 — FK 는 NO ACTION 유지, `repo.delete` 트랜잭션 내 app-level DELETE/UPDATE (workspaces cascade 와 동일 방식, 비소유 테이블은 raw `text()`).

**FK 범위 정정**: 백로그가 5테이블로 기재했으나 실제 `projects.id` 참조 콘텐츠/파생 = **6테이블** — `semantic_caches.project_id` 누락됨(안 다루면 500). "`memory.target_project_id`"는 실제 `promotion_audit.target_project_id`. (+ join 2: project_members/meeting_project_links 는 기존 선삭제.)

| 테이블 | 성격 | 처리 |
|---|---|---|
| `notes.project_id`, `action_items.project_id` | 사용자 콘텐츠 | **409-block** (service pre-check count) |
| `embedding_chunks.project_id`, `semantic_caches.project_id` | 파생 RAG 인덱스/캐시 | **DELETE** |
| `inbox_items.ai_suggested_project_id`, `promotion_audit.target_project_id` | 참조 포인터 | **SET NULL** |

**SET NULL 이 embeddings 에 위험한 근거(실증)**: `embeddings/repository.py` visibility 필터 첫 분기가 `project_id IS NULL` → **무조건 통과**. embedding_chunks 에 visibility 컬럼 없음(부모 project JOIN 파생) → private 프로젝트 detach 시 청크가 워크스페이스 전 멤버 RAG 에 노출 = 헌법 "RAG private 누수 0"(CONTEXT-MAP.md:96) 위반. → DELETE 로 원천 차단.

**구현**: `projects/exceptions.py` ProjectHasContentError(409) · `projects/repository.py` `count_content()` + `delete()` 4문 추가 · `projects/service.py` delete_project pre-check 409. race 는 pre-check(asyncpg+greenlet 에서 try/except IntegrityError 회피, [[feedback_asyncpg_greenlet_precheck]]). **검증**: BE pytest 650 pass (신규 6: 409 block×2 / 파생 purge / 포인터 SET NULL / empty private / FK introspection 드리프트 가드). FE onError sonner toast (project-detail/dashboard). E2E `t21-project-delete.spec.ts`(nightly team, 콘텐츠 409→노트삭제 204 / empty 204). 마이그레이션 없음.

**근거**: 2026-07-05 Stage 2 follow-up goal 4 이연분 + 본 세션 Explore(FK 6테이블 + visibility 누수 실증). BUG-PROJECT-DELETE-FK 후속.

---

## BL-S27e-A — 보안 hygiene cluster (Sprint 28 일부 RESOLVED, 일부 carry) ★ (P2)

**Sprint 28 일부 RESOLVED**:
- ✅ **SEC-3 (BUG-S28-SEC-3)** — JWT 검증 실패 4 except `logger.warning` + extra={error_type} 추가 (commit `feacccc` + `a1eea27`). pytest 4 case.

**Sprint 28 잔존 carry**:
- SEC-5 — `workspaces/invite_service.py:159-204` + `member_router.py` audit_events 테이블 + 4 endpoint hook
- SEC-6 — rate-limit (slowapi: RAG ≤ 30/min, upload ≤ 10/min)
- SEC-7 — `main.py:89-95` CORS allow_methods + allow_headers 화이트리스트
- SEC-11 — Sentry SKIP path forensic 표준화 (SEC-3 가 JWT 만 cover)

---

## BL-S27e-B — 보안 hardening cluster (Sprint 28 일부 RESOLVED, 일부 carry) ★ (P3)

- SEC-8 + r2-9 — 3 prompt 모두 `<<<SOURCE_BLOCK>>>` 구분자 통일
- SEC-9 — `common/r2.py:23-46` filename slugify + NFC + 길이 200
- ✅ **SEC-10 (BUG-S28-SEC-2)** — Sprint 28 fix: `r2-cleanup.yml:28` SHA pin 통일 (commit `5a199db`)

---

## BL-S27e-C — 성능 P1 cluster (Sprint 28 일부 RESOLVED, 일부 carry) ★★ (P1)

**Sprint 28 RESOLVED**:
- ✅ **PERF-4 (P0 격상)** — Gemini + Whisper timeout + circuit breaker (commit `1c2f8ff`, 7 test PASS)
- ✅ **BUG-S28-PERF-RT-1** — User + Member cache. dashboard 4286→1586ms (commit `feacccc`, 11 test)
- ✅ **PERF-2** — workspace_id 인덱스 3건 (alembic `be0e82ab810c`, commit `c8f777a`)

**2026-07-05 team-collab-audit RESOLVED**:
- ✅ **PERF-SSE-COMMIT (신규 발견, 최상위 병목)** — RAG 검색 read 트랜잭션이 Gemini 스트리밍(~10s) 내내 열려 커넥션 점유 → 동시 스트림 15개면 pool 고갈로 전체 API 블로킹. 스트리밍 진입 전 commit 으로 반납 (`rag/service.py`, 회귀 가드 `tests/rag/test_sse_connection_release.py` — 스트리밍 중 checkedout=0 검증, red-green 확인)
- ✅ **멤버 목록 N+1 (신규 발견)** — `invite_service.list_members` 멤버당 `find_by_id` 루프 (header 가 전 페이지 호출) → `list_members_with_users` 단일 JOIN (`workspaces/repository.py`)
- ✅ **PERF-1** — R2Service 공유 client (`_get_client` lazy + lock) + 모듈 싱글턴 `get_r2_service()` + main lifespan 래퍼에서 close (core→common 게이트 준수)
- ✅ **PERF-r2-2** — AsyncOpenAI/genai.Client 모듈 싱글턴 (생성자 identity 캐시 — 테스트 patch 자가 복원, `embeddings/service.py`·`services/ai_processing.py`·`services/transcription.py`)
- ✅ **PERF-5** — stale 종결: sse-starlette 2.x 가 `http.disconnect` 시 generator 자동 cancel — per-yield 체크 불필요
- ✅ **PERF-r2-5** — `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` env 설정화 (기본 5+10 유지). PERF-SSE-COMMIT 으로 주 고갈 원인 제거 — 상향은 Neon max_connections × 인스턴스 수 확인 후

**2026-07-05 Stage 2 재평가 (실측 n=20, `scripts/rag_timing_bench.py`) 종결**:
- ❌ **PERF-r2-3 — hybrid search 병렬화: 실측 기각.** rag.timing vector/text 분리 계측 후 20회 분포: vector p50=1,594ms / text p50=198ms → 병렬화 이득(=min(vector,text)) p50=**198ms** < 판정선(300ms 또는 total p50 5,721ms 의 10%=572ms). 세션 2개 분리 + pool 점유 +1 리스크 대비 이득 부족 — 종결. 재개 조건: 아래 PERF-r2-6/7 해소 후 text 구간이 커지는 데이터 변화 시.

**잔존 carry**:
- PERF-3 — `upload/router.py:91` streaming upload
- ✅ **PERF-r2-6 (2026-07-05 RESOLVED, `sprint/stage2-perf-r2`)** — `_apply_hnsw_session_params` 3 SET LOCAL → 단일 set_config(...,true)×3 (RTT 2회 절감). vector p50 1,672→1,350. I-21/E-8/ADR-020 문구 동기화(메커니즘 무관 표현, 사용자 승인). SHOW 기반 회귀 테스트 4건 green. BL-S27e-1 표 참조.
- ✅ **PERF-r2-7 (2026-07-05 RESOLVED, `sprint/stage2-perf-r2`)** — 분해 계측 결과 잔여 ~1,000ms 는 commit(1 RTT, 190ms)이 아니라 **enrich(1,700ms)**: `find_chunks_by_ids` 가 미사용 halfvec `embedding` 컬럼까지 fetch. `defer(embedding)` 로 enrich p50 1,700→194 / p95 3,048→230. rag.timing 에 enrich/commit 필드 상시 추가(bench regex 동기화). BL-S27e-1 표 참조.
- PERF-r2-4 잔여 — 1차 진입 lazy seed
- BUG-S28-PERF-1 — list endpoints single SQL window 또는 cursor pagination (5 도메인)
- BUG-S28-PERF-2 — Whisper API timeout 추가 spot (chunked_transcription)
- BUG-S28-PERF-3 — meetings BG audio streaming download

---

## BL-S27e-E — 테스트 정량 cluster (Sprint 28 일부 RESOLVED) ★ (P1/P2)

**Sprint 28 RESOLVED**:
- ✅ **TEST-5** — invite accept happy-path e2e (`invite-accept-happy-path.spec.ts` 신설)
- ✅ **TEST-7** — upload mime real browser e2e (`upload-mime-validation.spec.ts` 신설)

**잔존 carry**:
- TEST-3 — `vitest.config.ts` `coverage.include: ['src/**']`
- TEST-4 — `workspaces` 모듈 branch coverage
- TEST-6 — 회의 retry e2e
- TEST-8/9/10 — 큰 입력 / 유니코드 / Personal+Team 통합

---

## BL-S27e-G — Production cutover hardening (Sprint 27e Round 2 신규) ✅ **완료 (Sprint 27e Round 2, 2026-05-25)**

**해소**: PR #110 — SEC-r2-2/3/4 fix 묶음.
- `core/config.py` `_is_non_dev_env()` staticmethod 추출 (production + staging 통합 판정, OR + lower 일관성)
- `_validate_cron_token`: non-dev 환경 dev fallback 거부 + min 32 byte 강제
- `_no_dev_issuer_in_non_dev`: staging 도 dev Clerk issuer URL 거부
- `_require_audience_in_non_dev`: audience None default 가 `verify_aud=False` fallback 영구 SKIP 차단
- `tests/test_config.py` 4 신규 케이스 (staging 우회 + 약한 token + audience None + ENVIRONMENT-only) — 12/12 PASS

**근거**: Sprint 27e Round 2 security-findings-r2.md §2 r2-2/3/4. ADR-024 Clerk Production cutover 직격 결함.

---

## BL-S27e-4-OLD — FE 병렬 E2E flake (Sprint 27d 추정, false alarm) ✅ **재분류 (Sprint 27e Round 2)**

원 BL 본문은 위 BL-S27e-4 본문에 historical record 로 흡수. flake 가설 false 확정.

---

## BL-S26-3 — historical reference dead link cleanup ✅ **완료 (2026-06-23 ponytail cleanup)**

**현 상태:** Sprint 26 P0-3 dev-log/sprints+qa+notes 폐지 후 `docs/TODO.md` + `docs/REFACTORING-BACKLOG.md` 본문 (L50/95/145/200/1768/1835 등) 에 historical reference 다수 잔존. agy 검증 3회차 REVISE 지적.

**후보:** historical artifact 경로를 `git history` 참조로 치환하고, 필요한 경우 TODO.md 를 100줄 미만으로 슬림.

**의도:** historical reference 는 context 보존 가치 vs dead link risk trade-off. agy = "신규 AI 가 폐지 경로 읽으려 시도할 수 있음" 권고 → cleanup.

**결정:** historical audit/sprint/superpowers 산출물은 git history와 PR body로 보존. live docs 는 canonical docs 중심으로 유지.

**참조:** Sprint 26 verification 3회차 agy REVISE.

---

---

## BL-002 — process_meeting / capture_text 공통 로직 추출 ✅ **완료 (Sprint 11 PR3, 2026-05-12)**

**현 상태:**
`MeetingPipelineService`의 두 함수(360 LOC)가 요약 → 액션 추출 → Inbox 적재 → 임베딩 로직을 중복 작성. STT 이후 로직이 거의 동일.

**목표 인터페이스:**
```python
class MeetingPipelineService:
    async def process_meeting(self, meeting_id: UUID) -> None:
        """STT → 분석."""
        segments, duration = await self._transcribe(meeting_id)
        await self._analyze_and_store(meeting_id, segments, duration=duration)

    async def capture_text(self, meeting_id: UUID, transcript_text: str) -> None:
        """텍스트 입력 → 분석."""
        segments = await self._save_text_segment(meeting_id, transcript_text)
        await self._analyze_and_store(meeting_id, segments)

    async def _analyze_and_store(
        self,
        meeting_id: UUID,
        segments: list,
        duration: float | None = None,
    ) -> None:
        """공통: 요약 + 액션 + Inbox + 임베딩."""
        ...
```

**영향 파일:**
- `apps/api/src/meetings/pipeline_service.py` (360 LOC → ~250 LOC 예상)

**예상 LOC delta:** -100 ~ -110

**Risk:** 🟡 중간 — 파이프라인 핵심 코드, 테스트 3개로 회귀 검증 가능

**Test harness:** test_pipeline.py 3 테스트 존재. `_analyze_and_store` 단위 테스트 추가 권고.

**우선순위:** ★★★☆☆

**Sprint 묶음 권고:** BL-001과 묶어서 (Sprint 11+)

**근거:** deepen-modules audit 2026-05-12 (git history)

---

## BL-003 — RAG `_enrich_context` N+1 → 배치 쿼리 ✅ **완료 (Sprint 13 PR #21, 2026-05-12)**

**현 상태:**
`RagService._enrich_context()`가 결과 수(최대 10)만큼 `find_chunk_by_id()`를 루프 호출. `EmbeddingRepository`에 `find_chunks_by_ids(ids)` 배치 메서드가 없어 N+1 발생.

```python
# 현재 (N+1)
for r in results:
    parent_id = r.get("parent_chunk_id")
    if parent_id:
        parent = await self.embedding_repo.find_chunk_by_id(parent_id)
```

**목표 인터페이스:**
```python
# embeddings/repository.py 신규 메서드
async def find_chunks_by_ids(self, ids: list[UUID]) -> dict[UUID, EmbeddingChunk]:
    result = await self.session.execute(
        select(EmbeddingChunk).where(EmbeddingChunk.id.in_(ids))
    )
    chunks = result.scalars().all()
    return {c.id: c for c in chunks}

# rag/service.py 변경
parent_ids = [UUID(r["parent_chunk_id"]) for r in results if r.get("parent_chunk_id")]
parents = await self.embedding_repo.find_chunks_by_ids(parent_ids)
enriched = [
    {**r, "parent_text": parents.get(UUID(r["parent_chunk_id"]), None) and parents[UUID(r["parent_chunk_id"])].chunk_text or ""}
    for r in results
]
```

**영향 파일:**
- `apps/api/src/embeddings/repository.py` — `find_chunks_by_ids` 메서드 추가
- `apps/api/src/rag/service.py` — `_enrich_context` 배치 호출로 변경

**예상 LOC delta:** +12 (repository) / -8 (service)

**Risk:** 🟢 낮음 — 기존 메서드 제거 없음, 신규 추가만. 배치 반환 타입이 dict라 service 로직 소폭 변경 필요.

**Test harness:** 현 RAG service 단위 테스트 없음 (coverage ~0%). 마이그레이션 시 `test_rag_service.py` 신설 권고 — `_enrich_context` 단위 테스트 2건 (parent 있는 경우 / 없는 경우).

**우선순위:** ★★★★☆

**Sprint 묶음 권고:** 단독 (Sprint 12+). BL-001 meetings 상태 commit 단일화와 독립적. 저위험·고가치라 조기 처리 적합.

**근거:** deepen-modules audit 2026-05-12 Round 1 (git history)

---

## BL-004 — LLM 응답 계약 명시화 (암묵적 JSON 스키마 → Pydantic 검증) ✅ **완료 (Sprint 13 PR #21, 2026-05-12)**

**현 상태:**
`common/prompts.py`에 Gemini 응답 JSON 스키마가 프롬프트 텍스트 안에 문자열로만 존재. `ai_processing.py`는 `parse_json_response()` 결과를 타입 검증 없이 그대로 반환. `pipeline_service.py`는 `actions_data.get("actionItems", [])` 같은 문자열 키 접근에 의존.

프롬프트 스키마 변경 시 (`"key_decisions"` → `"decisions"` 등) 파싱 에러 없이 조용히 빈 값으로 저장됨. co-change 분석으로 발견: `ai_processing.py` 5회 변경 중 3회 이상이 `common/prompts.py` 동시 변경 — 수동으로 키 이름 일치 여부를 확인해온 패턴.

**목표 인터페이스:**
```python
# common/prompts.py 하단에 추가 (또는 common/llm_schemas.py 신설)
from pydantic import BaseModel

class MeetingSummaryResult(BaseModel):
    summary: str
    key_decisions: list[str] = []
    risks_and_issues: list[str] = []
    participants: list[str] = []
    topics: list[str] = []
    next_meeting_agenda: list[str] = []

class MeetingActionsResult(BaseModel):
    actionItems: list[dict] = []
    suggestedProject: dict = {}
    suggestedTags: list[str] = []

# ai_processing.py — 반환 타입 유지, 경계에서 검증 추가
async def summarize(self, transcript: str) -> dict:
    raw = parse_json_response(response.text)
    MeetingSummaryResult.model_validate(raw)   # 스키마 위반 시 즉시 ValidationError
    return raw                                  # caller 변경 없음

async def extract_actions_and_link(self, ...) -> dict:
    raw = parse_json_response(response.text)
    MeetingActionsResult.model_validate(raw)
    return raw
```

**영향 파일:**
- `apps/api/src/common/prompts.py` — Pydantic 모델 2개 추가 (또는 `common/llm_schemas.py` 신설)
- `apps/api/src/services/ai_processing.py` — 검증 2줄 추가 (summarize, extract_actions_and_link)

**예상 LOC delta:** +30 (스키마 모델) / +4 (검증 줄)

**Risk:** 🟢 낮음 — caller 변경 없음. `model_validate` 실패 시 Gemini 응답 파싱 에러로 처리 (현재도 ValueError로 처리 중, 에러 경로 동일).

**Test harness:** 현 ai_processing 단위 테스트 없음. 마이그레이션 시 `test_ai_processing.py` 신설 권고 — 스키마 불일치 시 ValidationError 발생 케이스 포함.

**우선순위:** ★★★☆☆

**Sprint 묶음 권고:** BL-003과 묶어서 (Sprint 12+). 둘 다 서비스 레이어 안전성 강화 방향으로 묶을 수 있음.

**근거:** deepen-modules audit 2026-05-12 Round 2 co-change 분석 (git history)

---

## BL-005 — memory.service.promote() Service Session 직접 접근 제거 ✅ **완료 (Sprint 19 PR #1 C10, 2026-05-18)**

**해소** (Sprint 27e Round 2 BUG-S27e-ARCH-7 verified):
- `apps/api/src/memory/service.py:405-505` `MemoryService.promote()` 가 `self.workspace_repo.find_by_id(target_workspace_id)` + `self.workspace_repo.find_member(...)` 사용 — WorkspaceRepository 경유.
- `grep "self.repo.session.execute" apps/api/src/memory/service.py` = **0 hit** verified.
- `MemoryService.__init__` workspace_repo 주입 강제 (line 424 fail-closed RuntimeError).

**근거**: Sprint 19 PR #1 C10 (Codex F-4), memory `project_sprint19_pr1_kickoff.md`. Sprint 27e Round 2 architecture-findings-r2.md §1 ARCH-7 verify.

---

(이하 historical record — closed 마크 위 본 BL 의 원 기록 보존)

**현 상태 (해소 전):**
`apps/api/src/memory/service.py:420, 431` — `MemoryService.promote`가 `self.repo.session.execute(target_q)` / `self.repo.session.execute(member_q)` 직접 호출. Backend Rules §3 (AsyncSession은 Repository만 보유) 위반. Workspace + WorkspaceMember 조회를 repo 위임 없이 inline.

**목표 인터페이스:**
```python
# workspaces/repository.py 확장
async def get_workspace(self, workspace_id: UUID) -> Workspace | None: ...
async def get_member(self, workspace_id: UUID, user_id: UUID) -> WorkspaceMember | None: ...

# memory/service.py promote()
target_ws = await self.workspace_repo.get_workspace(target_workspace_id)
member = await self.workspace_repo.get_member(target_workspace_id, promoted_by_user_id)
```

**영향 파일:**
- `apps/api/src/workspaces/repository.py` — 메서드 2개 추가 (이미 있을 가능성 있음, 확인 후 재사용)
- `apps/api/src/memory/service.py` — promote() session 호출 제거
- `apps/api/src/memory/dependencies.py` — WorkspaceRepository 주입

**예상 LOC delta:** +20 (repository) / -10 (service)

**Risk:** 🟢 낮음 — 동작 동일, 레이어 분리만

**Test harness:** `test_promote.py` 5 케이스 그대로 통과해야 함

**우선순위:** ★★★★★ (P0 헌법 위반)

**Sprint 묶음 권고:** BL-006과 묶어 Sprint 17 우선 처리

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-006 — memory → embeddings.create_chunk 직접 호출 → pipeline_service.py 분리 (ADR-014 위반) ✅ **완료 (Sprint 24 Wave 2 Phase 7, 2026-05-20)**

**현 상태 (해소 전):**
`apps/api/src/memory/service.py:550, :780` — `_bg_distill_and_embed` + module-level `_bg_promote_embed` 가 `from src.embeddings.repository import EmbeddingRepository` 를 lazy import 후 직접 `save_chunk` 호출. CONTEXT-MAP §4.2 + ADR-014 위반.

**해소 (2026-05-20):**
- 신설: `apps/api/src/memory/pipeline_service.py` — `MemoryPipelineService.save_memory_chunk(session, ...)` 가 `EmbeddingRepository.save_chunk` 호출 캡슐화. `source_type='memory'` 고정.
- 갱신: `apps/api/src/memory/service.py` — lazy import 2 hit 제거, `_bg_distill_and_embed` 와 `_bg_promote_embed` 가 pipeline 위임. `MemoryService.__init__` `pipeline: MemoryPipelineService | None = None` 추가, `_bg_*` 진입 전 fail-closed (`RuntimeError`).
- 갱신: `apps/api/src/memory/dependencies.py` — `MemoryPipelineService` 동반 주입.
- 회귀 방지: `apps/api/tests/architecture/test_no_memory_to_embeddings_lazy_import.py` 2 케이스 (lazy import 0 hit assertion + E-9 1 hit 유지 assertion).

**미해소 (E-9 예외 유지)**:
- `apps/api/src/memory/repository.py:33` 의 `from src.embeddings.repository import _apply_hnsw_session_params` 1 hit 는 vector_search HNSW SET LOCAL 위해 유지 (embeddings/CONTEXT.md E-9 — capsule 우회 최소 비용 약속, Sprint 16). vector_search 자체 흡수는 LOC vs 가치 비대칭으로 후속 sprint carry-over.

**테스트 결과**: pytest 406 → 408 + 1 skipped (architecture gate +2). 기존 memory 27 테스트 회귀 0.

**근거**: Sprint 24 Wave 2 trusty-heron plan / `git history` §"T-N+1 BL-006".

---

## BL-014 — Workspace switcher UI 누락 (Sprint 15 R5 spec gap) ✅ **완료 (Sprint 17, 2026-05-15)**

**현 상태:**
Stage 5-4 design-review (Playwright MCP) 2026-05-14. Sprint 15 R5에서 Personal workspace lazy seed 구현됨 (Lock vs Users 타입). BUT FE에 사용자가 Personal ↔ Team 사이 전환할 수 있는 switcher UI 부재.

- Topbar: 현재 워크스페이스명 "Kairos" + Users icon + member count "1" — 클릭 불가능한 plain text + badge
- Avatar dropdown: 유저 메뉴만 (다크 모드 / 설정 / 로그아웃) — workspace 전환 옵션 없음
- 사이드바: 프로젝트 트리만 — 워크스페이스 선택 없음

영향: Personal workspace seed가 되어도 사용자가 진입 불가. Sprint 15 R5 의도 부분 좌절.

**목표 인터페이스:**
- 옵션 A: Topbar workspace badge → dropdown switcher (DESIGN.md §Workspace Types "Workspace switcher dropdown options에 type badge inline")
- 옵션 B: Sidebar 상단 workspace selector 추가
- 옵션 C: `/workspace/[id]/...` route param 명시 (current = active workspace store만 기반)

**예상 LOC delta:** +80~120 (신규 컴포넌트 + store wiring)

**Risk:** 🟡 중간 — workspace store + RBAC 분기 영향

**Test harness:** E2E (Playwright) — Personal ws 진입 + 전환 + memory isolation 검증

**우선순위:** ★★★★☆ (P1 — Sprint 15 R5 spec 완결)

**Sprint 묶음 권고:** Sprint 16 (Best/Medium 분기 시 Promotion build와 묶기, Min 분기 시 별도 우선순위 평가)

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-41

---

## BL-015 — Workspace type badge (Lock/Users) 일관성 적용 ✅ **부분 완료 (Sprint 17, 2026-05-15)** — F-1 topbar + F-40 PromoteModal 완료. F-17 Recall card는 topbar switcher context redundancy 회피로 wontfix 결정.

**현 상태:**
Stage 5-4 design-review. DESIGN.md §Workspace Types lock-in (Sprint 15 patch):
- Personal: `Lock` icon + text-muted
- Team: `Users` icon + text-accent + bg-accent-subtle

BUT 실제 렌더 상태:
1. Topbar: Team workspace 진입 시 `Users` icon ✅ (단일 워크스페이스 case 정상)
2. Recall result card: type badge 누락 — 대신 "🔍 의미 매칭" semantic label
3. Memory item card 좌상단 corner: type badge 누락
4. PromoteModal dropdown option: Users icon ✅ (Team만 후보로 노출, 정상)

원인: BL-014 (switcher 없음) + Personal workspace에 가 본 적이 없어 Lock 분기 미검증.

**목표 인터페이스:**
- `<WorkspaceTypeBadge type="personal" | "team" />` shared component (`apps/web/src/features/workspaces/components/`)
- 사용 위치: switcher dropdown / topbar / recall card top-right / promote modal option

**예상 LOC delta:** +60 (신규 컴포넌트 + 4 호출처)

**Risk:** 🟢 낮음 — visual only

**Test harness:** Storybook or visual regression (없으면 design-review 재실행으로 검증)

**우선순위:** ★★★☆☆ (P2 polish — BL-014에 종속)

**Sprint 묶음 권고:** BL-014 후속 Sprint 16~17

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-1/F-17/F-40

---

## BL-017 — Mobile FAB collision with bottom nav ✅ **완료 (Sprint 22 OBN-04, 2026-05-19 PR #97 `22da49b`)**

**해소:**
Sprint 22 OBN-04 (FAB↔BottomNav collision fix) 에서 mobile viewport (`md:hidden`) FAB 의 `bottom-{nav-height + 16px}` margin 적용 + banner flex-wrap + mobile-responsive spec 통합 처리.

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-33 → Sprint 22 commit `22da49b` 에서 해소.

---

## BL-018 — DESIGN.md Sprint 15 patch drift (capture row + tabs + bottom nav 5th) ✅ **완료 (Sprint 17, 2026-05-15)**

**현 상태:**
Stage 5-4 design-review. DESIGN.md §Recall UI Layout이 Sprint 15 plan §3.4 Q1 A3 "B3 search-first FAB" 결정 이전 spec 그대로 유지:

```
[capture row: Mic button (lg) + Textarea (autosize, multi-line)]
[search bar: input + Cmd+K hint]
[tabs: Personal | Team]
```

실제 = search-first FAB layout (Mic row, search bar, tabs 미존재). Atomic Update §2 매트릭스 누락 retrofit 필요. Bottom nav 5th item DESIGN.md = "[검색]" but 실제 = "메모".

**목표 인터페이스:**
- DESIGN.md §Recall UI 갱신:
  - capture row 제거 (FAB로 통합)
  - tabs 제거 (single feed)
  - 또는 옵션 = Sprint 16 Best 분기 시 tabs 재도입 명시
- DESIGN.md Bottom Nav: "[검색]" → "[메모]" + 하단에 "Sprint 15 patch 2026-05-14" 기록

**예상 LOC delta:** +40 (DESIGN.md doc)

**Risk:** 🟢 낮음 (doc only)

**Test harness:** N/A (design-review에서 DESIGN.md 기준점이므로 fix 후 재실행 시 0 finding)

**우선순위:** ★★★☆☆ (P2 — atomic update 회수)

**Sprint 묶음 권고:** Sprint 16 첫 doc commit (Phase B와 묶음)

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-2/F-5/F-34

---

## BL-021 — e2e auth.setup Clerk koKR label selector mismatch ✅ **완료 (commit 2bf3df8)**

**해결:** `apps/web/e2e/auth.setup.ts:42` selector 를 `getByLabel(/email/i)` → `input[name="identifier"]` 로 정정. Clerk SDK standard input name 사용으로 locale-independent.

**현 상태:**
PR #29 CI e2e job fail (5m timeout). main에서 이미 같은 fail inherit (run 25825914554, 2026-05-13 push sha 8311620 이후). 본 PR 책임 아님 — auth.setup.ts 본 PR diff 0 (Sprint 14에서 마지막 수정).

직접 원인:
- Clerk SignIn component label = "이메일 주소" (koKR localization 적용 `9ea1a78 fix(auth): T-3 Clerk koKR localization + /dashboard force redirect`)
- e2e selector = `getByLabel(/email/i)` 영문 정규식만
- 한국어 label "이메일 주소" → `/email/i` 매치 0 → 60초 timeout → 3 retry fail → 7 후속 test "did not run"

증거:
- 사용자 local sign-in 페이지 스크린샷 (2026-05-14) — embedded SignIn form 정상 렌더, label "이메일 주소", continue button "계속"
- main last fail (25825914554) + PR #29 fail (25850407909) 동일 step / 동일 line / 동일 error message
- auth.setup.ts:42 `getByRole("button", { name: /continue|계속/i })` 이미 한국어 매치 ✅. line 39만 누락

**목표 인터페이스:**

가장 robust 옵션 (locale-independent):
```ts
// before
await page.getByLabel(/email/i).fill(email);
// after — Clerk SignIn component standard input name (locale 변화 무관)
await page.locator('input[name="identifier"]').fill(email);
```

대안 (regex 확장):
```ts
await page.getByLabel(/email|이메일/i).fill(email);
```

추천: `input[name="identifier"]` (Clerk SDK standard, 향후 locale 추가 시 미영향).

**예상 LOC delta:** +1/-1 (auth.setup.ts:39 1줄 patch)

**Risk:** 🟢 낮음 (test file only)

**Test harness:** PR push 후 GitHub Actions e2e job 재실행 통과 확인

**우선순위:** ★★★★☆ (P1 — CI 통과 정상화. main + 모든 후속 PR에 영향)

**Sprint 묶음 권고:** 별도 hotfix PR 또는 Sprint 16 첫 commit. Sprint 15 PR #29 직전 분리 권고 (PR #29 머지 무관, e2e fail은 동일 상태 유지).

**근거:** Sprint 15 Stage 5-6 qa Exhaustive 후속 진단 2026-05-14 — 사용자 화면 증거로 root cause 정정 (Clerk Account Portal redirect 아님, koKR label mismatch 확정).

---

## BL-027 — e2e auth.setup 외부 의존 (BE URL) 503/HTML 보호 ✅ **완료 (2026-05-15 fix PR)**

**도메인:** frontend / e2e / devops
**근거:** Sprint 16 PR #30 머지 후 main e2e 회귀. E2E_API_URL이 가리키는 Cloud Run service가
404 HTML 반환 → `auth.setup.ts:69` `(await createRes.json()).id` SyntaxError.
원인 = Cloud Run service URL stale 또는 redeploy 누락 (PR #30 머지 14h 전 main e2e success
시점 ~ 본 PR 머지 후 e2e fail 시점 사이 외부 환경 변화).

**증거:**
- run 25874617335 (PR #30 candidate) + rerun: 2회 fail (`SyntaxError: Unexpected token '<', "<html><hea"... is not valid JSON`)
- run 25862668773 (main 9cdee27, 코드 변경 0) rerun: 동일 fail
- 추정 Cloud Run URL curl: `404 Page not found` HTML — e2e 응답과 패턴 매칭

**fix:**
- `apps/web/e2e/auth.setup.ts` GET/POST 응답 `.ok()` 가드 + 명시 error 메시지 (status + apiUrl + body[0..200])
- 기존 `.json().catch(() => [])` silent fallback 제거 (503 시 wsList=[] 분기로 빠져 POST에서 다시 SyntaxError 발생하는 도미노 차단)
- 후속 = 사용자 GCP 콘솔에서 E2E_API_URL secret 갱신 (또는 Cloud Run service 재배포)

**예상 효과:**
- 동일 회귀 재발 시 fail 1번에 원인 출력 (전: SyntaxError stack ×3, 후: `status=404 apiUrl=... body=<html>... → E2E_API_URL ... 점검 필요`)
- CI 디버깅 1 round trip 단축

**Risk:** 🟢 낮음 (e2e 가드만, 런타임 영향 0)

**우선순위:** ★★★★☆ (회귀 진단 시간 직결)

**Sprint 묶음:** BL-021 (Sprint 15 hotfix-2 Clerk koKR selector mismatch) + 본 BL-027 status code 보호 = auth.setup hardening 2건 누적.

---

## BL-029 ✅ RESOLVED (Sprint 18, qa-fix-bl029-rag-sse-helper) — rag/pipeline_service.py SSE error 공용 helper

**도메인:** backend / rag

**해결:** 2 helper 추출.
- `_sse_error_done(message: str) -> tuple[dict, dict]` — error + done 이벤트 쌍 한 번에 (모듈 레벨 함수)
- `_check_project_access()` 메서드 — find/draft/private 3 분기를 하나의 `str | None` 반환 헬퍼로 통합

3 yield 블록 (각 8 줄) → 1 호출 + for-yield 2 줄. 본문 87 줄 → 96 줄 (helper 분리로 net +9 줄이지만 응집도 ↑, ADR-014 옵션 A 검증 정합 확보).

**테스트 추가:** `tests/rag/test_pipeline_service.py` 9 케이스 — helper + 7 visibility 시나리오 (admin 우회 / project 부재 / draft 미작성자 / private 미멤버 / private 멤버 OK / public OK / project_id 없음).

**근거:** Sprint 18 BL-029 follow-up.

---

## BL-030 — tests/services/test_transcription.py ffmpeg fixture 환경 의존 ✅ **완료 (Sprint 19)**

**해결:** test 에서 `src.services.transcription.convert_to_wav` 를 `_fake_convert_to_wav` stub 으로 patch 추가. ffmpeg 실제 호출 회피 — fake bytes (`b"fake_audio_bytes"`) 가 ffprobe 의 mp3 detection score 임계값에 영향받지 않게 차단. 157 pytest pass.

**도메인:** backend / tests
**근거:** Sprint 18 PR-C 검증 시 1 fail. `test_transcribe_returns_segments` 가 `ffmpeg` mp3 fixture 를 invalid 데이터로 호출 → ffmpeg `Format mp3 detected only with low score of 1. Failed to find two consecutive MPEG audio frames`.

**문제:**
- fixture mp3 가 binary 가 아닌 placeholder/text 가능성.
- 또는 ffmpeg 8.1.1 의 mp3 detection score 임계값 변경.
- CI 미정 — local 만 fail 인지, CI 도 fail 인지 미확인.

**해결 후보:**
- valid mp3 fixture 재생성 (LAME 또는 ffmpeg `-f lavfi -i sine`).
- 또는 transcription 테스트 mock 화 (실제 ffmpeg 호출 회피).

**예상 LOC delta:** fixture 1개 + 테스트 1~2줄 수정.

**Risk:** 🟢 낮음.

**우선순위:** ★★★☆☆ (회귀 시그널 회복).

**Sprint 묶음:** 단독 또는 BL-030 + transcription 테스트 정비.

**근거:** Sprint 18 검증 산출물.

---

## BL-031 ✅ RESOLVED (Sprint 18, qa-fix-bl031-domain-error-boundaries) — ErrorBoundary 도메인별 page-level 도입

**도메인:** frontend / reliability

**해결:** 5 도메인 error.tsx 신설 — 한 도메인 에러가 (app) 전체로 번지지 않도록 격리.
- `app/(app)/projects/[id]/error.tsx` — 프로젝트 권한/삭제 fallback + "대시보드로" 이탈 CTA
- `app/(app)/meetings/[id]/error.tsx` — STT/AI 처리 중 폴링 실패 fallback + "대시보드로"
- `app/(app)/inbox/error.tsx` — AI classify 서버 일시 장애 fallback
- `app/(app)/memory/error.tsx` — recall/promote 지연 fallback + "이미 저장된 메모는 안전" 안내
- `app/(app)/search/error.tsx` — RAG 임베딩 검색 장애 fallback + 키워드 단순화 안내

각 파일은 `reset()` + `digest` 표시 + 도메인 아이콘 (📁🎙️📥🧠🔎). group-level (`(app)/error.tsx`) 는 fallback-of-fallback 으로 유지.

**근거:** Sprint 18 BL-031 follow-up.

---

## BL-032 — superpowers/ stale doc 자동 archive 정책 ✅ **완료 (2026-06-23 ponytail cleanup)**

**도메인:** docs / 운영
**근거:** Sprint 18 PR-B 에서 superpowers/ 24 파일 archive 시도 후 revert (스킬 자동 산출 위치라 archive 부적합). 향후 신규 plan/spec 도 시간 지나면 stale — 정책 없으면 누적.

**결정:** historical superpowers 산출물은 git history와 PR body로 보존. live docs 에는 active plan/context notes만 둔다.

**예상 LOC delta:** -34 files.

**Risk:** 🟢 낮음.

**우선순위:** ★☆☆☆☆ (장기 — 누적 임계 시 진행).

**Sprint 묶음:** 단독, Sprint 25+ 추정.

**근거:** Sprint 18 PR-B revert (commit 51f8210).

---

## BL-034 ✅ RESOLVED (PR #41, 2026-05-15)

**제목**: asyncpg.InterfaceError "connection is closed" intermittent — Neon pool stale connection

**도메인**: backend / DB pool

**증상**: 다양한 API 호출 (clerk_id 기반 user lookup 등) 첫 호출 시 sqlalchemy.exc.InterfaceError "connection is closed" 발생 → 재시도 시 200. console 에 간헐적 500 에러 노출.

**원인 가설**:
- asyncpg connection pool 의 idle connection 재사용 시 Neon idle timeout 으로 이미 닫힌 connection 사용
- `pool_pre_ping` 미설정
- pool recycle 시간 미설정

**해결 방향**:
- `apps/api/src/core/db.py` 또는 engine config 에 `pool_pre_ping=True`, `pool_recycle=300` 추가
- 또는 asyncpg 의 `connection_class` 에서 `before_first_query` health-check

**우선순위**: ★★★☆☆ (P1 deferred — intermittent, 사용자 noticeable 하지만 retry 로 우회)

**근거**: Sprint 17 QA verification (2026-05-15), ISSUE-006. `/tmp/kairos-be.log` 스택트레이스 다수.

**Sprint 묶음**: 단독 또는 Sprint 18 DB hygiene.

---

## BL-035 ✅ RESOLVED (PR #43, 2026-05-15)

**제목**: workspace switcher 중복 이름 표시 — 5 duplicate "E2E 테스트 워크스페이스" 구분 불가

**도메인**: frontend / workspace switcher UX

**증상**: workspace switcher 에 5개 동일 이름 항목 표시. UUID 다름. 사용자가 어느 것을 고를지 알 수 없음. auth.setup.ts 의 "워크스페이스 보장" 로직이 race 또는 반복 실행으로 누적된 결과.

**해결 방향**:
- FE: 같은 이름 workspace 가 2+ 일 때 created_at 또는 ID 접미사 표시 (`E2E 테스트 워크스페이스 (1)` ... `(5)` 또는 `#1` 등)
- BE: 동일 owner + 동일 name + 동일 type unique constraint (alembic migration)
- Data: dev 환경 cleanup 스크립트

**우선순위**: ★★☆☆☆ (P2 — UX 만, 데이터 손실 없음)

**근거**: Sprint 17 QA, ISSUE-002.

---

## BL-036 ✅ RESOLVED (PR #45, 2026-05-16) — production 효과 측정은 별도

**제목**: 비 dashboard 라우트 sidebar project list 3-6s 지연 로딩

**도메인**: frontend / React Query staleTime + API perf

**증상**: /inbox, /memory, /notes, /search, /settings 등 진입 시 sidebar 가 "프로젝트 없음" 로 3-6s 표시 → 이후 project list 표시.

**원인 가설**:
- `useProjects` 의 staleTime / cacheTime 부족
- 라우트 변경 시 cache 무효화 후 refetch
- BE projects?status=active 응답 자체 느림 (2-4s)

**해결 방향**:
- React Query staleTime 1-2분 설정 (router 변경에 cache 유지)
- BE projects N+1 또는 join 패턴 확인

**우선순위**: ★☆☆☆☆ (P3 perf — 사용자 체감 가능하지만 blocking 0)

**근거**: Sprint 17 QA, ISSUE-003.

---

## BL-038 ✅ RESOLVED (PR #42, 2026-05-15)

**제목**: 초대 링크 생성 직후 invite list 미반영 — React Query cache invalidation 누락

**도메인**: frontend / `features/members`

**증상**: settings → 초대 → "초대 링크 생성" → toast "초대 링크가 생성되었습니다" 성공 → invite list 는 "아직 초대 링크가 없습니다" 유지 → reload + tab 재진입 시에야 표시.

**해결 방향**:
- `useCreateInvite` (또는 동등 mutation) `onSuccess` 에 `queryClient.invalidateQueries({ queryKey: inviteKeys.list(wid) })` 추가

**우선순위**: ★★☆☆☆ (P2 — UX, 1-2 line fix)

**근거**: Sprint 17 QA, ISSUE-007.

---

## BL-039 ✅ RESOLVED (PR #42, 2026-05-15)

**제목**: /settings 초대 탭에서 member 진입 시 빈 헤더만 노출 — 명시적 권한 에러 메시지 미표시

**도메인**: frontend / `app/(app)/settings/page.tsx` + 초대 panel

**증상**: member 역할로 /settings → 초대 탭 → 헤더 "초대 링크" 만 보이고 list / 생성 버튼 / 권한 부족 메시지 모두 미표시. BE 가 403 반환하지만 FE 가 명시 에러 처리 안 함.

**해결 방향**:
- `useInvites` (또는 동등) 에서 403 응답 시 "관리자 권한 필요" 등 명시 placeholder 렌더
- 또는 `hasRole("admin")` 가드로 탭 자체 비활성/숨김

**우선순위**: ★☆☆☆☆ (P3 UX — 동작은 정상 (member 가 못 만듦), 메시지만 미흡)

**근거**: Sprint 17 QA, ISSUE-010.


---

## BL-040 ✅ RESOLVED (PR #46, 2026-05-16)

**제목**: 글로벌 RAG 쿼리 visibility leak — vector_search / text_search 에 ADR-014 필터 누락

**도메인**: backend / rag + embeddings (security)

**증상**: Member (non-ProjectMember) 가 글로벌 RAG 쿼리 (project_id=None) 시 private project 의 embedding chunks 가 결과 + AI 답변에 포함됨. ADR-014 R-10 위반.

**해결**: `_visibility_filter_sql()` 헬퍼 + vector_search / text_search 에 requester_user_id + requester_role 추가. admin/owner 우회, member/viewer 는 public/draft(creator)/private(ProjectMember) 분기.

**원래 BL 등재 시 ISSUE-040**. Sprint 17 본 세션에서 발견 + 즉시 PR #46 으로 fix.

---

## BL-041 ✅ RESOLVED (PR #54, 2026-05-16)

**제목**: find_similar_cache leak — admin 이 만든 private 포함 cache 가 비-멤버 hit 시 노출

**도메인**: backend / embeddings + rag (security)

**증상**: ISSUE-040 후속 — vector_search 는 가드 적용했지만 semantic_caches 에 저장된 답변/sources 는 cache hit 경로로 누출 가능. 7일 TTL 안 noticeable.

**해결**: find_similar_cache 가 cache hit 시 sources chunks 의 visibility 를 anti-join 으로 검증. 위반 시 cache miss 처리. admin/owner 는 우회 (정책 일관).

---

## BL-042 ✅ RESOLVED (PR #59, 2026-05-16)

**제목**: semantic_caches.max_visibility 컬럼 — BL-041 검증 fast path

**도메인**: backend / embeddings

**증상**: BL-041 fix 가 cache hit 마다 _all_chunks_visible anti-join 1회 실행. public-only cache (대다수) 도 검증 비용 발생.

**해결**: alembic d4e5f6a7b8c9 — semantic_caches.max_visibility (text NOT NULL DEFAULT 'public') 추가. cache 저장 시 sources 의 max visibility 계산. read path 에서 max_visibility='public' 이면 검증 skip (fast path), 그 외 BL-041 anti-join 진행.

---

## BL-043 ✅ PARTIAL RESOLVED — meeting-upload e2e nightly + R2 cleanup script

**도메인**: ci / e2e

**해결 (PR #69)**: `.github/workflows/nightly-e2e.yml` cron 으로 heavy spec 분리.

**해결 (Sprint 18, qa-fix-r2-cleanup-script)**: R2 nightly cleanup script + workflow.
- `apps/api/scripts/r2_cleanup.py` — aioboto3 비동기, uploads/ prefix 의 N 일 이상 객체 dry run/--delete
- `.github/workflows/r2-cleanup.yml` — workflow_dispatch 수동 트리거 전용 (cron 은 사용자 검증 후)
- 안전 기본값: DRY RUN, max-keys 10000, prefix uploads/

**잔여**: cron 자동화 (사용자 검증 후 추가). fake Whisper response mock 은 별도 결정.

**근거**: Sprint 17 closeout, PR #67/#69 + Sprint 18 R2 cleanup.

---

## BL-044 — RESOLVED (Sprint 18, qa-fix-bl044-source-upload)

**제목**: SourceAddModal 의 attachment 실제 업로드 구현 — toast-only placeholder

**도메인**: frontend / `features/upload/components/source-add-modal.tsx`

**해결**: 새 BE 도메인 신설 대신 기존 notes / meetings API 재사용:
- **paste 탭** → `useCreateNote` + tiptap 문서 (제목 옵션, 본문 textarea → paragraph 노드)
- **url 탭** → `useCreateNote` + URL 링크 마크 + 선택 메모. 호스트명 자동 추출하여 노트 제목 사용
- **file 탭** — 형식별 분기:
  - 오디오/비디오 (`audio/*` / `video/*`) → `usePresignedUpload` + `useCreateMeeting` → STT 파이프라인 (기존 /new Upload 와 동일)
  - 텍스트 파일 (.txt/.md, `text/*`) → `file.text()` → `useCreateNote`
  - 기타 (PDF/이미지/doc) → "곧 지원될 예정" toast (BL-044 후속)

**근거 (취소된 원안)**: 새 BE source 도메인 + alembic 신설은 큰 scope. 실제 사용자 face 는 메모로 적재되면 충분 — notes 가 워크스페이스 단위 자료 보관소 역할을 이미 수행. PDF/이미지는 후속 BL 으로 분리.

**잔여 후속**: PDF/이미지/docx 파싱 (텍스트 추출 후 note 적재) 별도 BL 등재 필요 시 추가.

---

## BL-050 — 잔여 cross-workspace single-FK entity audit + composite FK 신설 (BUG-C01-EXT-FK 잔여) 🟡 **PARTIAL (Simple 4 완료, 2026-05-18 Sprint 21 PR #96)**

**도메인**: backend / multiple (inbox / embeddings / memory / promotion)

**증상**: Sprint 19 PR #2 BUG-C01-EXT-FK = **project_id only hardening** (action_items / notes / mpl / project_members). 다음 7+ entity 는 cross-workspace single-FK 로 남음:
- `action_items.meeting_id` ↔ meetings.workspace_id (audit 없음)
- `inbox.ai_suggested_project_id` ↔ projects.workspace_id
- `embeddings.project_id` ↔ projects.workspace_id
- `semantic_cache.project_id` ↔ projects.workspace_id
- `memory_items.embedding_chunk_id` ↔ embedding_chunks.workspace_id
- `memory_ai_calls.memory_id` ↔ memory_items.workspace_id
- `promotion_audit` (source + target workspace_id 2개 보유, intentional cross-workspace — 별도 분석)

PR #1 audit 4 case (action_items.project_id / notes.project_id / mpl / project_members) 외 영역.

**해결 방향**:
1. integration audit SQL 7+ 추가 (`test_workspace_integrity_audit.py` 확장)
2. mismatch 0 보장 확인 후 composite FK 신설 (PR #2 패턴 그대로)
3. nullable 컬럼은 MATCH SIMPLE 면제 test 추가
4. alembic 단일 revision 으로 묶음

**우선순위**: ★★★☆☆ (P2 defense-in-depth 확장, Sprint 20 carry-over)

### Simple 4 완료 (Sprint 21 PR #96, 2026-05-18)

- ✅ action_items.meeting_id (composite FK + audit)
- ✅ inbox_items.ai_suggested_project_id (composite FK + audit)
- ✅ embedding_chunks.project_id (composite FK + audit)
- ✅ semantic_caches.project_id (composite FK + audit)

### 회귀 안전망 (Sprint 24 Wave 2 T-N+2, 2026-05-20)

`apps/api/tests/fixtures/composite_fk.py` + `apps/api/tests/integration/test_composite_fk_scn_matrix.py` —
SCN-FK-01~12 매트릭스 (4 entity × 3 op = 12 case) 자동화. 회귀 시 SCN ID 로 즉시 식별.
기존 `test_workspace_fk_cross_tenant_block.py` (7 case) 와 상호 보완.

### Carry-over (Sprint 22+)

- memory_items.embedding_chunk_id — embedding_chunks(id, workspace_id) UNIQUE 선행 작업 필요
- memory_ai_calls.memory_id — memory_items(id, workspace_id) UNIQUE 선행 + NOT NULL FK 패턴 다름
- promotion_audit (source/target workspace_id) — intentional cross-workspace, 별도 분석

**근거**: Sprint 19 PR #2 plan agent §D scope omission, Codex 1차 F-8.

---

## BL-052 — 잔여 model 파일의 sqlalchemy → SQLModel import 통일 (codebase consistency) ✅ **완료 (cleanup PR, 2026-05-18)**

Sprint 19 PR #2 D9 commit (43a0eb4) 가 4 model 파일 (projects/notes/actions/meetings) 통일. 본 cleanup PR 가 잔여 17+ 파일 (3 model + 12 repo/service/main + 6 test) 완료.

### D9 commit msg 정정

D9 message 는 "select/delete/update/text/func/and_/or_/AsyncSession/JSONB 모두 SQLModel 미 re-export" 라고 명시했으나, 실제 empirical 검증 결과:
- **Re-export 가능 (Category A)**: `select, delete, update, text, func, and_, or_, exists, bindparam, distinct, JSON, Column, Text, ForeignKeyConstraint, UniqueConstraint, Index` 등 모두 sqlmodel 가 직접 re-export
- **Re-export 불가 (Category B)**: `async_sessionmaker, create_async_engine, JSONB, IntegrityError, pg_insert, HALFVEC` + alembic versions/*.py 의 `import sqlalchemy as sa` 한정

### 본 cleanup PR 진행 결과 (7 commit, 21 파일)

- **C1**: embeddings/inbox/memory model — JSON/Column/Text → sqlmodel
- **C2~C4**: auth/workspaces/projects/notes/actions/meetings/embeddings/inbox/memory/rag repository — query builder 통일 (inline import 3건 포함)
- **C5**: main.py text → sqlmodel
- **C6~C7**: tests/conftest.py + 5 test 파일 — text/select 통일

**검증**:
- 317 PASS 회귀 (변경 전과 동일)
- D7.5b drift detection 0 (re-export 는 동일 객체)
- pyright errors 172 (origin/main) → 100 (본 PR, 72 감소) — SQLModel typed result 가 더 좋음
- Codex 1차 plan review REVISE → 5 finding (plan 결함만, 모두 수락 후 patch)
- Codex 2차 diff review APPROVE (finding 0)

### 잔여 BL carry-over

- **BL-053**: AsyncSession 통일 (Level 3) — sqlmodel.ext.asyncio.session.AsyncSession 으로 전환 + common/database.py:class_= 변경 + 19+ 파일 type cascade. SQLAlchemy AsyncSession 의 subclass 라 안전하지만 별도 PR.
- **BL-054**: session.execute(stmt).scalars().all() → session.exec(stmt).all() migration (SQLModel typed result + boilerplate 제거).

**근거**: Sprint 19 PR #2 D9 commit + 사용자 피드백 (2026-05-18, 전수 조사 + 수정 요청).

---

## BL-053 — AsyncSession 통일 (Level 3, sqlmodel.ext.asyncio.session.AsyncSession 전환) ✅ **완료 (Sprint 20 cleanup PR #92, 2026-05-18)**

Sprint 20 cleanup PR #92 (branch `cleanup/bl-053-async-session`, origin/main@195b8e3 기반 5 commits).

### 본 PR 완료 결과 (5 commits, 29 파일)

```
E7.9a 10d8752 refactor(bl-053): E7.9a Codex 2차 review MINOR 2건 수락 fix (2 파일)
E4    84a9841 refactor(bl-053): E4 tests — AsyncSession SM cascade + fixture smoke (5 + 1 신규)
E3    21dab73 refactor(bl-053): E3 repository — AsyncSession SM cascade (9 파일)
E2    fa52d7a refactor(bl-053): E2 dependencies + rbac + main — AsyncSession SM cascade (10 파일)
E1    2482456 refactor(bl-053): E1 entry — AsyncSession SM 양분 import + class_= 통일 + smoke test
```

### Scope (29 파일, Level 3)

| 영역 | 객체 | 파일 수 | commit |
|---|---|---|---|
| Entry (양분 import) | `class_=AsyncSession` + `async_sessionmaker` 동반 | 5 (common/database, memory/{service,dependencies}, meetings/{pipeline_service,dependencies}) | E1 |
| Dependencies + rbac + main | `from sqlmodel.ext.asyncio.session import AsyncSession` (single import) | 10 (8 deps + auth/rbac + main) | E2 |
| Repository | type annotation cascade | 9 (actions/auth/embeddings/inbox/meetings/memory/notes/projects/workspaces) | E3 |
| Tests | conftest 양분 + 4 integration | 5 | E4 |
| Fixture smoke (신규) | `test_integration_session_is_smodel_async_session` + 의존 fixture cascade | 1 신규 (Codex MINOR-4) | E4 |
| Codex MINOR fix | smoke global reset + memory/service docstring 정정 | 2 (Codex 2차 MINOR-1+2) | E7.9a |

### Category B 영구 유지 (sqlalchemy.ext.asyncio)

- `async_sessionmaker` (5 파일): common/database.py, meetings/dependencies.py, meetings/pipeline_service.py, memory/dependencies.py, memory/service.py
- `create_async_engine` (3 파일): common/database.py, tests/conftest.py, tests/integration/test_alembic_upgrade.py
- alembic/env.py 의 `async_engine_from_config` (1 파일, autogenerate 표준)

모두 SQLModel 미 re-export → SA 영구 유지 ✅

### 검증 결과

- backend pytest tests/ → **321 passed + 1 skipped** (baseline 317 + 4 신규 smoke: 1 E1 + 3 E4)
- backend pytest tests/integration/test_alembic_upgrade.py → 1 PASS (drift 0 유지)
- pyright: **132 errors (origin/main) → 131 errors (본 PR, -1 개선)**
- grep `from sqlalchemy.ext.asyncio import AsyncSession`: **29 → 0** (100% 제거, alembic env.py 제외)

### Codex evaluator review

- 1차 plan review (verdict REVISE): 5 finding (MAJOR 2 + MINOR 3) 모두 수락 → plan v2 patch
  - MAJOR-1: 헌법 I-14 + B-10 충돌 (BL-054 F6 closeout 으로 carry-over)
  - MAJOR-2: BL-054 execute allowlist 불완전 (manifest G1~G5 — BL-054 F1 진입 전)
  - MINOR-3/4/5: E1 import 양분 + E6 fixture smoke + E7 grep gate (모두 적용)
- 2차 diff review (verdict **APPROVE**, 4.6/5 평균): 2 MINOR 모두 수락 → E7.9a fix
  - 1_pure_refactor=5, 2_sm_subclass_compat=5, 3_cat_b_allowlist=5, 4_smoke_test_coverage=4, 5_silent_failure_modes=4

### BL-054 carry-over (PR #93)

- 모든 repository 의 `session.execute(stmt).scalars().all()` / `.scalar_one_or_none()` / `.scalar_one()` 패턴을 SQLModel typed `session.exec(stmt).all()` / `.one_or_none()` / `.one()` 으로 migration
- 헌법 patch 동반 (CONTEXT-MAP I-14 + apps/api/CONTEXT.md B-10 + `apps/api/AGENTS.md`)
- execute allowlist manifest (G1~G5) 작성 후 진행

**근거**: Sprint 19 PR #2 D9 + BL-052 cleanup PR (#91) Plan agent verdict + Codex 1차/2차 review.

---

## BL-054 — session.execute(stmt).scalars().all() → session.exec(stmt).all() migration ✅ **완료 (Sprint 20 cleanup PR #93, 2026-05-18)**

Sprint 20 cleanup PR #93 (branch `cleanup/bl-054-session-exec`, PR #92 위 stack PR, 7 commits).

### 본 PR 완료 결과 (7 commits, 11 파일)

```
F6/F5.9a (closeout) docs(bl-054): F6 closeout — execute manifest 갱신 + 헌법 patch + Codex 2차 review 3 finding 수락
F3 d211d34 refactor(bl-054): F3 auth + inbox + notes — execute → exec (9 변환, 3 파일)
F2 56474ef refactor(bl-054): F2 actions + meetings + embeddings — execute → exec (14 변환, 3 파일)
F1 c30d6dc refactor(bl-054): F1 workspaces + projects + memory — execute → exec (34 호출, 4 파일)
F0 c23c9dc docs(bl-054): F0 execute manifest 신설 (G1~G5 카테고리)
```

### Scope (57 변환 + manifest + 헌법 patch)

| 영역 | 변환 호출 | commit |
|---|---|---|
| F1 workspaces (14) + projects (8) + memory_repo (9) + memory_svc (3) | 34 | F1 |
| F2 actions (4) + meetings (5) + embeddings (5) | 14 | F2 |
| F3 auth (3) + inbox (3) + notes (3) | 9 | F3 |
| **총 G1+G3-convert 변환** | **57** | F1~F3 |

### 유지 (manifest 정합, src/ 잔여 19 호출)

- **G3-keep** (1): actions/repository.py:75 cancel_todo_by_project — `.rowcount` 사용
- **G3-keep-dialect** (1): memory/repository.py:304 — `pg_insert(...).on_conflict_do_nothing()` (SA dialect insert)
- **G4 raw text** (17): main.py healthcheck (1) + auth/dependencies.py seed (2) + embeddings/repository.py 8 + memory/repository.py 4 + embeddings 320 cache UPDATE

### 헌법 patch (Codex 1차 MAJOR-1 수락)

- `CONTEXT-MAP.md` I-14: `session.exec() 금지` → manifest 기반 allowlist 명시
- `apps/api/CONTEXT.md` B-10: 동일 정정 + N+1 방지 selectinload 동일

### 검증

- pytest tests/ → **321 passed + 1 skipped** (BL-053 후와 동일, 회귀 0)
- pyright → **132 errors** (BL-053 후 131, +1 미세)
- manifest 정합 검증 통과: G1 변환 누락 0, 잔여 19 = G3-keep 1 + G3-keep-dialect 1 + G4 17

### Codex evaluator review

- 1차 plan review (verdict REVISE): MAJOR-1 (헌법 충돌) + MAJOR-2 (manifest 불완전) 수락 → F0 manifest 신설 + F6 헌법 patch
- 2차 diff review (verdict REVISE → F5.9a fix 수락):
  - MAJOR-1 manifest stale → manifest 갱신 (G2 stale 제거 + G4 17 정확 명시 + F5 gate 정확화)
  - MAJOR-2 pg_insert unclassified → G3-keep-dialect 카테고리 신설 + memory/repository.py:304 docstring 추가
  - MINOR-3 rowcount rationale → actions/repository.py:75 docstring 정정 + manifest G3-keep rationale 명확화
  - 2차 scores: 1=2 / 2=5 / 3=4 / 4=5 / 5=3

**근거**: Sprint 19 PR #2 D9 + BL-052 cleanup PR Plan agent verdict + Codex 1차/2차 review.

---

## ~~BL-T2-003~~ — Whisper chunk 분할 (4hr+) ✅ **완료 (Sprint 24 Wave 2 T-N+4, 2026-05-20)**

**현 상태**: **[해소 2026-05-20] Sprint 24 Wave 2 T-N+4**. 4시간+ recording production 처리 차단 해소.

**원본 발견**: Sprint 24 Multi-Agent QA Day 1 Sentinel Tier 2 (`git history`).

**문제**:
- `transcription.py:TranscriptionService.transcribe()` 가 Whisper API 단일 호출.
- 60MB+ audio (Whisper 25MB 제한 초과) 업로드 시 API 400 — 4hr+ recording 처리 불가.

**해소 결과 (PR: Sprint 24 Wave 2 Phase 8)**:
- `services/chunked_transcription.py` 신설 — `_ffmpeg_probe_duration` + `_ffmpeg_split` + `_whisper_transcribe_single` + `_merge_with_offset` + `transcribe_chunked` (5 모듈 함수).
- `services/transcription.py` 에 `TranscriptionService.transcribe_with_chunking(audio_bytes, filename)` entry 추가 — 1hr 이하 단일 호출, 1hr 초과 chunked 경로 분기.
- `meetings/pipeline_service.py:process_meeting` 호출처 교체 (`transcribe` → `transcribe_with_chunking`).
- `tests/services/test_whisper_chunked_4hr.py` — 3 신규 test (short single / 4hr 4 chunk offset / overlap dedupe). mock 기반 (ffmpeg/Whisper 실제 호출 회피).

**Atomic Update**: `apps/api/CONTEXT.md` §10 STT 파이프라인 + `docs/architecture/ai-pipeline.md` §"STT (Speech-to-Text)" + 본 BL closed mark.

**제약·후속**:
- 4hr 라이브 audio 실측은 별도 dogfood 과제 (테스트는 mock 검증). 사용자 audio sample 확보 시점에 production 1회 verify 권장.
- 더 정교한 dedup (text 유사도 / 시간 fuzzy match) 필요 시 후속 BL 발의 — 현재는 exact text match within overlap window.

---

