<!-- Sprint 24 Wave 2 trusty-heron — Multi-Agent QA P0/P1 fix bundle design doc (5 sections + Success Criteria) -->

# Sprint 24 Wave 2 — `trusty-heron` Design Doc

> Multi-Agent QA P0/P1 dogfood-blocking 결함 16 task fix bundle + Phase B Post-Swap Delta 측정 + 헌법 §4.2 정합.
>
> 입력: kickoff prompt `docs/sprint-24-wave2-kickoff-prompt.md` + `~/.claude/plans/docs-sprint-24-wave2-kickoff-prompt-md-cuddly-lecun.md` (approved) + `docs/dev-log/2026-05-19-sprint24-qa-multi-agent/{sprint-24-plan,evidence-matrix,post-swap-delta-stub}.md`
> 산출 PR: `sprint-24/wave2-trusty-heron` (Phase 별 1 commit, ~9-10 commit + Codex polish)
> 데드라인: 2026-05-28 (Phase B 측정 검증)

---

## 0. Context

| 항목 | 값 |
|---|---|
| main HEAD | `f46a075` (PR #100 Sprint 24 entry) |
| pytest baseline | 387 passed + 1 skipped |
| FE typecheck | 0 errors / vitest 50 |
| alembic head | `9dd1a3b80431` (Wave 2 변경 없음 — audit endpoint read-only + Whisper chunk 도 schema 변경 X + composite FK fixture 도 변경 X) |
| Pre-Sprint Closure | Phase B Gemini swap (`003908a`) + Wave 1 BL-063/064/066 (`b1c777b`) 모두 main 적용 |

**의도된 outcome**: 5 페르소나 dogfood 회귀 0 + 헌법 §4.2 정합 + Phase B 품질 검증 PASS + 데드라인 2026-05-28 충족.

---

## 1. Architecture

### Phase 의존 (9 Phase + carry)

```
Phase 1 T-2 Delta 측정 (P0 first, gate)
   ↓ OK → Phase 2 진입 / fail → STOP + revert PR 옵션
Phase 2 P0 Critical (T-AI-DATE + T-RAG-MOCK-REMOVE)
Phase 3 P0 High UX (T-OBN-05 + T-MOBILE-HEADER)
Phase 4 P1 FE missing pages (T-PROJ-LIST + T-NOTE-DETAIL + T-CMD-K-FIX)
Phase 5 P1 RAG + compliance (T-RAG-TIME-FILTER + T-AUDIT-VIEW)
Phase 6 P1 Performance (T-BE-PERF spike + Top 1 fix)
Phase 7 헌법 (T-N+1 BL-006 cross-domain import 해소)
Phase 8 Production (T-N+4 BL-T2-003 Whisper 4hr+ chunk)
Phase 9 회귀 안전망 (T-N+2 composite FK fixture)
```

각 Phase 1 commit + 의미 단위 polish commit (Codex finding 100% 수락). 총 9-10 base commit + Codex polish 4-8개 예상.

### Code 경계 매트릭스

| 도메인 | 본 sprint 변경 |
|---|---|
| `backend/src/common/prompts.py` | T-AI-DATE 현재 연도 context |
| `backend/src/services/ai_processing.py` | T-AI-DATE deadline_date assertion |
| `backend/src/embeddings/repository.py` | T-RAG-TIME-FILTER search() time_range SQL clause |
| `backend/src/common/promote_helpers.py` 또는 신규 router | T-AUDIT-VIEW read endpoint |
| **`backend/src/memory/pipeline_service.py` 신설** | T-N+1 BL-006 orchestrator (capture/distill/promote + embeddings.save_chunk 위임) |
| `backend/src/memory/service.py` (lazy import 제거) | T-N+1 service 순수화 |
| `backend/src/memory/repository.py:33` | T-N+1 `_apply_hnsw_session_params` import (캡슐화 우회 유지 또는 E-9 helper 분리) |
| `backend/src/services/transcription.py` (또는 신규 chunked variant) | T-N+4 Whisper 4hr+ chunk + ffmpeg duration |
| `backend/tests/fixtures/composite_fk.py` (신설) | T-N+2 SCN-FK-01~12 fixture |
| `frontend/src/features/rag/components/search-scope.tsx:31-37` | T-RAG-MOCK-REMOVE empty state + UI 비활성화 |
| **Frontend rollback**: `today-feed.tsx` (banner function + mount 제거) + `components/empty-state.tsx` (Sprint 22 OBN-03 props 제거 + plain copy 통일) + `project-list/detail.tsx` + `meeting-summary.tsx` (`useOnboarding` 호출처 정리) + `frontend/e2e/tests/{home,first-project,mobile-responsive}.spec.ts` (banner assertion 제거). **Frontend 신설**: `frontend/src/components/onboarding/onboarding-tooltip.tsx` + `frontend/e2e/tests/onboarding-tooltip-first-visit.spec.ts` + shadcn `tooltip`/`popover` 의존성. **유지**: `useOnboarding` hook + BE 도메인 + `User.onboarding_step` + template seed + `meeting-detail-header.tsx` Export discoverability + `meeting-export.spec.ts` | T-OBN-05 **D 옵션**: banner 폐기 + Linear-style tooltip (Codex+Gemini deep research 합의 + Codex cross-check 정밀화). 시간 3.5-4.5h |
| `frontend/src/components/layout/header.tsx` | T-MOBILE-HEADER padding reflow |
| `frontend/src/app/(app)/projects/page.tsx` (신설) | T-PROJ-LIST 카드 그리드 |
| `frontend/src/app/(app)/notes/[id]/page.tsx` (신설) | T-NOTE-DETAIL Tiptap viewer + edit-in-place |
| dashboard 추천 질문 component | T-CMD-K-FIX onClick → cmd-k store + setQuery |
| `frontend/src/app/(app)/settings/page.tsx` | T-AUDIT-VIEW Audit 탭 (admin only) |

### Atomic Update §2 매트릭스

| 코드 변경 | 동시 갱신 docs |
|---|---|
| T-OBN-05 D 옵션 (banner 폐기 + tooltip) | (1) `backend/src/onboarding/CONTEXT.md` — UI 결정 변경 anchor (BE step lifecycle 책임은 그대로). (2) Sprint 22 산출물 doc deprecated 라벨 — `docs/dev-log/2026-05-19-sprint22-result-report.html` + `docs/dev-log/2026-05-19-sprint22-dogfooding.md` + `docs/superpowers/specs/2026-05-19-sprint22-onboarding-e2e-obs.md` + `docs/superpowers/plans/2026-05-19-sprint22-tasks.md` (4 문서 모두 D 옵션 결정 anchor link). (3) `docs/REFACTORING-BACKLOG.md` BL-NEW-OBN-DATA-RETRY 등재. (4) Atomic Update — banner 컴포넌트 제거 시 `frontend/CONTEXT.md` (있다면 onboarding-aware empty-state 섹션 제거) |
| T-AI-DATE | `backend/CONTEXT.md` AI § + `docs/architecture/ai-pipeline.md` |
| T-RAG-TIME-FILTER | `backend/src/embeddings/CONTEXT.md` + `docs/architecture/rag-pipeline.md` Layer 3 |
| T-AUDIT-VIEW endpoint | `backend/src/<도메인>/CONTEXT.md` §엔드포인트 + `docs/api/endpoints.md` |
| **T-N+1 BL-006** | **`CONTEXT-MAP.md` §4.2 + §7 부채 + `backend/CONTEXT.md` §4 + `backend/src/memory/CONTEXT.md` + `backend/src/embeddings/CONTEXT.md` (E-9 갱신) + `docs/architecture/cross-domain-pipeline.md`** |
| T-N+4 Whisper chunk | `backend/CONTEXT.md` STT § + `docs/architecture/ai-pipeline.md` STT 단계 |
| T-N+2 fixture | BL-024 cross-link + `backend/tests/fixtures/composite_fk.py` doc |

PR 본문 "Docs sync" 섹션 필수 — `git diff --stat docs/ backend/**/CONTEXT.md frontend/**/CONTEXT.md CONTEXT-MAP.md` 결과 첨부.

---

## 2. Components

### Phase 1 — T-2 Post-Swap Delta (2h, P0 first)

**산출물**: `docs/dev-log/2026-05-20-sprint24-wave2/post-swap-delta-report.md` + 비교 fixture.

**측정 방법**:
1. baseline (`003908a^` 직전 commit, `gemini-2.5-flash`) 결과 캡쳐 시도. **현실적으로 baseline 미캡쳐 (`f46a075`까지 모두 swap 이후)** → **alternative**: prompt cache + 직접 호출 baseline 생성. 또는 git checkout `003908a^` → temp branch 에서 동일 fixture 호출 → 측정.
2. 5 시나리오 fixture (text 3 sample × 5 query × 2 모델). fixture audio 불필요 — text prompt 만.
3. post-swap (main) 동일 fixture 호출 → JSON 캡쳐.
4. delta 자동 비교 스크립트 (`backend/scripts/sprint24_wave2_delta.py` 신설) — length / cosine / 정성 평가 표 작성.

**Gate**:
- DELTA-1 (RAG) 정성 "worse" 0건
- DELTA-3 (액션 추출) precision/recall -10% 이내
- DELTA-2/4/5 ±20% 이내

Fail 시 **STOP + 사용자 보고 + revert PR 옵션 검토** (Phase 2 진입 전).

### Phase 2 — P0 Critical (2.5h)

**T-AI-DATE** (1.5h):
- `backend/src/common/prompts.py:ACTION_EXTRACTION_PROMPT` — 헤더에 `현재 연도={current_year}` + Few-shot 예시 ("7월 25일" → "{current_year}-07-25 또는 {current_year+1}-07-25 if past")
- `backend/src/services/ai_processing.py:extract_action_items` — 후처리:
  ```python
  for action in actions:
      if action.due_date is None:
          continue
      if action.due_date.year < current_year:
          logger.warning("AI hallucinate past year date, dropping", extra={"meeting_id": meeting_id, "due_date": action.due_date})
          action.due_date = None
  ```
- 신규 테스트: `backend/tests/services/test_ai_action_date_with_year_context.py` (연도 미명시 input + current_year context → 정확 연도 추출 + assertion drop case)

**T-RAG-MOCK-REMOVE** (1h):
- `frontend/src/features/rag/components/search-scope.tsx:31-37` — `MOCK_SELECTABLE_SOURCES` 제거 + selection UI `disabled` + empty state copy ("소스 선택 기능 준비 중 — 현재는 전체 워크스페이스에서 검색합니다")
- 신규 BL 등재: `BL-NEW-RAG-SOURCE-SELECT` (Sprint 25+ B path 검토)
- 검증: Playwright snapshot regression (`frontend/e2e/tests/rag-search-scope.spec.ts`)

### Phase 3 — P0 High UX (3h)

**T-OBN-05** (2-3h, **D 옵션 — Codex+Gemini deep research 합의**):

**배경**: Sprint 22 OBN-02~04 의 OnboardingBanner FE 발화 미작동 (BUG-CURIOUS-003). Codex/Gemini 외부 의견 + Multi-Agent QA 데이터 (TTFV 255초 = banner 없이도 가치 도달) + 글로벌 데이터 (checklist 완료율 19.2% / 효과 인식 12%) + PERSONA-001 (1인 풀스택 founder = power user) 정합 분석 결과 = **banner 폐기 + Linear-style inline tooltip 전환**.

**Sprint 22 OBN 실제 산출물 매트릭스** (grep verify):

| 산출물 | 실제 위치 | 처리 |
|---|---|---|
| OnboardingBanner function 정의 | `frontend/src/features/home/components/today-feed.tsx:30-67` | **삭제** (function 자체 + 관련 markup) |
| OnboardingBanner mount | `frontend/src/features/home/components/today-feed.tsx:368 (<OnboardingBanner />)` | **삭제** (JSX 호출 제거) |
| `useOnboarding` import (today-feed) | `today-feed.tsx:20` | **삭제** (banner 제거 후 unused) |
| **EmptyState 컴포넌트 자체** | `frontend/src/components/empty-state.tsx` (Sprint 22 OBN-03 `onboardingStep` + `context` prop 추가) | **정리** (`onboardingStep` + `context` props 제거 + onboarding-aware hint 분기 삭제 + plain copy 통일). Codex cross-check 누락 발견 |
| EmptyState 호출처 onboarding-aware 분기 | `project-list.tsx:7,12` + `project-detail.tsx:26,86` + `meeting-summary.tsx:5,12` | **정리** (`useOnboarding` 의존 제거 + `onboardingStep` / `context` prop 전달 제거) |
| **E2E banner assertion** | `frontend/e2e/tests/home.spec.ts` (G1 `Step 1/4`) + `first-project.spec.ts` (G2 `Step 2/4` NEW) + `mobile-responsive.spec.ts` (OBN-04 banner case) | **정리** (banner assertion 제거 또는 tooltip assertion 으로 교체). Codex cross-check 누락 발견 |
| **Sprint 22 결과/dogfooding/spec/plan 문서** | `docs/dev-log/2026-05-19-sprint22-result-report.html` + `docs/dev-log/2026-05-19-sprint22-dogfooding.md` + `docs/superpowers/specs/2026-05-19-sprint22-onboarding-e2e-obs.md` + `docs/superpowers/plans/2026-05-19-sprint22-tasks.md` | **deprecated 라벨 + Sprint 24 Wave 2 D 옵션 결정 anchor** (D 옵션 spec 으로 link). Codex cross-check 누락 발견 |
| `useOnboarding` hook | `frontend/src/features/onboarding/hooks.ts` | **유지** (lifecycle/funnel 미래 가치 — Codex 확인) |
| onboarding API client | `frontend/src/features/onboarding/api.ts` | **유지** |
| BE onboarding 도메인 | `backend/src/onboarding/{service,router,repository,dependencies,schemas}.py` + `CONTEXT.md` | **유지** (Sprint 22 OBN-02 BE 자산, step lifecycle 책임 — 헌법 모순 없음 Codex 확인) |
| User.onboarding_step + alembic + event hook | BE 전반 | **유지** (자산) |
| template seed (3 프로젝트) | `backend/src/workspaces/service.py` (Sprint 15) | **유지** (empty dashboard 안티패턴 회피) |
| **Export discoverability** (OBN 무관) | `frontend/src/features/meetings/components/meeting-detail-header.tsx` Export button + `meeting-export.spec.ts` (G8) | **유지** (Codex 확인 — OBN 폐기 대상 아님, BUG-C04 별개 가치) |

**신규 tooltip (A 패턴, 첫 방문 페이지 inline) — Codex cross-check 후 축소**:

shadcn `Tooltip` + `Popover` 의존성 확인 필요 (현재 미설치 시 `pnpm dlx shadcn add tooltip popover` 도입).

- `frontend/src/components/onboarding/onboarding-tooltip.tsx` 신설 — shadcn `Tooltip` + `Popover` 재사용
- **2 + 2 조건부 tooltip** (Codex 권장 — power user 친화):
  - **무조건**: `/dashboard` 첫 방문 — "AI 검색은 ⌘K — 워크스페이스 회의/노트 전체 검색"
  - **무조건**: `/search` (또는 ⌘K 첫 열기) — "검색 범위는 현재 워크스페이스 전체입니다"
  - **조건부** (User.onboarding_step < 2 + empty state): `/projects` — "+ 새 프로젝트로 시작하세요"
  - **조건부** (User.onboarding_step < 3 + empty 상태): `/new` — "회의 음성을 업로드하면 AI 가 자동 요약합니다"
- localStorage `kairos.onboarding.tooltip_shown.{page}` 로 재방문 시 발화 X
- dismiss button (X) 명시 + Esc key dismiss
- minimal analytics event: `tooltip_shown` / `tooltip_dismissed` (page name property)

**시간 분해 (Codex cross-check 후 정확화)**:
- banner rollback (today-feed.tsx) 0.5h
- EmptyState 컴포넌트 자체 + 3 호출처 정리 (empty-state.tsx + project-list/detail + meeting-summary) 0.5-1h
- E2E test 3 파일 banner assertion 정리 + Sprint 22 docs deprecated 라벨 0.5h
- shadcn Tooltip/Popover 의존성 추가 + tooltip 컴포넌트 구현 (2 + 2 조건부) 1.5-2h
- analytics event + localStorage 0.5h
- 신규 E2E (`onboarding-tooltip-first-visit.spec.ts`) 0.5h
= **3.5-4.5h** (A 옵션 2h 와 비교 시 +1.5-2.5h. Codex 권장 정합)

**본 sprint scope 영향**: 24.5h → 26-27h (T-BE-PERF 포함 시 ~30-33h, 8일 예산 32-64h 내 여유).

**신규 E2E + 기존 E2E 정리**:
- 신규: `frontend/e2e/tests/onboarding-tooltip-first-visit.spec.ts` — storageState clear → /dashboard + /search tooltip 발화 + /projects + /new 조건부 tooltip + dismiss + 재방문 시 tooltip X 검증
- 정리: `home.spec.ts` (G1 `Step 1/4` assertion 제거 또는 tooltip 으로 대체) + `first-project.spec.ts` (G2 `Step 2/4` assertion 제거) + `mobile-responsive.spec.ts` (OBN-04 banner case 제거)
- 회귀 가드: `onboarding-banner` data-testid 더 이상 mount 안 됨 (dashboard snapshot)

**BL 신규 등재** — `BL-NEW-OBN-DATA-RETRY` (Sprint 25+, F4 페르소나 인터뷰 확정 후 onboarding 재설계 검토 — 데이터 기반).

**T-MOBILE-HEADER** (0.5-1h):
- `frontend/src/components/layout/header.tsx` 또는 `(app)/layout.tsx` — header padding `lg:pl-X md:pl-0` 등 reflow. ancestor `main.flex-1 overflow-hidden` 유지.
- 3 viewport (375/393/412) screenshot regression (Playwright)
- 신규 테스트: `frontend/e2e/tests/mobile-header-overflow.spec.ts`

### Phase 4 — P1 FE missing pages (6h)

**T-PROJ-LIST** (2h):
- `frontend/src/app/(app)/projects/page.tsx` 신설 — `useProjects` 훅 + shadcn Card grid + status badge + last_activity timestamp + create button (`+ 새 프로젝트`)
- sidebar dead-end (BUG-CASUAL-001) 해소
- 신규 E2E: `frontend/e2e/tests/projects-list.spec.ts`

**T-NOTE-DETAIL** (3h):
- `frontend/src/app/(app)/notes/[id]/page.tsx` 신설 — `useNote(id)` + Tiptap `EditorContent` (readonly toggle) + `NoteExportButton` (md/json) + `ItemPromoteModal` trigger
- Tiptap edit-in-place: pencil icon → editable mode → save (auto-save debounce 1s)
- 신규 E2E: `frontend/e2e/tests/note-detail.spec.ts` (sidebar click → /notes/[id] 도달 + ExportButton 클릭 가능)

**T-CMD-K-FIX** (1h):
- dashboard 추천 질문 button 4건 — onClick → `useCmdK()` store `openWithQuery(query)` 호출
- 신규 vitest unit: `frontend/src/features/home/components/__tests__/dashboard-suggestions.test.tsx`

### Phase 5 — P1 RAG + compliance (6h)

**T-RAG-TIME-FILTER** (2h):
- `backend/src/embeddings/repository.py:search` — `time_range: Literal["1w", "1m", "3m", "all"] | None = None` param + WHERE clause:
  ```sql
  AND chunk.created_at >= now() - interval :time_window
  ```
- mapping: 1w → '7 days' / 1m → '30 days' / 3m → '90 days' / all → no filter
- 신규 테스트: `backend/tests/embeddings/test_rag_time_range_sql_clause.py`

**T-AUDIT-VIEW** (4h, sub-agent 2분할 BE+FE):
- BE 신규 endpoint: `GET /api/v1/workspaces/{wid}/audit/promotions?item_type=<meeting|note|inbox|action>&limit=20&cursor=<id>` — admin only (`require_member` + role check)
- FE Settings 4번째 tab `Audit` — `useAuditPromotions(item_type, limit, cursor)` infinite scroll + 도메인 filter dropdown
- 신규 테스트: pytest read endpoint + Playwright admin gate

### Phase 6 — P1 Performance (4-6h)

**T-BE-PERF spike** (sub-agent 1, Spike + Top 1 fix):
- localhost BE API workspaces/members/meetings/inbox 첫 진입 3015-3865ms 진단
- 의심: Clerk JWT verify 직렬 + DB warm-up
- profiling: cProfile + py-spy 또는 print timing. SQLAlchemy event listener `before_cursor_execute` + `after_cursor_execute` 로 query timing
- 산출물: `docs/dev-log/2026-05-NN-be-perf-spike.md` (5-section report) + Top 1 fix commit
- 후속 fix carry-over BL 등재

### Phase 7 — 헌법 (3h)

**T-N+1 BL-006** (3h):
- `backend/src/memory/pipeline_service.py` 신설 (`MemoryPipelineService`). capture / distill / promote orchestrator. `EmbeddingRepository.save_chunk` 위임:
  ```python
  class MemoryPipelineService:
      def __init__(self, session, ...):
          self.session = session
          self.memory_repo = MemoryRepository(session)
          self.embedding_repo = EmbeddingRepository(session)
      
      async def capture_with_embedding(self, ...):
          memory = await self.memory_repo.create(...)
          chunk = await self.embedding_repo.save_chunk(workspace_id, source_type='memory', source_id=memory.id, ...)
          return memory, chunk
  ```
- `backend/src/memory/service.py:550, 780` lazy import 제거 → service 는 pipeline 미주입 시 RuntimeError
- `backend/src/memory/repository.py:33` `_apply_hnsw_session_params` import — **E-9 외부 사용처 유지** (helper 분리 X, 캡슐화 우회의 최소 비용 약속 유지). pipeline_service 도입은 service-level 분리, repository-level 직접 sql (`vector_search`) 은 E-9 패턴 유지.
- `CONTEXT-MAP.md` §4.2 의존 다이어그램 갱신 (memory → embeddings 점선 표시 유지 + pipeline_service 경유 명시) + §7 BL-006 closed mark
- 신규 테스트: import-linter 또는 ruff custom rule `tests/test_no_cross_domain_lazy_import.py` (ruff custom rule 어려우면 pytest custom)

### Phase 8 — Production (4h)

**T-N+4 BL-T2-003** (4h):
- `backend/src/services/transcription.py` 또는 신규 `chunked_transcription.py`:
  ```python
  async def transcribe_chunked(audio_url: str, ...) -> list[Segment]:
      duration = await ffmpeg_probe_duration(audio_url)
      if duration <= 3600:  # 1hr
          return await transcribe_full(audio_url)
      chunks = await split_audio_chunks(audio_url, chunk_seconds=3600, overlap_seconds=5)
      segments = await asyncio.gather(*[transcribe_full(c) for c in chunks])
      return merge_with_offset(segments, chunk_seconds=3600, overlap_seconds=5)
  ```
- ffmpeg subprocess + asyncio.gather 병렬
- offset 보존 (chunk index × 3600 + segment.start)
- 신규 테스트: pytest mock 4hr+ audio + chunk count 4 + offset 검증

### Phase 9 — 회귀 안전망 (2h)

**T-N+2 composite FK fixture** (2h):
- `backend/tests/fixtures/composite_fk.py` 신설 — 12 SCN entity 별 helper:
  ```python
  @pytest_asyncio.fixture
  async def composite_fk_meeting_project_link_violation(session, two_workspaces):
      """SCN-FK-01: MeetingProjectLink (insert) cross-workspace 거부"""
      meeting = await create_meeting(session, workspace_id=two_workspaces[0])
      project = await create_project(session, workspace_id=two_workspaces[1])
      with pytest.raises(IntegrityError):
          await create_meeting_project_link(session, meeting_id=meeting.id, project_id=project.id, workspace_id=two_workspaces[0])
  ```
- `backend/tests/conftest.py` `from backend.tests.fixtures.composite_fk import *` 또는 pytest plugin pattern
- CI 통합: 기존 `pytest tests/` 에 자동 포함 (별도 marker 불필요)

---

## 3. Data Flow

### T-AI-DATE prompt → action 추출

```
Meeting transcript (한국어, 일자 명시 또는 미명시)
   ↓ MeetingService.process_meeting (헌법 I-2 orchestrator)
   ↓ ai_processing.extract_action_items(transcript, current_year=2026)
   ↓ prompts.ACTION_EXTRACTION_PROMPT.format(current_year=2026, transcript=...)
   ↓ Gemini gemini-3.1-flash-lite 호출 → ActionItem JSON list
   ↓ 후처리 검증 loop:
       if action.due_date.year < 2026 → drop (warn log)
       else → keep
   ↓ ActionItem repository save (workspace_id matched)
```

### T-RAG-TIME-FILTER search → SQL clause

```
FE search-scope.tsx → time_range select (1w/1m/3m/all)
   ↓ POST /rag/ask body.time_range
   ↓ RagPipelineService.ask(query, ..., time_range='1w')
   ↓ EmbeddingRepository.search(query_embedding, workspace_id, project_ids, time_range='1w')
   ↓ SQL:
     SELECT * FROM embedding_chunks
     WHERE workspace_id = :wid
       AND project_id = ANY(:pids)
       AND chunk_level = 2
       AND created_at >= now() - interval '7 days'  -- NEW
     ORDER BY embedding <=> :query_embedding
     LIMIT 20
   ↓ Re-ranking + Generation
```

### T-AUDIT-VIEW endpoint → Settings UI

```
admin user → Settings → Audit tab → useAuditPromotions(item_type='meeting', limit=20)
   ↓ GET /api/v1/workspaces/{wid}/audit/promotions?item_type=meeting&limit=20
   ↓ admin role check (require_member + role in {owner, admin})
   ↓ ItemPromotionAuditRepository.find_by_workspace(wid, item_type='meeting', limit=20, cursor=None)
   ↓ JSON list (audit_id, source_workspace_id, target_workspace_id, source_item_id, new_item_id, promoted_by, created_at, embedding_status)
   ↓ FE infinite scroll + 도메인 filter dropdown
```

### T-N+1 BL-006 memory capture flow (BEFORE → AFTER)

```
BEFORE (헌법 §4.2 위반):
MemoryService.capture_text(...)
   ↓ memory_repo.create(...)
   ↓ from src.embeddings.repository import EmbeddingRepository  # lazy import (SCN-BL-006-02)
   ↓ EmbeddingRepository(session).save_chunk(...)
   ↓ commit

AFTER (orchestrator 위임):
MemoryPipelineService.capture_text_with_embedding(...)
   ↓ memory_repo.create(...)
   ↓ embedding_repo.save_chunk(...)  # __init__ 에서 주입된 repo
   ↓ commit
```

---

## 4. Error Handling

### Phase 1 DELTA Gate Fail (T-2)

- **Trigger**: DELTA-1 worse 1건+ / DELTA-3 -10% 초과 / DELTA-2/4/5 ±20% 초과
- **즉시 STOP** → 사용자 보고 + 다음 옵션 검토:
  - Option 1: Phase B revert PR (`003908a` 되돌리기 + `gemini-2.5-flash` 복원)
  - Option 2: prompt tuning (Few-shot 보강) 후 재swap
  - Option 3: hybrid 분기 (distill 만 3.1-flash-lite, action 추출은 2.5-flash 유지)

### Sub-agent stall (Phase 5 T-AUDIT-VIEW + Phase 6 T-BE-PERF)

- sub-agent ~1.5h limit (R2 mitigation)
- stall 시 controller 가 git log progress verify → 진척 0 면 dispatch 재시작 또는 분할 축소
- §19 룰 강제: sub-agent 는 코드 수정만 (산출물 디렉토리 또는 source 파일), commit 은 controller 만

### T-AI-DATE 후처리 drop edge case

- `due_date.year < current_year` 만 drop → 만약 `due_date.year > current_year + 5` 면 keep (사용자가 의도적 long-term 일정일 수 있음)
- log warn with `meeting_id` + `due_date` for 후속 분석
- 신규 테스트 case: 2025년 (과거) drop / 2026년 (현재) keep / 2031년 (5년+) keep / null keep

### T-N+1 import-linter fail-closed

- ruff custom rule 작성이 어려우면 pytest test `test_no_memory_to_embeddings_lazy_import.py` 로 fail-closed:
  ```python
  def test_memory_service_no_lazy_embeddings_import():
      source = Path("backend/src/memory/service.py").read_text()
      assert "from src.embeddings" not in source, "BL-006 위반 — pipeline_service 위임 필요"
  ```

### T-N+4 Whisper chunk merge edge case

- chunk N 의 마지막 5초 overlap 과 chunk N+1 의 처음 5초 중복 segment 처리
- merge 알고리즘: chunk N 의 segment.end 가 5초 overlap 영역에 있으면 chunk N+1 의 동일 시간 segment 와 deduplicate (text 유사도 기준)

---

## 5. Testing

### per-task 신규 테스트 (Phase 별)

| Task | 신규 테스트 파일 | 종류 |
|---|---|---|
| T-2 | `docs/dev-log/2026-05-20-sprint24-wave2/post-swap-delta-report.md` | 측정 report |
| T-AI-DATE | `backend/tests/services/test_ai_action_date_with_year_context.py` | pytest unit (4 case) |
| T-RAG-MOCK-REMOVE | `frontend/e2e/tests/rag-search-scope.spec.ts` | Playwright snapshot |
| T-OBN-05 | `frontend/e2e/tests/onboarding-tooltip-first-visit.spec.ts` + banner rollback regression | Playwright E2E (D 옵션) |
| T-MOBILE-HEADER | `frontend/e2e/tests/mobile-header-overflow.spec.ts` | Playwright 3 viewport |
| T-PROJ-LIST | `frontend/e2e/tests/projects-list.spec.ts` | Playwright E2E |
| T-NOTE-DETAIL | `frontend/e2e/tests/note-detail.spec.ts` | Playwright E2E |
| T-CMD-K-FIX | `frontend/src/features/home/components/__tests__/dashboard-suggestions.test.tsx` | vitest unit |
| T-RAG-TIME-FILTER | `backend/tests/embeddings/test_rag_time_range_sql_clause.py` | pytest integration |
| T-AUDIT-VIEW | `backend/tests/common/test_audit_promotions_endpoint.py` + `frontend/e2e/tests/settings-audit.spec.ts` | pytest + Playwright admin gate |
| T-BE-PERF | `docs/dev-log/2026-05-NN-be-perf-spike.md` | profiling report |
| T-N+1 BL-006 | `backend/tests/architecture/test_no_memory_to_embeddings_lazy_import.py` | pytest custom rule |
| T-N+4 BL-T2-003 | `backend/tests/services/test_whisper_chunked_4hr.py` | pytest mock |
| T-N+2 | `backend/tests/fixtures/composite_fk.py` (12 SCN helper) + 기존 통합 test 에서 import | fixture module |

**총 신규 테스트**: ~14 파일, ~30+ case (pytest 387 → 410+ expected).

### 회귀 가드

| 가드 | 명령 | Expected |
|---|---|---|
| pytest baseline | `cd backend && uv run pytest tests/ -q` | 387 → 410+ + 1 skipped |
| FE typecheck | `cd frontend && pnpm typecheck` | 0 errors |
| FE vitest | `cd frontend && pnpm test` | 50 → 55+ PASS |
| alembic drift | `pytest tests/integration/test_alembic_upgrade.py` | drift 0 (Wave 2 schema 변경 없음) |
| Playwright e2e (기존 15) | `cd frontend && pnpm e2e` | 모두 PASS + 신규 7 spec 추가 |

### Dogfooding mini-redo (Wave 2 closeout 직전)

- Curious 페르소나 mini-redo (storageState clear or incognito 새 Clerk 계정)
- 시나리오: 신규 가입 → onboarding step 1~4 발화 확인 → 첫 프로젝트 → 회의 업로드 → AI 요약 → RAG /ask
- 검증 대상:
  - BUG-CURIOUS-001 (AI 날짜 hallucinate) — 회의 본문 "7월 X일" 미명시 → 액션 마감일 = 2026년 또는 null
  - BUG-CURIOUS-002 (dead-click) — dashboard 추천 질문 click → ⌘K palette open + query 자동
  - BUG-CURIOUS-003 (onboarding) — dashboard 진입 시 step 1~4 UI 발화
  - BUG-MOBILE-001 (헤더 잘림) — 375 viewport 에서 프로필 버튼 가시
  - BUG-CASUAL-001 (`/projects` 404) — sidebar 프로젝트 → list page 정상 도달
- Phase B Delta verify: Sentry Gemini API latency 5.76x (Phase A spike 일치)

---

## Success Criteria

본 sprint 종결 조건:

1. **Phase 1 DELTA gate PASS** — DELTA-1 worse 0 / DELTA-3 -10% 이내 / DELTA-2/4/5 ±20% 이내
2. **9 Phase 16 task 모두 commit + Codex APPROVE 2 cycle 연속**
3. **pytest 387 → 410+ + FE typecheck 0 + vitest 50 → 55+ + Playwright e2e 회귀 0**
4. **헌법 §4.2 정합** — `grep -rE 'from src\.embeddings' backend/src/memory/service.py` → 0 hit (repository.py 의 `_apply_hnsw_session_params` import 는 E-9 유지, 별도 허용)
5. **CONTEXT-MAP §7 BL-006 closed mark** + Atomic Update §2 매트릭스 모든 task 적용 (PR 본문 "Docs sync" 섹션 첨부)
6. **Dogfooding mini-redo** Curious 5 BUG 회귀 0
7. **PR `sprint-24/wave2-trusty-heron`** base=`main` (R7 verify) + draft → ready
8. **Carry-over BL 등재** — BL-NEW-RAG-SOURCE-SELECT (Sprint 25+ B path) + **BL-NEW-OBN-DATA-RETRY** (onboarding 재설계, F4 인터뷰 결과 기반) + Sprint 25 plan 초안 (T-LAND-01/02 + BL-T2 P2 5건 + Power P2 + BUG-CASUAL P2/P3 + a11y P2 + BL-068/069)

---

## 사용자 결정 게이트 (확정)

| 게이트 | 결정 |
|---|---|
| G1 Codename | `trusty-heron` |
| G2 stash@{0} | 보존 (R8, pop 금지) |
| G3 PR 전략 | A 단일 multi-commit PR |
| G4 T-BE-PERF | 포함 (Phase 6) |
| G5 Worktree | 머지된 2개 정리 완료 |
| Spec depth | Standard (15 question 확정) |
| T-AI-DATE | B (prompt + 후처리 검증) |
| T-RAG-MOCK-REMOVE | A 단기 + B Sprint 25+ 별도 |
| T-OBN-05 | **D (Codex+Gemini deep research 합의)** — banner FE 폐기 + Linear-style inline tooltip (첫 방문 페이지) + minimal analytics. BE hook + seed 유지. BL-NEW-OBN-DATA-RETRY 등재 (Sprint 25+, F4 인터뷰 결과 기반 재설계 검토) |
| T-MOBILE-HEADER | A (header padding reflow) |
| T-PROJ-LIST | A (카드 그리드) |
| T-NOTE-DETAIL | B (Tiptap viewer + edit-in-place) |
| T-CMD-K-FIX | A (⌘K palette + query 자동) |
| T-RAG-TIME-FILTER | A (BE 만 SQL clause) |
| T-AUDIT-VIEW UI | A (Settings audit 탭) |
| T-AUDIT-VIEW BE | A (단일 endpoint + item_type query) |
| T-BE-PERF | B (Spike + Top 1 bottleneck fix) |
| T-N+1 BL-006 | A (memory/pipeline_service.py 신설) |
| T-N+4 Whisper | A (1hr chunk + 5초 overlap) |
| T-N+2 fixture | A (tests/fixtures/composite_fk.py + conftest import) |
| PR commits | A (Phase 별 1 commit, ~9-10 base + Codex polish) |
| Carry-over | 최소 (BL-NEW + Sprint 25 명시) |

---

## Risk Register (R1~R8)

| R | Risk | Mitigation |
|---|---|---|
| R1 | Codex fact-mismatch | Stage 4 직전 함수명/모듈/hook placement grep verify (Wave 1 패턴 정합) |
| R2 | Sub-agent stall | T-AUDIT-VIEW BE/FE 분할 + T-BE-PERF 단일 dispatch, ~1.5h limit |
| R3 | 코드 외부 원인 | Playwright reproduce / curl first. T-BE-PERF 외부 의존 (Clerk JWT verify) 발견 시 BL carry |
| R4 | BE/FE shape mismatch | T-AUDIT-VIEW endpoint response schema alias_generator + Pydantic V2 alias |
| R5 | alembic scope | Wave 2 변경 0 (모든 task schema 변경 X 확정). drift gate PASS |
| R6 | scope overrun | T-BE-PERF Spike 6h 초과 시 fix carry Sprint 25 |
| R7 | stack PR base | `gh pr view <N> --json baseRefName` → "main" verify |
| R8 | stash@{0} 보존 | 어떤 worktree 에서도 pop 금지 (design-review 잔재) |
