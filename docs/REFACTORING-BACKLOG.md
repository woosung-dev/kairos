# Kairos 리팩토링 백로그

> deepen-modules audit 산출물. 각 BL 항목은 사용자 승인 후 등재.
> 형식: BL-NNN + 우선순위(★) + Sprint 권고

---

## 다음 Sprint 진입점 (Sprint 27+)

**Sprint 26 (glittery-tulip) 부터 sprint-별 handoff/closeout/verification/kickoff/final-summary 파일을 작성하지 않는다.** 지속 정보는 (1) git log + 머지된 PR body, (2) 이 백로그의 BL 항목, (3) `.claude/projects/.../memory/MEMORY.md` (선택). 다음 sprint 첫 commit 의도는 마지막 머지된 PR 의 "다음 sprint 진입점" 섹션에 1-3줄로 남긴다.

**현재 다음 픽업** (2026-05-23, Sprint 27a 진행 중): Sprint 26 머지 완료 (PR #104 → main `1be5beb`) → Sprint 27a luminous-anchor (D-6 grill + BL-S26-1 토큰컷, 본 PR) → Sprint 27b GA launch (Clerk Production + Svix + 외부 5명 dogfooding) → Sprint 28 paid customer 1명 (PMF signal).

**종료 기준** (3 도구 합의): GA launch 는 milestone, **paid customer 1명** 이 진짜 종료 신호.

---

## BL-S27c-1 — `get_current_user` lazy seed race condition fix ★★★ (P0)

**현 상태**: `backend/src/auth/dependencies.py:160-169` 의 User INSERT 가 race-unsafe. Dashboard 첫 진입 시 FE 가 5+ API 동시 호출 → 각 transaction 이 `find_by_clerk_id`=None → 동시 INSERT → 1개 성공 + 나머지 IntegrityError `duplicate key value violates unique constraint "ix_users_clerk_id"` → 500.

**증상 verified** (Sprint 27c audit, Account #3 c@e.com localhost 재현): `GET /workspaces` 500 + `/workspaces/{id}/members` 500 + `/workspaces/{id}/projects` 500 + `/workspaces/{id}/inbox` 403 (lazy fallback). production 의 동일 증상도 같은 race condition 추정 (deploy stale 가설 무효).

**목표**: User INSERT 에 `ON CONFLICT (clerk_id) DO NOTHING` 추가 (같은 file line 175-184 의 workspace INSERT 패턴 정합). 또는 try/except IntegrityError + retry find_by_clerk_id fallback.

**근거**: Sprint 27c audit, `docs/audits/2026-05-23-sprint27c-audit/ROOT-CAUSE-CORRECTION.md`.

**영향**: 외부 5명 진입 60-80% 첫 dashboard 진입 시 500 가능성. dogfooding prerequisite.

---

## BL-S27c-2 — GEMINI_API_KEY 재발급 ★★★ (P0)

**현 상태**: `backend/.env` 의 `GEMINI_API_KEY` invalid. BE log `google.genai.errors.ClientError: 400 API_KEY_INVALID`. 회의 업로드 → AI pipeline 전체 실패 (status="실패").

**목표**: Google AI Studio (`https://aistudio.google.com`) 에서 새 API key 발급 + local `.env` + Cloud Run secret 동기화.

**근거**: Sprint 27c audit, `docs/audits/2026-05-23-sprint27c-audit/qa-function.md` P0-AI-PIPELINE.

**영향**: Kairos 핵심 가치 (AI 자동 요약) 0. ADR-019 Phase B (gemini-3.1-flash-lite) 동작 prerequisite.

---

## BL-S27c-3 — Landing screenshot 3건 400 fix ★★ (P1)

**현 상태**: `/landing/screenshots/screenshot-dashboard.png` / `meeting-summary.png` / `rag-answer.png` 모두 Next.js Image optimizer 400. 파일 disk 존재 (`frontend/public/landing/screenshots/`). source code bug (localhost + production 동일 400).

**목표**: Next.js Image config / format / dimension issue 원인 진단 + fix. 또는 직접 `<img>` 태그 fallback.

**근거**: Sprint 27c audit `ceo-perspective.md` P1-S27c-1. "이미 동작하는 제품입니다" 섹션 trust 직격타.

---

## BL-S27c-4 — Meeting 실패 후 retry UI ★ (P2)

**현 상태**: meeting status="실패" 표시되나 retry 버튼 없음. R2 storage 의 stale audio 도 정리 안 됨.

**근거**: Sprint 27c audit `qa-function.md` P2-FAIL-NO-RETRY.

---

## BL-S27c-5 — Failed meeting copy mismatch ★ (P2)

**현 상태**: status=`실패` 인데 요약 탭 "AI 분석이 **완료되면** 요약이 자동으로 생성됩니다" 표시. 사용자 오해.

**목표**: status별 동적 copy ("실패" 시 "AI 분석 중단됨 / retry 권고" 등).

---

## BL-S27c-6 — Inbox `/inbox` empty state UI ★ (P2)

**현 상태**: 신규 가입 직후 `/inbox` 진입 시 헤더만 표시. empty state ("아직 항목이 없어요" 등) 부재. Memory + Projects page 와 일관성 불일치.

---

## BL-S27c-7 — `/actions` route 404 또는 진입점 부재 ★ (P2)

**현 상태**: `/actions` URL 직접 진입 시 404. dashboard 빠른 접근 카드에도 진입점 없음. CONTEXT-MAP §4.3 FE features 에 `actions` 명시.

**목표**: dedicated route 또는 meeting detail 내 action items 진입점 명시.

---

## BL-S27c-8 — A11Y PopoverTrigger nativeButton 3 page 공통 ★ (P1)

**현 상태**: Dashboard / Projects / CmdK 진입 시 console error `Base UI: A component that acts as a button expected a native <button> because the nativeButton prop is true`. OnboardingTooltip 의 PopoverTrigger render prop 에 non-button.

**목표**: PopoverTrigger 의 `nativeButton` prop=false 또는 render slot 에 native `<button>` 전달.

---

## BL-S27c-9 — Production health check + Cloud Run min instance 1 ★ (P1)

**현 상태**: production BE `/api/v1/health` 응답이 200 (~65ms) ↔ timeout (10s+) 반복. Cloud Run cold start aggressive scaling 추정. 외부 5명 동시 진입 시 SLA risk.

**목표**: Cloud Run min instance 1 권고 (USD ~$10-15/month) 또는 CDN 헬스체크 + alert 설정.

**근거**: Sprint 27c audit `cto-perspective.md` 운영 readiness 3/10 BLOCK 한계.

---

## BL-S27c-10 — Cloud Run secret rotation 정책 ★ (P2)

**현 상태**: GEMINI_API_KEY invalid 가 secret 관리 process 의 첫 실패 case. rotation 정책 (auto-renewal / alert / staging verify) 부재.

**근거**: Sprint 27c audit `cto-perspective.md` 보안 baseline.

---

## BL-S27c-12 — logout 시 `localStorage.kairos-workspace` clear ★★ (P1, Wave 4 발견)

**현 상태**: Clerk `signOut()` 후에도 `localStorage.kairos-workspace.activeWorkspaceId` 가 이전 user 의 workspace_id 잔존. 다른 user login 시 stale ID 사용 → cross-tenant API 호출 → 403 → UI 에 "워크스페이스 멤버가 아닙니다" 표시.

**증상**: Sprint 27c Wave 4 verify 중 재현 — Account #3 logout → Account #1 login 후 /new 페이지 진입 시 `1fcb8cf6-...` (Account #3 workspace) 호출 → 403. dashboard 는 graceful fallback (`/workspaces` list 후 retry) 동작, 다른 페이지는 fallback X.

**Fix 후보**: (a) Clerk `<SignOutButton onSignOutComplete>` hook 에 `localStorage.removeItem('kairos-workspace')` (b) Zustand persist onRehydrate 에 user_id verification 가드 (c) `kairos-workspace` 의 user_id 도 함께 저장 + activeWorkspaceId 와 비교.

**근거**: Sprint 27c Wave 4 audit `WAVE-4-VERIFIED.md`.

---

## BL-S27c-11 — Real IDOR + edge case 회귀 가드 강화 ★ (P2)

**현 상태**: Sprint 27c audit 에서 real cross-tenant IDOR verified (Account #1 → Account #2 workspace, 5 endpoint 403). 단 `backend/tests/integration/` 의 동일 시나리오 회귀 가드 명시 필요. Sprint 19 BUG-C01-EXT 의 후속 안정화.

**근거**: Sprint 27c audit `qa-edgecase.md` real verify 통과 + 헌법 I-9 정합 verified.

---

## BL-S27e-1 — RAG latency p95 < 5s 목표 + 모니터링 (Sprint 27d carry) ★ (P3)

**현 상태**: Sprint 27d opus audit (agent-3 CTO) localhost dev 5 sample 평균 10.6s. Gemini `gemini-3.1-flash-lite` API 응답 시간이 지배적. 캐시 hit 률 / cold path 분포 미관측.

**목표**: p95 < 5s. Sentry performance monitoring 도입 시 자동 추적 (ADR-021). 캐시 hit 률 + cold path 분포 모니터링.

**근거**: Sprint 27d opus audit BUG-S27d-6 (P3). 외부 dogfooding 시 UX 임계 임박.

---

## BL-S27e-2 — 사이드바 nav flicker 디버깅 (Sprint 27d carry) ★ (P3)

**현 상태**: Sprint 27d opus audit (agent-5 일반사용자) `/notes` 진입 시 사이드바 일부 nav link 가 일시 미표시 → 곧 정상 복원. useEffect dependency 또는 SWR cache hydration 타이밍 이슈 추정.

**목표**: render order 분석 + initial render 시 nav skeleton 또는 SSR-hydration 동기화.

**근거**: Sprint 27d opus audit BUG-S27d-7 (P3). 기능 손실 0, 시각 잡음.

---

## BL-S27e-3 — CSP 정책 도입 (Sprint 27d carry) ★ (P3)

**현 상태**: Sprint 27d 보안 헤더 fix (BUG-S27d-4) 에서 X-Frame-Options / X-Content-Type-Options / Referrer-Policy / Permissions-Policy 4종은 추가됐으나 CSP 는 의도적 SKIP. Next.js + Clerk + R2 + Sentry 등 다수 도메인의 정책 정리 미완.

**목표**: 외부 도메인 inventory 정리 → `strict-dynamic` + nonce 기반 CSP 적용. Clerk SDK 의 inline script 정책 호환 확인.

**근거**: Sprint 27d opus audit BUG-S27d-4 fix 시 CSP 분리. agent-3 CTO 권고.

---

## BL-S27e-4 — FE 병렬 E2E flake (storageState / account isolation) ★ (P3)

**현 상태**: Sprint 27d codex audit 의 CODEX-OBS-1. FE 전체 병렬 E2E 10 tests 중 2건이 최초 1회 실패 후 focused 재실행에서 PASS. `e2e/.auth/user.json` storageState 단일 공유 + onboarding localStorage 마크가 병렬 worker 간 race. dogfooding blocker 는 아니나 CI 게이트로 올리기 전 정리 필요.

**증상**: `pnpm e2e` 병렬 실행 시 `onboarding-tooltip-first-visit.spec.ts` + `actions-redirect.spec.ts` 일부 worker 가 동일 storageState 의 localStorage 마크 충돌로 console.error 또는 timing fail.

**Fix 후보**:
- (a) worker 별 storageState 분리 (`e2e/.auth/user-{worker}.json`) + setup 에서 N개 계정 병렬 로그인
- (b) onboarding localStorage 마크 prefix 에 worker index 포함
- (c) `fullyParallel: false` 임시 회귀 가드 (성능 손해)
- (d) onboarding spec 만 serial group 으로 격리 (project 분리)

**근거**: Sprint 27d codex final audit `codex-regression.md` CODEX-OBS-1. P3 분류.

---

## BL-S27-1 — WorkspaceMember.is_active soft delete (D-6.1 후속) ★

**현 상태**: WorkspaceMember 는 hard delete. 퇴사 사용자의 creator_id reference 가 orphan 표시.

**목표**: `is_active: bool` 컬럼 신설 + 퇴사 시 false 토글. audit trail 보존.

**근거**: ADR-023 D-6.1.

---

## BL-S27-2 — RAG 신선도 라벨 + 6개월 stale 알림 (D-6.2/D-6.5 후속) ★

**현 상태**: second-brain §6 Slite 모델 정의 (🟢 ≤1M / 🟡 1-3M / 🔴 >3M) — 미구현.

**목표**: RAG 응답에 신선도 라벨 + 6개월 미갱신 콘텐츠 "이 정보가 아직 유효한가요?" 알림.

**근거**: ADR-023 D-6.2 / D-6.5.

---

## BL-S27-3 — AdminAccessAudit 테이블 (D-6.4 후속) ★

**현 상태**: admin/owner 가 private project 조회 시 audit log 없음 (visibility bypass).

**목표**: `AdminAccessAudit (admin_user_id, private_project_id, first_access_at)` row 신설. 운영 가시성 + enterprise transition base.

**근거**: ADR-023 D-6.4 회수 옵션.

---

## BL-S26-1 — 필수 규칙 토큰 ≤ 3,000 추가 cut (Sprint 27a partial → carry-over) ★

**Sprint 27a 진행** (2026-05-23): 2,918→2,614 words / 3,793→~3,398 tokens (10% 절감). 목표 ≤3,000 까지 추가 13% cut 필요. CONTEXT-MAP I-2/I-9/I-14/I-17/I-18 압축 + §2 4 박스 → 1 박스 + AGENTS.md Kairos 컨텍스트 80줄 → 8줄 (CONTEXT-MAP 위임). 추가 cut 시 정보 손실 risk → plan §3 정책으로 잔여 carry. ★★→★ 강도 하향.

**현 상태:** 2026-05-23 Sprint 26 측정 = 2,845 words → 추정 3,698 tokens (목표 ≤ 3,000, 23% 초과).

**대상:** `AGENTS.md` (135줄) + `CONTEXT-MAP.md` (106줄) + `.ai/common/global.md` (71줄) + `.ai/templates/workflow.md` (80줄) = 392줄.

**후보 cut:** CONTEXT-MAP I-9 멀티테넌시 격리 한 줄 (11항 압축 가능) · I-14 SQLModel typed query allowlist 5 카테고리 → 표 1줄 · §2 핵심 엔티티 21개 → ERD 링크 + 핵심 12개 · §6 불변식 21개 중 일부 ADR 분리. AGENTS.md 신규 검증 증거 표준 5줄 → 워크플로우 참조 1줄.

**근거:** Sprint 26 메타-sprint 가 강행 cut 금지 정책 (plan risk mitigation §3) — 정보 보존 우선, 추가 cut 은 별도 BL.

**참조:** Sprint 26 verification 4회차 + memory `project_governance_lightening_decision` 4 신호.

---

## BL-S26-2 — docs/*.md ≤ 30 추가 cut (Sprint 26 carry-over) ★★

**현 상태:** 2026-05-23 측정 = 47 파일 (superpowers 제외, maxdepth 2). 목표 ≤ 30 (57% 초과).

**카테고리:** `docs/adr/` 19 + `docs/architecture/` 7 + `docs/requirements/` 8 + `docs/guides/` 8 + `docs/api/` 1 + `docs/plans/active/` 1 + root 3 (README/REFACTORING-BACKLOG/TODO).

**후보 cut:** (A) `docs/adr/` 19건 중 superseded 식별 → `docs/adr/archive/` 분리 + 카운트 제외 · (B) `docs/requirements/` 8건 중 interview-results/competitive-analysis archive · (C) `docs/architecture/` 7건 통합 (data-flow-example → ai-pipeline 흡수 등) · (D) `docs/guides/` 8건 중 r2-cleanup-cron + prompt-env-docs 통합.

**근거:** Sprint 26 plan G2 결정 (dev-log/qa+notes 전부 폐지) 적용 후에도 초과 → 추가 cut 별도 BL.

**참조:** Sprint 26 verification 4회차.

---

## BL-S26-3 — historical reference dead link cleanup (Sprint 26 carry-over) ★

**현 상태:** Sprint 26 P0-3 dev-log/sprints+qa+notes 폐지 후 `docs/TODO.md` + `docs/REFACTORING-BACKLOG.md` 본문 (L50/95/145/200/1768/1835 등) 에 historical reference 다수 잔존. agy 검증 3회차 REVISE 지적.

**후보:** (A) sed 일괄 — `docs/dev-log/{sprints,qa,notes}/...` 참조를 "(Sprint NN 산출물, git history 참조)" 로 inline replace · (B) TODO.md 통째 슬림 (518줄 → 100줄 미만).

**의도:** historical reference 는 context 보존 가치 vs dead link risk trade-off. agy = "신규 AI 가 폐지 경로 읽으려 시도할 수 있음" 권고 → cleanup.

**제외:** `docs/superpowers/plans/` + `docs/superpowers/specs/` (G1 = historical archive 보존).

**참조:** Sprint 26 verification 3회차 agy REVISE.

---

---

## BL-001 — meetings 파이프라인 status commit 단일화 (D-9 장기 개선)

**현 상태:**
`MeetingPipelineService.process_meeting` / `capture_text` 각각 4회 commit (transcribing, duration, analyzing, completed/failed). I-2 예외 조항으로 현재 허용 결정이지만 partial commit state가 존재함.

**목표 인터페이스:**
```python
# status progress 전용 테이블 분리 (예시)
class MeetingProgress(SQLModel, table=True):
    meeting_id: UUID
    step: str          # "transcribing" | "analyzing" | "completed" | "failed"
    created_at: datetime
    metadata: dict     # duration, error_message 등

# pipeline_service.py 는 meeting status를 한 번만 commit
# progress는 별도 insert (non-blocking, fire-and-forget 가능)
async def _report_progress(meeting_id, step, **meta): ...
```

**영향 파일:**
- `backend/src/meetings/models.py` — MeetingProgress 모델 추가
- `backend/src/meetings/pipeline_service.py` — commit 횟수 감소
- `alembic/versions/` — 마이그레이션 추가

**예상 LOC delta:** +50 (모델) / -30 (pipeline_service 단순화)

**Risk:** 🟡 중간 — polling API(`GET /status`)가 새 테이블을 읽도록 변경 필요

**Test harness:** 현 test 3개 존재. 마이그레이션 + polling API 테스트 추가 권고.

**우선순위:** ★★★☆☆

**Sprint 묶음 권고:** 단독 (Sprint 11+, F4 외부 인터뷰 완료 후)

**근거:** deepen-modules audit 2026-05-12 (docs/dev-log/notes/2026-05-12-meetings-deepen.md)

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
- `backend/src/meetings/pipeline_service.py` (360 LOC → ~250 LOC 예상)

**예상 LOC delta:** -100 ~ -110

**Risk:** 🟡 중간 — 파이프라인 핵심 코드, 테스트 3개로 회귀 검증 가능

**Test harness:** test_pipeline.py 3 테스트 존재. `_analyze_and_store` 단위 테스트 추가 권고.

**우선순위:** ★★★☆☆

**Sprint 묶음 권고:** BL-001과 묶어서 (Sprint 11+)

**근거:** deepen-modules audit 2026-05-12 (docs/dev-log/notes/2026-05-12-meetings-deepen.md)

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
- `backend/src/embeddings/repository.py` — `find_chunks_by_ids` 메서드 추가
- `backend/src/rag/service.py` — `_enrich_context` 배치 호출로 변경

**예상 LOC delta:** +12 (repository) / -8 (service)

**Risk:** 🟢 낮음 — 기존 메서드 제거 없음, 신규 추가만. 배치 반환 타입이 dict라 service 로직 소폭 변경 필요.

**Test harness:** 현 RAG service 단위 테스트 없음 (coverage ~0%). 마이그레이션 시 `test_rag_service.py` 신설 권고 — `_enrich_context` 단위 테스트 2건 (parent 있는 경우 / 없는 경우).

**우선순위:** ★★★★☆

**Sprint 묶음 권고:** 단독 (Sprint 12+). BL-001 meetings 상태 commit 단일화와 독립적. 저위험·고가치라 조기 처리 적합.

**근거:** deepen-modules audit 2026-05-12 Round 1 (docs/dev-log/notes/2026-05-12-rag-deepen.md)

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
- `backend/src/common/prompts.py` — Pydantic 모델 2개 추가 (또는 `common/llm_schemas.py` 신설)
- `backend/src/services/ai_processing.py` — 검증 2줄 추가 (summarize, extract_actions_and_link)

**예상 LOC delta:** +30 (스키마 모델) / +4 (검증 줄)

**Risk:** 🟢 낮음 — caller 변경 없음. `model_validate` 실패 시 Gemini 응답 파싱 에러로 처리 (현재도 ValueError로 처리 중, 에러 경로 동일).

**Test harness:** 현 ai_processing 단위 테스트 없음. 마이그레이션 시 `test_ai_processing.py` 신설 권고 — 스키마 불일치 시 ValidationError 발생 케이스 포함.

**우선순위:** ★★★☆☆

**Sprint 묶음 권고:** BL-003과 묶어서 (Sprint 12+). 둘 다 서비스 레이어 안전성 강화 방향으로 묶을 수 있음.

**근거:** deepen-modules audit 2026-05-12 Round 2 co-change 분석 (docs/dev-log/notes/2026-05-12-services-deepen.md)

---

## BL-005 — memory.service.promote() Service Session 직접 접근 제거 (I-1 / Backend Rules §3 위반)

**현 상태:**
`backend/src/memory/service.py:420, 431` — `MemoryService.promote`가 `self.repo.session.execute(target_q)` / `self.repo.session.execute(member_q)` 직접 호출. Backend Rules §3 (AsyncSession은 Repository만 보유) 위반. Workspace + WorkspaceMember 조회를 repo 위임 없이 inline.

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
- `backend/src/workspaces/repository.py` — 메서드 2개 추가 (이미 있을 가능성 있음, 확인 후 재사용)
- `backend/src/memory/service.py` — promote() session 호출 제거
- `backend/src/memory/dependencies.py` — WorkspaceRepository 주입

**예상 LOC delta:** +20 (repository) / -10 (service)

**Risk:** 🟢 낮음 — 동작 동일, 레이어 분리만

**Test harness:** `test_promote.py` 5 케이스 그대로 통과해야 함

**우선순위:** ★★★★★ (P0 헌법 위반)

**Sprint 묶음 권고:** BL-006과 묶어 Sprint 17 우선 처리

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-006 — memory → embeddings.create_chunk 직접 호출 → pipeline_service.py 분리 (ADR-014 위반) ✅ **완료 (Sprint 24 Wave 2 Phase 7, 2026-05-20)**

**현 상태 (해소 전):**
`backend/src/memory/service.py:550, :780` — `_bg_distill_and_embed` + module-level `_bg_promote_embed` 가 `from src.embeddings.repository import EmbeddingRepository` 를 lazy import 후 직접 `save_chunk` 호출. CONTEXT-MAP §4.2 + ADR-014 위반.

**해소 (2026-05-20):**
- 신설: `backend/src/memory/pipeline_service.py` — `MemoryPipelineService.save_memory_chunk(session, ...)` 가 `EmbeddingRepository.save_chunk` 호출 캡슐화. `source_type='memory'` 고정.
- 갱신: `backend/src/memory/service.py` — lazy import 2 hit 제거, `_bg_distill_and_embed` 와 `_bg_promote_embed` 가 pipeline 위임. `MemoryService.__init__` `pipeline: MemoryPipelineService | None = None` 추가, `_bg_*` 진입 전 fail-closed (`RuntimeError`).
- 갱신: `backend/src/memory/dependencies.py` — `MemoryPipelineService` 동반 주입.
- 회귀 방지: `backend/tests/architecture/test_no_memory_to_embeddings_lazy_import.py` 2 케이스 (lazy import 0 hit assertion + E-9 1 hit 유지 assertion).

**미해소 (E-9 예외 유지)**:
- `backend/src/memory/repository.py:33` 의 `from src.embeddings.repository import _apply_hnsw_session_params` 1 hit 는 vector_search HNSW SET LOCAL 위해 유지 (embeddings/CONTEXT.md E-9 — capsule 우회 최소 비용 약속, Sprint 16). vector_search 자체 흡수는 LOC vs 가치 비대칭으로 후속 sprint carry-over.

**테스트 결과**: pytest 406 → 408 + 1 skipped (architecture gate +2). 기존 memory 27 테스트 회귀 0.

**근거**: Sprint 24 Wave 2 trusty-heron plan / `docs/superpowers/specs/2026-05-20-sprint24-wave2-trusty-heron-design.md` §"T-N+1 BL-006".

---

## BL-007 — memory AI 호출 helper (`_call_distill` / `_call_embedding` / `_call_transcribe`) → services/memory_ai_calls.py 통합

**현 상태:**
`backend/src/memory/service.py:637~709` — module-level helper 3개에서 Gemini / OpenAI / Whisper client 직접 생성. 주석 "테스트 monkeypatch 진입점"이지만 BG task session_factory 컨텍스트와 AI 호출 시간 블로킹 분리 X. session orphan 위험.

**목표 인터페이스:**
```python
# services/memory_ai_calls.py 신설 (또는 services/ai_processing.py 확장)
class MemoryAiCallsService:
    async def distill(self, transcript: str) -> MemoryDistillResult: ...
    async def transcribe(self, r2_key: str) -> str: ...
    async def embed(self, text: str) -> list[float]: ...
```

**영향 파일:**
- `backend/src/services/memory_ai_calls.py` — 신설 (또는 ai_processing.py 확장)
- `backend/src/memory/service.py` — helper 제거

**예상 LOC delta:** +120 (services) / -75 (memory/service)

**Risk:** 🟢 낮음 — interface 변경 없음, 위치만 이동

**Test harness:** 신규 test_memory_ai_calls.py 필요

**우선순위:** ★★★☆☆ (P1, Seam 보강)

**Sprint 묶음 권고:** Sprint 18+ (BL-005/006 이후)

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-008 — memory R2 boto3 client 재생성 → R2Service 메서드로 상향

**현 상태:**
`backend/src/memory/service.py:602, 620` — `_upload_audio_to_r2` / `_download_audio_from_r2`가 R2Service 주입받지만 `self.r2_service._session.client(...)` non-public API 우회. Backend Rules §5 권장 (`aioboto3` async session 패턴) 위반.

**목표 인터페이스:**
```python
# common/r2.py R2Service 확장
class R2Service:
    async def upload_audio(self, key: str, body: bytes, content_type: str) -> None: ...
    async def download_audio(self, key: str) -> bytes: ...
    async def delete_audio(self, key: str) -> None: ...
```

**영향 파일:**
- `backend/src/common/r2.py` — 메서드 3개 추가
- `backend/src/memory/service.py` — helper 2개 → R2Service 메서드 호출

**예상 LOC delta:** +60 (r2.py) / -30 (memory/service)

**Risk:** 🟢 낮음 — interface 단순화. 기존 동작 동일.

**Test harness:** R2Service mock 테스트 추가

**우선순위:** ★★★☆☆ (P1)

**Sprint 묶음 권고:** Sprint 18+ (BL-007과 묶을 수 있음, 두 건 다 service.py LOC 감소)

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-009 — memory MemoryItem status state machine 분리 (3 BG task 중복 제거)

**현 상태:**
`backend/src/memory/service.py:515~549, 568~588, 755~787` — `processing → embedding_pending → active` (또는 embedding_failed) 전이 로직이 3개 BG task에 유사 중복. status 열거형은 `models.py:48~49`에 있지만 transition 검증 X. status 추가/변경 시 grep 3곳 수정 필요 (locality 낮음).

**목표 인터페이스:**
```python
# memory/status_flow.py 신설
class MemoryStatusFlow:
    @staticmethod
    def transition(current: str, event: str) -> str: ...   # valid 전이만 허용
    @staticmethod
    def is_terminal(status: str) -> bool: ...
```

**영향 파일:**
- `backend/src/memory/status_flow.py` — 신설
- `backend/src/memory/service.py` — 3개 BG task에서 사용

**예상 LOC delta:** +60 (status_flow) / -40 (service)

**Risk:** 🟢 낮음 — 행동 동일

**Test harness:** status_flow unit test 신설 + 기존 service 테스트 통과 유지

**우선순위:** ★★☆☆☆ (P2)

**Sprint 묶음 권고:** Sprint 19+ (BL-006 pipeline_service 분리 후 자연스럽게 결합)

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-010 — memory MemoryQueryEmbeddingCache race condition 정책 결정

**현 상태:**
`backend/src/memory/service.py:335~355` — `_get_query_embedding` cache lookup 후 저장 (line 354). 동시 호출 시 UNIQUE 충돌 무시 (`repository.py:269` "race condition은 무시"). 두 workspace가 동일 normalized_query 입력 시 cache 공유 여부 deterministic X.

**목표 인터페이스:**
정책 결정 필요:
- 옵션 A: workspace_id 기반 strict 격리 (현재 의도, 명시화)
- 옵션 B: cross-workspace shared cache (cost 절감 + 의미적 동일 query)
- 옵션 C: 둘 다 + 사용자 opt-in 플래그

ADR 신설 (ADR-020 후보) — Sprint 18+ wedge 검증 후 결정.

**영향 파일:**
- 정책 결정 후 `service.py:335~355` + `repository.py` 수정 또는 그대로

**예상 LOC delta:** TBD

**Risk:** 🟢 낮음 — 의미적 결정 ADR

**Test harness:** 정책에 따라 추가

**우선순위:** ★☆☆☆☆ (P2, 의미 결정)

**Sprint 묶음 권고:** Sprint 18+ (Recall demand 검증 N 충분 후)

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-011 — memory 모듈 test coverage 일괄 보강 (Stage 5-5 Testing specialist 9 critical)

**현 상태:**
Sprint 15 stage 5-5 testing specialist 9 CRITICAL + 4 INFORMATIONAL 미커버 경로 식별. 기존 6 test file (test_api/service/recall/promote/metrics/admin_cleanup)는 happy path 위주 — BG task 실행 / cross-ws isolation / status transition / RBAC 회귀 / lazy seed 회귀 미보호.

**목표 인터페이스:**
신규 또는 확장 test file 9개:
1. `test_promote.py` — target=personal/존재X/non-member 3 negative path
2. `test_api.py` — voice capture + oversized (413) + empty bytes (422)
3. `test_service.py` — _bg_distill_and_embed / _bg_transcribe_distill_embed / _bg_promote_embed 직접 await + status transition 검증 (성공+실패 분기)
4. `test_recall.py` — vector hit path (_call_embedding monkeypatch return fake 1536d) + cache hit + concurrent insert (ON CONFLICT 검증)
5. `test_promote.py` — cross-workspace memory_id isolation (404 보장)
6. `tests/auth/test_personal_workspace_seed.py` 신설 — lazy seed idempotent + 동시 호출
7. `test_memory_router_rbac.py` 신설 — viewer/member 차이 + 비-멤버 403
8. `test_admin_cleanup.py` — R2 delete monkeypatch + expired item 실제 row 갱신
9. `test_service.py` — PromotionAudit.embedding_status='failed' 분기 + Memory.status='embedding_failed'

추가 informational (P1):
- `test_dogfood_smoke_import.py` — scripts/dogfood_smoke.py import smoke
- `test_metrics.py` — percentile edge (NULL latency / 1건 / 다수)
- `test_api.py` — status state machine (5 status seed + GET)
- `test_service.py` — _normalize_audio ffmpeg 부재 fallback

**예상 LOC delta:** +700 (테스트 전체)

**Risk:** 🟢 낮음 — 테스트 추가만, 코드 변경 X

**Test harness:** 기존 conftest fixtures 재사용 (memory_client, seed_memory). RBAC fixture는 신규 (viewer / member / non-member user).

**우선순위:** ★★★★☆ (회귀 방지)

**Sprint 묶음 권고:** Sprint 16 첫 주 (Phase B Gemini swap과 묶음, BG task 변경 시 회귀 안전망 필수)

**근거:** Stage 5-5 testing specialist 2026-05-14

---

## BL-012 — memory 모듈 hygiene cleanup (Stage 5-5 Maintainability 18건)

**현 상태:**
Stage 5-5 maintainability specialist 18 INFORMATIONAL. dead code / magic constants / long methods / function-scope imports / DI bypass / silent failure. 각각 단독으로는 minor지만 누적 시 service.py 844 lines가 더 두꺼워짐.

**목표 인터페이스:**
1. Dead code: `WorkspaceMembershipError` 제거 (memory/exceptions.py:27 — 사용 X)
2. Dead field: `PromotionAudit.promoted_note_id` 제거 또는 사용 lock-in
3. Duplicate imports 정리 (service.py:202 timedelta, R2Service)
4. DI bypass: cleanup_expired_r2_audio가 `R2Service()` 재생성 -> `self.r2_service` 사용
5. Silent failure: R2 delete except에 `logger.warning` 추가
6. Magic constants: GEMINI_MODEL/WHISPER_MODEL/EMBEDDING_MODEL을 core/config.py로 이관 (ADR-019 Phase B와 묶기 적절)
7. ttl_days=7 / 30 / 365 named constants
8. Long methods: recall (90 lines) + promote (99 lines) helper 분리
9. Function-scope imports (service.py:406 select/Workspace/WorkspaceMember) module-level 이관
10. stale comment 정리 (service.py:598)

**예상 LOC delta:** -150 (cleanup) / +50 (helpers)

**Risk:** 🟢 낮음 — interface 변경 없음

**Test harness:** 기존 테스트 그대로 통과 + BL-011 보강된 회귀 안전망 활용

**우선순위:** ★★★☆☆ (P2 hygiene)

**Sprint 묶음 권고:** Sprint 17 (BL-005~010 본 묶음과 함께 — service.py 전체 리팩토링 1 PR)

**근거:** Stage 5-5 maintainability specialist 2026-05-14

---

## BL-013 — alembic migration FK ondelete + 2-phase deploy + downgrade safety

**현 상태:**
Stage 5-5 data-migration specialist 6 CRITICAL. Sprint 15 migration `a1b2c3d4e5f6_sprint15_memory_workspace_type.py`가:
1. 모든 FK에 `ondelete` 명시 X (default RESTRICT) — workspace 삭제 시 memory_items가 차단
2. Schema + backfill 단일 migration — 2단계 배포 위반 (.ai/stacks/fastapi/backend.md §9)
3. CREATE INDEX without CONCURRENTLY — prod scale에서 workspaces 테이블 ACCESS EXCLUSIVE lock
4. Downgrade가 데이터 손실 (DROP TABLE) — 사용자 확인 가드 부재
5. `workspaces.type` server_default='team'이 기존 solo workspace를 잘못 misclassify (founder 시나리오에서는 무영향이나 multi-tenant 시 surprise)

**목표 인터페이스:**
신규 migration 2~3개로 분리:
- `aXXX_alter_memory_fk_ondelete.py` — memory_items/ai_calls/events workspace FK -> CASCADE / promotion_audit -> RESTRICT
- `aYYY_split_workspace_type_backfill.py` — DDL과 DML 분리 (이미 적용된 상태이므로 2단계 deploy는 사후 documentation)
- downgrade에 `ALLOW_DESTRUCTIVE_DOWNGRADE` env 가드

**예상 LOC delta:** +120 (신규 migration 2~3개)

**Risk:** 🟡 중간 — prod DB 마이그레이션 추가 실행 필요

**Test harness:** test_alembic_memory.py 확장 — FK behavior 시뮬레이션 (workspace 삭제 -> memory_items CASCADE 검증)

**우선순위:** ★★★☆☆ (prod 배포 안정성)

**Sprint 묶음 권고:** Sprint 17 (multi-tenant 시점 이전 필수, 또는 첫 외부 user team 시점)

**근거:** Stage 5-5 data-migration specialist 2026-05-14

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
- `<WorkspaceTypeBadge type="personal" | "team" />` shared component (`frontend/src/features/workspaces/components/`)
- 사용 위치: switcher dropdown / topbar / recall card top-right / promote modal option

**예상 LOC delta:** +60 (신규 컴포넌트 + 4 호출처)

**Risk:** 🟢 낮음 — visual only

**Test harness:** Storybook or visual regression (없으면 design-review 재실행으로 검증)

**우선순위:** ★★★☆☆ (P2 polish — BL-014에 종속)

**Sprint 묶음 권고:** BL-014 후속 Sprint 16~17

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-1/F-17/F-40

---

## BL-016 — PromoteModal 동명 workspace 구분 (UX 모호성)

**현 상태:**
Stage 5-4 design-review. PromoteModal combobox에 동일한 name "E2E 테스트 워크스페이스" 4개 표시 (founder test data 결과). 코드는 `workspace.name` 그대로 렌더 → workspace.id로 distinct 하나 사용자는 4개 동일 옵션 사이 구분 불가.

**목표 인터페이스:**
- Option label에 secondary info 추가: `{name} · {membersCount}명` 또는 `{name} · {idSuffix-4}` 또는 `{name} · {createdAtRelative}`
- 또는 동명 그룹화 (헤더 + indent)

**예상 LOC delta:** +20 (PromoteModal option label)

**Risk:** 🟢 낮음

**Test harness:** Storybook fixture 또는 design-review 재실행

**우선순위:** ★★☆☆☆ (P2 — multi-tenant 시점 이전 필수, founder 1인 시점 무영향)

**Sprint 묶음 권고:** Sprint 17 (multi-tenant 진입 시)

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-23

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

## BL-019 — Recall metrics 신선도 + sparkline

**현 상태:**
Stage 5-4 design-review /admin/recall-metrics. `30초마다 자동 갱신` description 있으나 last-updated timestamp 미노출. 4 metric tile만, trend (7일) sparkline 없음. p95 4934ms = p50 4934ms (단일 데이터 포인트) — sparse data 표시 없음.

**목표 인터페이스:**
- header에 last-updated `{relative time}` 표시
- 각 metric tile에 7일 sparkline (memory_events 테이블에서 일별 aggregation)
- p95=p50 일치 시 "데이터 부족" badge
- BE: GET /workspaces/{ws}/memory/metrics?range=7d 옵션

**예상 LOC delta:** +200 (BE aggregation + FE sparkline)

**Risk:** 🟡 중간 (BE 신규 endpoint)

**Test harness:** test_memory_metrics_aggregation.py

**우선순위:** ★★☆☆☆ (P2 polish — founder admin)

**Sprint 묶음 권고:** Sprint 17+ (R7 metrics 정식 build)

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-30/F-31

---

## BL-020 — Recall result card / mobile placeholder polish (3건 묶음)

**현 상태:**
Stage 5-4 design-review 잡다한 polish 3건:
1. Mobile (375px) search placeholder "무엇을 다시 찾고 싶으세요? (예: Sprint 15 wedge)" 트런케이션 — viewport edge 잘림
2. Recall result card 날짜 format "2026. 5. 14." trailing period (Korean convention but uncommon for app UI)
3. Recall result card 우상단 "🔍 의미 매칭" label 위치 — title과 경쟁

**목표 인터페이스:**
1. Placeholder 단축: "무엇을 다시 찾고 싶으세요?" (예시 제거 또는 별도 hint)
2. Date format: relative ("오늘" / "어제" / "3일 전") 또는 ISO ("2026-05-14")
3. 의미 매칭 label: 우하단 corner로 이동 또는 icon-only tooltip

**예상 LOC delta:** +30

**Risk:** 🟢 낮음

**Test harness:** design-review 재실행

**우선순위:** ★☆☆☆☆ (P3 polish)

**Sprint 묶음 권고:** Sprint 17+ (polish bundle)

**근거:** Stage 5-4 design-review specialist 2026-05-14 F-18/F-21/F-37

---

## BL-021 — e2e auth.setup Clerk koKR label selector mismatch ✅ **완료 (commit 2bf3df8)**

**해결:** `frontend/e2e/auth.setup.ts:42` selector 를 `getByLabel(/email/i)` → `input[name="identifier"]` 로 정정. Clerk SDK standard input name 사용으로 locale-independent.

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

## BL-022 — embedding_chunks / semantic_caches 파티셔닝 (대규모 도달 시)

**도메인:** embeddings (pgvector HNSW 인덱스 운영)
**근거:** Sprint 16 ADR-020 §"Alternatives Considered" 2 — 파티셔닝 deferred 결정 (AD-54). 당근(Karrot) DB 밋업 1회 §4 노하우 — 1000만+ row 통테이블에서 HNSW 랜덤 I/O + Vacuum 시간 폭증 시 필요.

**문제 (지연):**
현재 kairos 데이터 규모는 작음 (chunk 수만 단위). HNSW + halfvec + iterative_scan 으로 충분. 하지만 다음 조건 도달 시 파티셔닝 필요:
- workspace 100+ (테넌트 격리 단위 증가)
- embedding_chunks 100만+ row (HNSW 단일 인덱스 메모리 압박)
- VACUUM ANALYZE 시간 분 단위 (운영 부담)
- 특정 workspace_id 쿼리 시 partition pruning 효과 ≫ HNSW 그래프 전체 탐색

**옵션:**

1. **workspace_id 기반 LIST 파티셔닝** — 워크스페이스당 인덱스 분리. RBAC 자연스러움. workspace 수가 적을 때 유효 (수십~수백).
2. **project_id 기반 HASH 파티셔닝** — 프로젝트 수 많을 때. 다만 RAG 쿼리는 project_id 필터 빈도 낮음 (workspace_id 위주).
3. **created_at 기반 RANGE 파티셔닝** — 시계열 데이터에 유리. 오래된 청크는 cold storage로 분리 가능.

**Trigger 조건 (재진입):**
- `SELECT count(*) FROM embedding_chunks` ≥ 1,000,000
- `SELECT count(*) FROM workspaces` ≥ 100
- `pg_stat_user_tables.n_live_tup` 기반 VACUUM 시간 5분 이상
- RAG p95 latency baseline × 1.5 이상 (`bench_vector_search.py --mode latency`)

**의존:**
- ADR-020 Stage 5 측정 통과 후 Accepted 상태 전제
- alembic 추가 마이그레이션 + 기존 데이터 재배치 (대용량 시 다운타임 가능 — backend.md §9 2단계 배포)
- 신규 ADR 작성 필요 (파티셔닝 키 + 인덱스 전략)

**예상 LOC delta:** +200~500 (alembic + repository.py 파티션 인지 쿼리 + 운영 스크립트)

**Risk:** 🟡 중간 (데이터 재배치 + planner 동작 변경)

**우선순위:** ★★☆☆☆ (조건부 미래 — Trigger 도달 전 보류)

**Sprint 묶음 권고:** 별도 sprint. ADR-020 후속.

---

## BL-023 — semantic_caches.hit_count 별도 테이블 분리 (당근 §4-B 갱신 잦은 컬럼 분리)

**도메인:** embeddings
**근거:** Sprint 16 ADR-020 §"AD-59" + 당근 DB 밋업 §4-B "갱신이 잦은 컬럼은 데드 튜플 양산하므로 별도 테이블로 분리".

**문제:**
`semantic_caches.hit_count`는 매 cache hit마다 `UPDATE ... SET hit_count = hit_count + 1` 발생 (`embeddings/repository.py:189`). 같은 row의 다른 컬럼 (`question`, `answer`, `sources`, `question_embedding`)은 불변. 빈번 UPDATE로 dead tuple 양산 + HOT update 실패 시 인덱스 update 비용.

**단기 대응 (본 sprint Stage 4 적용)**:
- `fillfactor = 80` → 페이지에 여유 공간 → HOT update 활성화
- `autovacuum_analyze_scale_factor = 0.02` → 통계 자주 갱신

**중장기 (BL-023)**:
별도 테이블 `semantic_cache_hits (cache_id PK, hit_count, last_hit_at)` 분리. semantic_caches는 불변 — INSERT 후 UPDATE 없음. hit_count 별도 테이블은 HOT update + 작은 row 사이즈로 dead tuple 영향 최소.

**Trigger:** semantic_caches row 10만+ 또는 fillfactor 적용 후에도 dead tuple ≥30% 측정 시.

**예상 LOC delta:** +120~200 (신규 테이블 + alembic + repository.py 분리 + service 호출 경로)

**Risk:** 🟡 중간 (cache invalidation race condition 검토 필요)

**우선순위:** ★★☆☆☆ (조건부)

**Sprint 묶음 권고:** Sprint 17+ ADR-020 후속.

---

## BL-024 — pg_prewarm 정책 (Cloud Run cold start 시 인덱스 워밍업)

**도메인:** infra / embeddings
**근거:** 당근 DB 밋업 §4-C "벡터 인덱스가 shared_buffers 캐시에 모두 올라갈 정도의 인스턴스 사양 + 노드 추가 시 pg_prewarm 워밍업".

**문제:**
Cloud Run + Neon Postgres 환경에서 BE 인스턴스 cold start 시:
- 첫 RAG 쿼리 → HNSW 인덱스 디스크 I/O → p99 latency spike
- shared_buffers는 PG instance 메모리에 의존 (Neon compute size)

**제안:**
1. **인덱스 사양 확인**: `pg_size_pretty(pg_total_relation_size('idx_chunks_hnsw'))` < Neon shared_buffers
2. **pg_prewarm**:
   ```sql
   CREATE EXTENSION pg_prewarm;
   SELECT pg_prewarm('idx_chunks_hnsw');
   SELECT pg_prewarm('idx_cache_hnsw');
   ```
3. **자동 워밍업** — Cloud Run job 또는 BE startup hook에서 `SELECT pg_prewarm(...)` 실행 (PG 재시작 시점만 의미 있음 — Neon serverless라 빈도 다름)
4. **모니터링** — `pg_stat_database.blks_hit / (blks_hit + blks_read)` 캐시 hit ratio ≥0.99

**Trigger:** p99 latency baseline × 2 도달 또는 인덱스 크기 > Neon shared_buffers.

**예상 LOC delta:** +60~80 (extension migration + prewarm script + startup hook)

**Risk:** 🟢 낮음 (read-only)

**우선순위:** ★★☆☆☆ (조건부)

**Sprint 묶음 권고:** Sprint 17+ ADR-020 후속 또는 운영 알람 트리거 시.

---

## BL-025 — 읽기 분산 (Neon read replica + 리더 라우팅)

**도메인:** infra / backend.core
**근거:** 당근 DB 밋업 §4-C "대규모 트래픽 시 읽기 분산(리더 DB 인스턴스)".

**문제:**
현 kairos는 단일 Neon DB. RAG 쿼리 (CPU heavy — HNSW 그래프 traversal) + capture/promote (write heavy)가 같은 인스턴스 경합.

**제안:**
1. **Neon read replica 활성화** (Neon plan upgrade 필요)
2. **app DATABASE_URL_REPLICA** 환경변수 추가 → `common/database.py` 분리
3. **읽기 쿼리 라우팅** — `vector_search` / `text_search` / `find_similar_cache` / `find_chunks_by_ids` → replica session; capture / promote / `save_chunks` → primary session
4. **PgBouncer 라운드로빈** — 당근 §5-A 노하우. Cloud Run 다중 인스턴스에서 connection 편차 해소

**Trigger:**
- RAG p95 ≥ 1초 또는 동시 사용자 50+ 또는 CPU 사용률 ≥80%

**예상 LOC delta:** +200~400 (database 분리 + repository read/write 어노테이션 + 트랜잭션 경계 재정의 + pgbouncer 설정)

**Risk:** 🟡 중간 (read-after-write 일관성 검토 필요 — capture 직후 recall 시나리오)

**우선순위:** ★★☆☆☆ (조건부)

**Sprint 묶음 권고:** Sprint 18+ ADR 신설 (읽기 분산 결정 + 일관성 정책).

---

## BL-026 — 측정 강화: nDCG / precision / 인덱스 빌드 시간 / EXPLAIN ANALYZE 헬퍼

**도메인:** embeddings / tests
**근거:** Sprint 16 ADR-020 Stage 5 verification 산출물 확장.

**문제:**
현 `bench_vector_search.py`는 recall@10 + p50/p95 만. 다음 측정 누락:
- **nDCG@10** — 순위 가중 적합도. recall@10보다 ranking quality 정확 반영
- **precision@10** — 결과 정확도
- **인덱스 빌드 시간** — HNSW CREATE INDEX CONCURRENTLY 측정 (ADR-020 §"비용/리스크" 데이터 부재)
- **EXPLAIN ANALYZE 헬퍼** — `Index Scan using idx_chunks_hnsw` 자동 검증 pytest fixture
- **다양한 query 종류** — 한국어 / 영어 / 짧은 / 긴 query 분포 분석

**예상 LOC delta:** +150~250 (bench script 확장 + fixture 다양화 + 헬퍼)

**Risk:** 🟢 낮음 (테스트/측정만)

**우선순위:** ★★★☆☆ (Sprint 16 Stage 5 진입 시 통합 권장)

**Sprint 묶음 권고:** **Sprint 16 Stage 5 verification** — 본 sprint 측정 산출물에 포함하거나 직후 sprint.

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
- `frontend/e2e/auth.setup.ts` GET/POST 응답 `.ok()` 가드 + 명시 error 메시지 (status + apiUrl + body[0..200])
- 기존 `.json().catch(() => [])` silent fallback 제거 (503 시 wsList=[] 분기로 빠져 POST에서 다시 SyntaxError 발생하는 도미노 차단)
- 후속 = 사용자 GCP 콘솔에서 E2E_API_URL secret 갱신 (또는 Cloud Run service 재배포)

**예상 효과:**
- 동일 회귀 재발 시 fail 1번에 원인 출력 (전: SyntaxError stack ×3, 후: `status=404 apiUrl=... body=<html>... → E2E_API_URL ... 점검 필요`)
- CI 디버깅 1 round trip 단축

**Risk:** 🟢 낮음 (e2e 가드만, 런타임 영향 0)

**우선순위:** ★★★★☆ (회귀 진단 시간 직결)

**Sprint 묶음:** BL-021 (Sprint 15 hotfix-2 Clerk koKR selector mismatch) + 본 BL-027 status code 보호 = auth.setup hardening 2건 누적.

---

## BL-028 — memory/service.py BackgroundMemoryService 분할

**도메인:** backend / memory
**근거:** Sprint 18 PR-C3 진행 중 발견. memory/service.py 864 LOC monolith. 클래스 메서드 `_bg_distill_and_embed` + `_bg_transcribe_distill_embed` + 모듈 함수 `_bg_promote_embed` 가 백그라운드 task 책임. Sprint 18 에서는 11줄 wrapper `_create_memory_embedding_chunk` 만 inline (circular import 회피).

**문제:**
- `_call_distill` / `_call_embedding` / `_call_transcribe` 모듈 헬퍼가 service.py 내부에 있어 background 분리 시 circular import.
- Foreground (capture_text/capture_voice/recall) + background (distill/embed/transcribe) 책임 단일 클래스 누적.

**해결:**
- `backend/src/memory/_helpers.py` 신설 — `_call_*` 헬퍼 3개 이동.
- `backend/src/memory/background.py` 신설 — `BackgroundMemoryService` 클래스 (3 백그라운드 task).
- `MemoryService.__init__` 에 BackgroundMemoryService 주입. router 변경 없음.

**예상 LOC delta:** service.py −300 / background.py +250 / _helpers.py +100. net +50, monolith 해소.

**Risk:** 🟡 중간 — session_factory 패턴 유지 + 22 memory tests 회귀 검증 필요.

**우선순위:** ★★☆☆☆ (구조 개선, 동작 동등)

**Sprint 묶음:** 단독 또는 다른 memory 부채 (BL-005/006) 와 묶음.

**근거:** Sprint 18 PR-C3 retrofit (commit ccfb192).

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

## BL-032 — superpowers/ stale doc 자동 archive 정책

**도메인:** docs / 운영
**근거:** Sprint 18 PR-B 에서 superpowers/ 24 파일 archive 시도 후 revert (스킬 자동 산출 위치라 archive 부적합). 향후 신규 plan/spec 도 시간 지나면 stale — 정책 없으면 누적.

**문제:**
- 스킬이 매 sprint plan/spec 자동 생성. Sprint 종료 후 plan 은 reference 가치 ↓.
- 영구 누적 시 docs/superpowers/ 비대.

**해결 후보:**
1. **시간 기준** — N+3 sprint 이상 stale plan 자동 archive (script).
2. **참조 기준** — 본문 frontmatter 에 `status: archived` 마킹 → 색인 제외.
3. **외부 저장** — docs/superpowers/ 자체를 git ignore + 별도 백업 storage.

**예상 LOC delta:** 정책 doc 1 + 스크립트 1 (~100 LOC).

**Risk:** 🟢 낮음.

**우선순위:** ★☆☆☆☆ (장기 — 누적 임계 시 진행).

**Sprint 묶음:** 단독, Sprint 25+ 추정.

**근거:** Sprint 18 PR-B revert (commit 51f8210).

---

## BL-033 — pyright + SQLModel false positive 다수 무관 진단

**도메인:** backend / devex
**근거:** Sprint 18 PR-A 진행 중 다수 pyright 진단 발생 — `Argument of type "bool" cannot be assigned to ... whereclause`. 모두 `.where(Model.col == value)` 패턴에서 SQLModel column comparison 을 bool 로 추론.

**문제:**
- 변경과 무관한 false positive 다수 → 신규 진단 노이즈 묻힘.
- IDE 경고 누적 → 개발자 무시 습관화 → 진짜 에러 놓침.

**해결 후보:**
1. SQLModel 타입 stub 갱신 (`sqlalchemy.orm.Mapped` 호환).
2. pyright config 에서 해당 룰 무시 또는 strictness 조정.
3. SQLModel → SQLAlchemy 2.0 native + Pydantic 분리 (장기).

**예상 LOC delta:** config 1줄 ~ 코드 전면 (옵션 별).

**Risk:** 🟡 중간 (옵션 3 시) / 🟢 낮음 (옵션 1/2).

**우선순위:** ★★☆☆☆.

**Sprint 묶음:** 단독.

**근거:** Sprint 18 PR-A diagnostic 누적.

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
- `backend/src/core/db.py` 또는 engine config 에 `pool_pre_ping=True`, `pool_recycle=300` 추가
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

## BL-037 ⚠️ DEFERRED (PR #44 closed by user, 2026-05-15) — DESIGN.md 결정 대기

**제목**: Google Fonts Satoshi 요청 pending → FOIT 가능성

**도메인**: frontend / typography network

**증상**: `https://fonts.googleapis.com/css2?family=Satoshi:...` 가 network 에서 pending 상태로 남음. fallback font 로 렌더되거나 FOIT 발생 가능.

**해결 방향**:
- Satoshi 가 Google Fonts 에 미공개 폰트 (이름 충돌? 직접 호스팅 필요?) — 확인 필요
- `font-display: swap` 또는 fallback 명시
- 또는 self-host (`/public/fonts/` + `@font-face`)

**우선순위**: ★☆☆☆☆ (P3 cosmetic, DESIGN.md 확인 필요)

**근거**: Sprint 17 QA, ISSUE-004.

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
- `backend/scripts/r2_cleanup.py` — aioboto3 비동기, uploads/ prefix 의 N 일 이상 객체 dry run/--delete
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

## BL-045

**제목**: Satoshi 폰트 정합 — Google Fonts URL 영구 pending, DESIGN.md 결정 필요

**도메인**: frontend / typography

**증상**: BL-037 fix (Fontshare URL 교체) PR #44 가 user 거절로 closed. DESIGN.md 의 의도된 Satoshi 사용 방법이 무엇인지 미정 (Fontshare CDN / self-host / Google Sans 대체).

**현 상태**: globals.css 의 `--font-display: 'Satoshi'` 에 대한 link 가 layout.tsx 에서 Google Fonts 404 → fallback 'sans-serif' 로 렌더.

**해결 방향**: DESIGN.md 검토 + 디자이너 결정 → fix.

**우선순위**: ★☆☆☆☆ (P3 cosmetic, fallback 으로 사용자 체감 영향 작음)

---

## BL-047 — projects.repository find_projects_by_meeting / add_meeting_link cross-domain cascade 모니터링

**도메인**: backend / projects + cross-domain (meetings/inbox/notes/rag)

**증상**: Sprint 19 PR #1 C9 (commit 6f646e7) 에서 ProjectRepository 의 `find_by_id` / `find_members` / `is_member` / `add_meeting_link` / `remove_meeting_link` / `find_projects_by_meeting` 시그니처 변경 후 cross-domain 호출자 (actions/inbox/notes/rag/meetings) 모두 전수 patch. 단 향후 새 도메인이 ProjectRepository 호출 시 시그니처 누락 잠재.

**현 상태**: handoff v2 의 Codex 2차 Minor 3 명시 finding. 본 C9 commit 으로 일부 해소 (cross-domain 호출자 cascade). 단 모니터링 필요.

**해결 방향**: lint rule 또는 grep CI 작업으로 1-인자 `find_by_id(project_id)` 호출 패턴 차단. 또는 Repository protocol 강제.

**우선순위**: ★★☆☆☆ (P2 monitoring, immediate risk 0 but 잠재 regression 방지)

---

## BL-048 — Sprint 19 PR #1 matrix endpoint 전수 forward coverage 강화

**도메인**: backend / tests

**증상**: Sprint 19 PR #1 C9~C12 의 `test_workspace_idor_matrix.py` 가 도메인별 signature anchor 6~8건 + representative endpoint forward 1~4건 으로 활성화. Codex 2차 review F-2 finding = "memory/rag/workspaces/upload 의 모든 endpoint 별 mock service kwargs 정확 비교 강화 필요".

**현 상태**: 45 endpoint 중 anchor + forward = ~40 test pass. positional fallback 허용 패턴 일부 남음 — generator 누락 catch 강도 약함.

**해결 방향**: (1) router 호출 모두 keyword 인자로 정리 (`service.method(workspace_id=workspace_id, ...)`) → matrix mock `call_args.kwargs.get("workspace_id") == workspace_a_id` 정확 비교 가능. (2) 도메인별 endpoint 전수 forward test 추가 — memory 4 / workspaces 8 / projects 11 (현재 4 만 forward).

**우선순위**: ★★★☆☆ (P2 hardening, 본 PR scope 외 — generator regression 방지)

**근거**: Sprint 17 QA, PR #44 close.

---

## BL-049 — production-scale alembic guard (NOT VALID + VALIDATE 2단계 + CONCURRENTLY)

**도메인**: backend / alembic / DBA runbook

**증상**: Sprint 19 PR #2 BUG-C01-EXT-FK 의 alembic migration `e5f6g7h8i9ja` 가 단순 `op.create_foreign_key` + `op.alter_column ... SET NOT NULL` 패턴 사용. dogfooding scale (~수십 row) 에서는 ms 단위 lock — 안전.

production scale (>1만 row 또는 동시 트래픽) 진입 시 다음 패턴 권장:
- `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY ... NOT VALID` + 별도 `ALTER TABLE ... VALIDATE CONSTRAINT ...` (lock 격하)
- `CREATE UNIQUE INDEX CONCURRENTLY` + `ALTER TABLE ... ADD CONSTRAINT ... USING INDEX`
- `ALTER COLUMN ... SET NOT NULL` 의 `CHECK (col IS NOT NULL) NOT VALID` → `VALIDATE` → `SET NOT NULL` 패턴
- `LOCK TABLE ... IN EXCLUSIVE MODE` (backfill 중 신규 insert 차단)

**현 상태**: PR #2 머지 시점 = dogfooding scale + Cloud Run entrypoint = 자연 maintenance window. 본 BL 은 첫 외부 user 온보딩 직전 audit 트리거.

**해결 방향**: 단일 테이블 1만 row 이상 또는 production traffic 발생 시 위 패턴으로 alembic template 갱신.

**우선순위**: ★★☆☆☆ (P2 production hardening, 현 시점 risk 0)

**근거**: Sprint 19 PR #2 plan agent 평가, Codex 1차 F-6 review.

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

`backend/tests/fixtures/composite_fk.py` + `backend/tests/integration/test_composite_fk_scn_matrix.py` —
SCN-FK-01~12 매트릭스 (4 entity × 3 op = 12 case) 자동화. 회귀 시 SCN ID 로 즉시 식별.
기존 `test_workspace_fk_cross_tenant_block.py` (7 case) 와 상호 보완.

### Carry-over (Sprint 22+)

- memory_items.embedding_chunk_id — embedding_chunks(id, workspace_id) UNIQUE 선행 작업 필요
- memory_ai_calls.memory_id — memory_items(id, workspace_id) UNIQUE 선행 + NOT NULL FK 패턴 다름
- promotion_audit (source/target workspace_id) — intentional cross-workspace, 별도 분석

**근거**: Sprint 19 PR #2 plan agent §D scope omission, Codex 1차 F-8.

---

## BL-051 — Sprint 15/16 기존 schema drift 정리 (compare_metadata 잔여 finding)

**도메인**: backend / SQLModel models / alembic

**증상**: Sprint 19 PR #2 D7.5b `test_alembic_upgrade.py` 신설 (alembic.compare_metadata) 시 PR #2 scope 외 다수 drift 검출. PR #2 의 `_is_pr2_scope_drift` filter 가 BL-051 카테고리로 분리:
- `memory_ai_calls.created_at` / `memory_events.created_at` / `memory_items.created_at` 등 TIMESTAMP(timezone=True) vs DateTime() (Sprint 15)
- `embedding_chunks` / `semantic_caches` 의 HNSW + halfvec 인덱스 model 미명시 (Sprint 16 ADR-020)
- `workspaces.type` / `workspaces.inbox_threshold` / `workspace_invites.default_project_visibility` server_default 차이 (Sprint 15)
- `idx_workspace_members_ws_user` / `idx_projects_workspace_status` / `idx_projects_workspace_sort` 등 인덱스 명시 누락 (Sprint 16 BL-036)
- `notes.content` JSON server_default

**해결 방향**:
1. 각 model `__table_args__` 또는 Field 에 `sa_column=Column(..., server_default=...)` 명시
2. 인덱스는 `Index(...)` 또는 `Field(..., index=True)` + 복합 인덱스는 `__table_args__` 에 `Index(...)` 추가
3. TIMESTAMP(timezone=True) ↔ DateTime() 통일 — Sprint 15 의 timezone-aware 마이그레이션 fix
4. drift filter 의 `_is_pr2_scope_drift` op_type filter (modify_default / modify_type 등) 점진적 축소

**우선순위**: ★☆☆☆☆ (P3 cleanup, runtime 영향 0 — 단 향후 신규 model 추가 시 alembic 누락 catch 약화)

**근거**: Sprint 19 PR #2 D7.5b drift detection 도입 후 catch 한 기존 부채.

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
- 헌법 patch 동반 (CONTEXT-MAP I-14 + backend/CONTEXT.md B-10 + .ai/stacks/fastapi/backend.md)
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
- `backend/CONTEXT.md` B-10: 동일 정정 + N+1 방지 selectinload 동일

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

## Sprint 22 carry-over (CO-1~14, 2026-05-19 Sprint 23 진입 시 BL 등재)

> 출처: `~/.claude/projects/.../memory/project_sprint22_done.md` carry-over 섹션. Sprint 24+ 진입 시 각 BL 상세 채움.

## BL-055 — OpenTelemetry full instrumentation (CO-1)

**현 상태:** Sprint 22 Sentry FE+BE conditional init 적용 (ADR-021). OpenTelemetry 는 Sentry 위 layer 로 RAG p50/p95 / pipeline span / cross-domain trace 미구현.

**목표:** OpenTelemetry SDK 도입 → RAG 6-Layer + meetings pipeline + cross-domain orchestrator span 측정. Sentry breadcrumb + OTel span 통합.

**Risk:** 🟡 중간 — production 비용 + Cloud Run cold start 영향 측정 필요.

**우선순위:** ★★★☆☆ (P2, Sprint 24+ observability sprint 묶음)

**Sprint 묶음 권고:** Sprint 25+ production observability deepening

**근거:** Sprint 22 carry-over CO-1.

---

## BL-056 — Email reminder for stuck onboarding (CO-2)

**현 상태:** Sprint 22 OBN-02 onboarding_step 0~4 적용. step ≤ 2 + 24h+ 정체 user 대상 reminder 미구현.

**목표:** BackgroundTask 또는 별도 worker → step ≤ 2 + last_activity > 24h user 에게 email reminder 발송. unsubscribe link 포함.

**Risk:** 🟢 낮음 — email provider 선정 + template 필요.

**우선순위:** ★★☆☆☆ (P3, growth marketing 후순위)

**Sprint 묶음 권고:** 외부 user dogfooding 시작 후 retention 측정 결과 기반.

**근거:** Sprint 22 carry-over CO-2.

---

## BL-057 — Onboarding step 5+ collaboration (CO-3)

**현 상태:** Sprint 22 OBN-02 step 4 (RAG ask) 까지 정의. 협업 액션 (첫 댓글 / 첫 share / 첫 invite) 후속 step 미정의.

**목표:** step 5+ 추가 — 첫 댓글 / 첫 share / 첫 invite 이벤트 hook. 협업 onboarding 측정.

**Risk:** 🟢 낮음 — onboarding 도메인 module 확장.

**우선순위:** ★★☆☆☆ (P3, 협업 기능 활성화 후)

**Sprint 묶음 권고:** Sprint 26+ 협업 기능 sprint.

**근거:** Sprint 22 carry-over CO-3.

---

## BL-058 — A/B test framework for OnboardingBanner copy (CO-4)

**현 상태:** OnboardingBanner copy 하드코딩. A/B 측정 framework 부재.

**목표:** PostHog / GrowthBook 등 도입 → banner copy variant A/B → conversion 측정.

**Risk:** 🟡 중간 — 외부 provider 선정 + feature flag 인프라.

**우선순위:** ★★☆☆☆ (P3, growth experimentation 후순위)

**Sprint 묶음 권고:** Sprint 27+ growth experimentation.

**근거:** Sprint 22 carry-over CO-4.

---

## BL-059 — Sentry observability 후속 (BL-OBS-1/2/3, CO-8/9/10)

**현 상태:** Sprint 22 Sentry FE+BE conditional init 적용. quota 모니터링 + 배포 체크리스트 + PII linter 미구현.

**목표:**
- BL-OBS-1: Sentry quota 모니터링 (월 한도 임계 알람)
- BL-OBS-2: 배포 체크리스트 (DSN env 검증 + before_send PII scrub regression 차단)
- BL-OBS-3: PII linter (CI 단계 `name` / `email` / `phone` 등 민감 필드 server-side 로그 차단)

**Risk:** 🟡 중간 — CI 단계 linter false-positive 조정 + provider 한도 추적.

**우선순위:** ★★★☆☆ (P2, production observability 안정화)

**Sprint 묶음 권고:** Sprint 24/25 observability sprint.

**근거:** Sprint 22 carry-over CO-8/9/10.

---

## BL-060 — Playwright G3/G5/G6 progress N/4 assertion (CO-11)

**현 상태:** Sprint 22 Playwright G2/G7/G8 NEW. G3/G5/G6 progress N/4 assertion 보강 미진행 (runtime fixture 후).

**목표:** Playwright spec G3/G5/G6 에 OnboardingBanner progress N/4 assertion 추가. runtime fixture 도입 후 활성화.

**Risk:** 🟢 낮음.

**우선순위:** ★★☆☆☆ (P3).

**Sprint 묶음 권고:** Sprint 24/25 e2e coverage 보강.

**근거:** Sprint 22 carry-over CO-11.

---

## BL-061 — Playwright G4 SSE mock 디버깅 (CO-12)

**현 상태:** Sprint 22 G4 SSE mock 디버깅 시 sub-agent stall. spec skip 상태.

**목표:** G4 spec runtime PASS — SSE response mock fixture 안정화 + done event 처리.

**Risk:** 🟡 중간 — SSE mock pattern 표준화 필요.

**우선순위:** ★★★☆☆ (P2).

**Sprint 묶음 권고:** Sprint 24 e2e fix.

**근거:** Sprint 22 carry-over CO-12.

---

## BL-062 — BE timezone-aware DateTime 전환 (CO-14)

**현 상태:** Sprint 22 Codex 2차 polish 에서 FE Zod `.datetime()` (Z suffix 강제) 제거 + nullable 유지. BE 가 naive DateTime 사용 중. FE 가 timezone 보장 못함.

**목표:** BE 의 `datetime.utcnow()` → `datetime.now(UTC)` 전 도메인 통일 + alembic timezone aware migration + FE Zod `z.iso.datetime()` 복원.

**Risk:** 🔴 높음 — 전 도메인 모델 + 기존 row backfill + FE all date display 영향.

**우선순위:** ★★★☆☆ (P2 — type safety + global team 대비).

**Sprint 묶음 권고:** Sprint 26+ 전 도메인 timezone migration sprint.

**근거:** Sprint 22 carry-over CO-14 + Sprint 6 dogfooding PR #14 (workspaces timezone-naive 통일).

---

> **CO-5** = BL-050 의 "잔여 3 entity (memory_items / memory_ai_calls / promotion_audit)" 로 흡수. BL-050 §"잔여" 섹션 참조.
> **CO-6** = ADR-019 Phase B (Gemini 3.1-flash-lite 6 spots swap, 2026-05-28 EOL) — TODO.md Sprint 24+ Next Actions 명시. BL 신설 없음.
> **CO-7** = BUG-AUTH-WH (Clerk webhook Svix 서명 + event allowlist + idempotency) — Sprint 19 PR #3 carry. BL 신설 없음.
> **CO-13** = `test_config.py` pyright +3 baseline (본 sprint 무관) — micro fix, BL 신설 가치 적음. Sprint 24+ 자율 cleanup.

---

## BL-063 — ActionItem 도메인 promote source actions 복제 (Sprint 23 CO-15)

**현 상태:** Sprint 23 D4 Meeting promote 가 `action_item_count=0` reset (Codex 3차 P3 fix). 실 ActionItem 행은 복제 안 함 → target meeting 의 action 탭 빈.

**목표:** Meeting promote 시 source 의 ActionItem rows 도 새 meeting_id 로 remap 복제. 또는 사용자 명시 trigger UI (별도 ActionItem promote endpoint 이미 존재).

**Risk:** 🟢 낮음.

**우선순위:** ★★☆☆☆ (P3) → **Sprint 24 P1 승격 (diligent-beaver)**.

**Sprint 묶음 권고:** ~~Sprint 25+ promote 정합성~~ → **Sprint 24 diligent-beaver 진입** (사용자 결정: 자동 복제 default, action_item_count 0 reset 제거).

**근거:** Sprint 23 D4 Codex 3차 P3 carry-over.

---

## BL-064 — Note promote 의 임베딩 재계산 옵션 (Sprint 23 CO-16)

**현 상태:** Sprint 23 D4 Note promote 가 source chunk 0 인 경우 `NotePromoteNotEmbeddedError(400)` 거부 (Codex 6차 P2 fix). 사용자에게 재시도 안내.

**목표:** source plain_text 있고 chunk 만 부재 (embed_note_async race) 인 경우 target ws 에 `embed_note_async` 흐름 schedule → 자동 embedding. UX 개선.

**Risk:** 🟡 중간 — EmbeddingService instance + BG task chain.

**우선순위:** ★★☆☆☆ (P3) → **Sprint 24 P1 승격 (diligent-beaver)**.

**Sprint 묶음 권고:** ~~Sprint 24/25 promote UX 보강~~ → **Sprint 24 diligent-beaver 진입** (사용자 결정: BG schedule + embedding_status="regenerating" 필드 + polling endpoint).

**근거:** Sprint 23 Codex 6차 P2 권장 "Recompute embeddings".

---

## BL-065 — Member.last_active_at 필드 (Sprint 23 CO-17)

**현 상태:** Sprint 23 D2 Variant C 디자인 보완 detail "last activity Nd ago". `Member` type / BE schema 미존재 → 미적용 (visual-only 스코프 유지).

**목표:** BE `WorkspaceMember.last_active_at` column + alembic + FE `Member.lastActiveAt` + member-list row 우측 "Nd ago" 표시 (Geist Mono 11px).

**Risk:** 🟡 중간 — schema 변경 + activity tracking 로직 (기본 = last API 호출 시점).

**우선순위:** ★★☆☆☆ (P3).

**Sprint 묶음 권고:** Sprint 26+ Settings UX.

**근거:** Sprint 23 D2 Variant C 시안 미적용 carry-over.

---

## BL-066 — D1/D3 dogfood verify (Sprint 23 CO-18)

**현 상태:** Sprint 23 Task 5 D1 (WorkspaceSwitcher) + Task 6 D3 (Inbox dismiss UX) = 정적 분석 + minimal fix. 실 dev server reproduce 미진행.

**목표:** dev server 또는 CI e2e job 결과로 fix 실 효과 확인. 부족 시 root cause 추가 분석.

**Risk:** 🟢 낮음 — verify 작업.

**우선순위:** ★★★☆☆ (P2 — dogfood validation).

**Sprint 묶음 권고:** **Sprint 24 diligent-beaver 진입** (Task 1, 진단 first 강제).

**근거:** Sprint 23 진단 first 미완 (Playwright reproduce 환경 의존).

---

## BL-067 — pyright `_update(...).where(...)` false-positive (Sprint 23 CO-19)

**현 상태:** memory / meetings / notes / actions 도메인 `session.exec(_update(M).where(M.id == X).values(...))` 패턴이 pyright reportAssignmentType false-positive (M.id 의 bool 캐스팅). 4 도메인 동일.

**목표:** pyright stub 또는 SQLModel typing 개선으로 false-positive 차단. 또는 `# type: ignore[...]` 일관성 적용 + 사유 명시.

**Risk:** 🟢 낮음 — type 진단만, runtime 무관.

**우선순위:** ★☆☆☆☆ (P4 — quality of life).

**Sprint 묶음 권고:** Sprint 27+ pyright cleanup.

**근거:** Sprint 23 다수 sub-agent 발견.

---

## BL-068 — D1 WorkspaceSwitcher Playwright/manual reproduce (Sprint 24 BL-066 carry)

**현 상태:** Sprint 24 BL-066 정적 분석 결과 Sprint 23 `9e2eee2` D1 fix 가 현 코드에 정합 반영됨 (`queryClient.invalidateQueries(predicate)` + `router.refresh()` 제거 + ws list 보존). Playwright reproduce 는 Clerk OAuth (Google) 자동화 한계 + 실 user data (다중 ws account) 의존으로 carry-over.

**목표:** Playwright `storageState` 캡쳐 (사용자 manual 1회 로그인 후 cookie state 저장) 또는 Clerk dev mode test user API (Sprint 22 OBN-01 패턴) 활용한 e2e spec. D1 시나리오: ws switcher 클릭 → 다른 ws 전환 → dashboard data 갱신 + ws list 보존.

**Risk:** 🟢 낮음 — verify 작업. Clerk infrastructure 의존.

**우선순위:** ★★☆☆☆ (P3 — manual dogfood 가능 시 P2 승격).

**Sprint 묶음 권고:** Sprint 25+ e2e Clerk infrastructure.

**근거:** Sprint 24 BL-066 carry-over (Playwright reproduce 환경 의존).

---

## BL-069 — D3 Inbox dismiss Playwright/manual reproduce (Sprint 24 BL-066 carry)

**현 상태:** Sprint 24 BL-066 정적 분석 결과 Sprint 23 `928fc7c` D3 fix 가 현 코드에 정합 반영됨 (`useInbox(wid, {isProcessed: false})` queryKey 격리 + `invalidate inboxKeys.byWorkspace(wid)` prefix + autoProcessed 그룹 제거 + camelCase param BE alias 정합). Playwright reproduce 는 BL-068 과 동일 인프라 의존.

**목표:** Playwright spec — inbox 항목 dismiss → list 즉시 사라짐 → reload 후에도 보존 verify. 사용자 manual carry-over 또는 BL-068 인프라 도입 후 묶음 진행.

**Risk:** 🟢 낮음 — verify 작업.

**우선순위:** ★★☆☆☆ (P3).

**Sprint 묶음 권고:** Sprint 25+ e2e Clerk infrastructure (BL-068 동반).

**근거:** Sprint 24 BL-066 carry-over.

---

## ~~BL-T2-003~~ — Whisper chunk 분할 (4hr+) ✅ **완료 (Sprint 24 Wave 2 T-N+4, 2026-05-20)**

**현 상태**: **[해소 2026-05-20] Sprint 24 Wave 2 T-N+4**. 4시간+ recording production 처리 차단 해소.

**원본 발견**: Sprint 24 Multi-Agent QA Day 1 Sentinel Tier 2 (`docs/dev-log/qa/2026-05-19-sprint24-qa-multi-agent/verification.md:272`).

**문제**:
- `transcription.py:TranscriptionService.transcribe()` 가 Whisper API 단일 호출.
- 60MB+ audio (Whisper 25MB 제한 초과) 업로드 시 API 400 — 4hr+ recording 처리 불가.

**해소 결과 (PR: Sprint 24 Wave 2 Phase 8)**:
- `services/chunked_transcription.py` 신설 — `_ffmpeg_probe_duration` + `_ffmpeg_split` + `_whisper_transcribe_single` + `_merge_with_offset` + `transcribe_chunked` (5 모듈 함수).
- `services/transcription.py` 에 `TranscriptionService.transcribe_with_chunking(audio_bytes, filename)` entry 추가 — 1hr 이하 단일 호출, 1hr 초과 chunked 경로 분기.
- `meetings/pipeline_service.py:process_meeting` 호출처 교체 (`transcribe` → `transcribe_with_chunking`).
- `tests/services/test_whisper_chunked_4hr.py` — 3 신규 test (short single / 4hr 4 chunk offset / overlap dedupe). mock 기반 (ffmpeg/Whisper 실제 호출 회피).

**Atomic Update**: `backend/CONTEXT.md` §10 STT 파이프라인 + `docs/architecture/ai-pipeline.md` §"STT (Speech-to-Text)" + 본 BL closed mark.

**제약·후속**:
- 4hr 라이브 audio 실측은 별도 dogfood 과제 (테스트는 mock 검증). 사용자 audio sample 확보 시점에 production 1회 verify 권장.
- 더 정교한 dedup (text 유사도 / 시간 fuzzy match) 필요 시 후속 BL 발의 — 현재는 exact text match within overlap window.

---

## BL-NEW-RAG-SOURCE-SELECT — RAG source-level selection v1 (Sprint 25+ 검토)

**현 상태:** 미시작 (carry-over from Sprint 24 Wave 2 T-RAG-MOCK-REMOVE / BUG-POW-005).

Sprint 24 Wave 2 T-RAG-MOCK-REMOVE 에서 `frontend/src/features/rag/components/search-scope.tsx` 의 MOCK_SELECTABLE_SOURCES 5건 제거 후 "선택한 소스" 탭을 "소스 선택 기능 준비 중 — 현재는 전체 워크스페이스에서 검색합니다" empty state 로 변경. 장기적으로 source-level (회의/노트 단위) RAG 검색 범위 선택이 실제로 필요한가는 Power persona 데이터 수집 후 결정.

**목표:**

1. BE: `GET /api/v1/workspaces/{wid}/embeddings/sources?type=meeting|note` — indexable source list endpoint (페이지네이션 + name + type + project_id + project_name).
2. FE: selection state (Zustand or local) + RAG `/ask` 요청에 `source_ids: list[uuid]` 전달.
3. BE: `embeddings/repository.py vector_search` 에 `source_ids` filter SQL clause 추가 (workspace_id + source_ids).

**Risk:** 🟡 중간 — 신규 endpoint + RAG filter SQL clause 추가. 인덱스 영향 검증 필요 (workspace_id + source_type composite index 활용 가능 여부).

**우선순위:** ★★☆☆☆ (P2 — Power user feature, wedge 정합 미증명).

**Sprint 묶음 권고:** Power persona 인터뷰 (F4 outreach) 결과 confirmed + 명시적 요구 시 Sprint 25+ 진입. 아닐 시 폐기 + UI 자체 hide.

**예상 시간:** 3-5h.

**근거:** Sprint 24 Wave 2 T-RAG-MOCK-REMOVE — MOCK 데이터가 실 워크스페이스 명/회의 명을 false-impression 출력해 Power user 가 selection 시도 → 검색 결과 mismatch 발생.

---

## BL-NEW-DELTA3-REMEASURE — Phase B swap DELTA-3 P/R n=20 재측정 (Sprint 24 Wave 2 carry)

**현 상태:** 미시작 (carry-over from Sprint 24 Wave 2 Phase 1 T-2 post-swap delta gate).

Phase B `gemini-2.5-flash → gemini-3.1-flash-lite` swap 후 DELTA-3 액션 추출 P/R 측정 결과 `ΔP=-30% / ΔR=-22.2%` (n=5 sample, token-level overlap). 수치상 gate 임계 -10% 초과 FAIL 이지만 (1) sample size n=5 + 1 mismatch=±10% jump 의 noise floor, (2) 주 원인이 양 모델 공통 `due_date` 2024 hallucinate (Phase 2 T-AI-DATE 가 fix), (3) assignee 누락 + 회의 일정 over-extraction (Phase 2 prompt 강화로 fix) → **conditional PASS** 판정 후 Phase 2 진입.

Phase 2 T-AI-DATE 완료 후 n=20 으로 확장 재측정해 P/R 회복 confirmation 필요.

**목표:**

1. `backend/tests/llm/fixtures/sample_transcripts.py` 의 DELTA_3 ground-truth sample 을 5 → 20 으로 확장 (다양한 회의 시나리오 — 1:1, 4+명 회의, 마감일 명시/미명시 mix, assignee 명시/미명시 mix).
2. `backend/scripts/sprint24_wave2_delta.py` (또는 후속 sprint 의 동등 스크립트) 로 post-Phase-2 모델 (gemini-3.1-flash-lite + T-AI-DATE prompt) 재측정.
3. 결과 비교: baseline `P=1.000 R=1.000` (n=5) vs post-Phase-2 (n=20) — gate 임계 P/R ≥ 0.9.
4. fail 시: prompt 추가 강화 (예: assignee 명시 의무 위반 사례 Few-shot 추가) 또는 hybrid (chain-of-thought 또는 2-step extraction) 도입 검토.

**Risk:** 🟢 낮음 — 측정 작업. 실 API key + 비용 (~$0.50 예상, n=20 × 2 모델).

**우선순위:** ★★★☆☆ (P1 — Phase B swap gate 의 conditional 조건 해소 + ADR-019 Phase B 정합성 closure).

**Sprint 묶음 권고:** Sprint 25 첫 commit 또는 Sprint 24 closeout 직후. carry-over 시 conditional 조건 closure 까지 추적.

**예상 시간:** 1-2h (fixture 확장 1h + 측정 + 비교 1h).

**근거:** `docs/dev-log/sprints/2026-05-20-sprint24-wave2/post-swap-delta-report.md` §4 + §7 + §9 — Phase 2 진입 conditional 조건 명시 + Gate FAIL revert 미발동 사유 의존.

---

## BL-NEW-OBN-DATA-RETRY — Onboarding 재설계 data-driven retry (Sprint 25+)

**현 상태:** 미시작 (carry-over from Sprint 24 Wave 2 T-OBN-05 D 옵션 결정).

Sprint 22 OBN-01~04 의 OnboardingBanner 는 Sprint 24 Wave 2 에서 폐기 (Codex+Gemini deep research 합의 + Multi-Agent QA 데이터 TTFV 255초 / 글로벌 checklist 완료율 19.2% / PERSONA-001 power user 정합 분석). PERSONA-002/003 (PM 가설) 또는 tooltip analytics 결과 confirmed 시 onboarding 재설계 검토.

**진입 조건 (둘 중 하나):**
- F4 외부 인터뷰 (`docs/requirements/interview-results.md`) 결과 PM 페르소나 confirmed (다른 페르소나 친화 onboarding 가 ROI 확인).
- 또는 Sprint 24 Wave 2 tooltip analytics (`tooltip_shown` / `tooltip_dismissed`) 4-6주 데이터 축적 후 power user friction 또는 효과 부재 입증.

**목표 (재도입 시):**
1. AI personalize (1인 founder vs 팀 wedge 분화 — branching tutorial).
2. step 별 CTA 가 page transition 자동 trigger (passive banner → active deep-link).
3. measure 자체 강화 (activation funnel — workspace → project → meeting → RAG ask 각 step transition rate).
4. tooltip 산출물과 통합 (Linear-style first-visit hint 유지 + 명시적 walkthrough overlay 옵션 추가).

**Risk:** 🟢 낮음 — 신규 도입. 기존 BE 자산 (`User.onboarding_step` + event hook) 재활용 가능.

**우선순위:** ★★☆☆☆ (P3 — F4 외부 인터뷰 결과 또는 analytics 데이터 의존).

**Sprint 묶음 권고:** Sprint 25+ (F4 결과 또는 analytics 데이터 누적 후). 사용자 cohort sample size n≥20 권고.

**예상 시간:** 4-6h (재도입 시) — UI 설계 2h + BE 재활용 1h + analytics 추가 1h + E2E 1-2h.

**근거:** `docs/superpowers/specs/2026-05-20-sprint24-wave2-trusty-heron-design.md` §T-OBN-05 D 옵션 + Codex/Gemini deep research 합의 메모.


## BL-NEW-BE-PERF-COLD-START — Cloud Run + Neon cold start 진단 (Sprint 25+)

**상태**: 미시작 (carry-over from Sprint 24 Wave 2 T-BE-PERF spike)
**우선순위**: P1 (모바일 사용성 직결, BUG-MOBILE-005 의 main bottleneck 추정)
**예상 시간**: 4-6h

### 배경
Sprint 24 Wave 2 Phase 6 spike 결과: localhost 측정 BE 4 API 직렬 25ms (sub-second). Multi-Agent QA Mobile 보고는 3015-3865ms. 150x 갭 → BE 로직 외 origin (cold start + 외부 인프라).

### 진입 조건
- Sentry distributed trace 도입 후 production cold start 측정 가능

### 작업
1. Cloud Run min-instances 0 → 1 trade-off (cost vs latency)
2. Neon connection pool pre-warm + autoscale window
3. Vercel→Cloud Run RTT 진단

---

## BL-NEW-BE-PERF-PARALLEL-API — Dashboard 4 API 병렬화 (Sprint 25+)

**상태**: 미시작 (carry-over from Sprint 24 Wave 2 T-BE-PERF spike)
**우선순위**: P2

### 배경
dashboard 4 API (workspaces / members / meetings / inbox) 가 직렬 호출. workspaceId 의존 chain 검토 시 병렬화 가능 가능성. localhost 25ms → 12ms (~50%) 추정.

### 작업
- FE hook 의존 매트릭스 검토 (workspaceId 가 다른 hook 의존 여부)
- Promise.all 또는 useQueries 도입
- E2E timing 회귀 가드


## BL-NEW-JWT-CACHE-CACHETOOLS — JWT cache cachetools 전환 (Sprint 25+)

**상태**: 미시작 (carry-over from Sprint 24 Wave 2 Gemini 2차 Medium finding)
**우선순위**: P3 — functional regression 아님, refactor 권고
**예상 시간**: 1h

### 배경
Sprint 24 Wave 2 Phase 6 T-BE-PERF Top 1 fix 에서 `backend/src/auth/dependencies.py` 의 `_JWT_CLAIMS_CACHE` 를 자체 dict + 수동 maxsize 청소로 구현. Gemini 2차 review 가 `cachetools.TTLCache` 권고 (의존성 추가, 검증된 라이브러리).

### 작업
1. `cachetools` 의존성 추가 (pyproject.toml)
2. `_JWT_CLAIMS_CACHE: TTLCache(maxsize=1000, ttl=60)` 로 교체
3. `_jwt_cache_get/_set` 함수 단순화 (TTLCache 가 자동 eviction)
4. token_exp 상한 로직은 wrapper 로 보존

---

## BL-NEW-RAG-TIME-NONE-EXPLICIT — RAG time_range=None 명시 처리 (Sprint 25+)

**상태**: 미시작 (carry-over from Sprint 24 Wave 2 Gemini 2차 Low finding)
**우선순위**: P4 — 현재 작동 OK, 가독성 권고

### 배경
`backend/src/rag/service.py` 의 `is_time_filtered = time_range is not None and time_range != "all"`. None 이 default 라 None 도 cache 적용 (의도된 작동). 그러나 가독성 위해 명시적 처리 권고.

### 작업
- `is_time_filtered` 를 helper 함수로 추출 + docstring 으로 None/"all" 동치 명시

---

## BL-NEW-CLOUD-RUN-MIN-INSTANCES — Cloud Run min-instances=1 (Sprint 25+ 운영)

**상태**: 운영 권고 (Gemini 2차 Low finding + BL-NEW-BE-PERF-COLD-START 연계)
**우선순위**: P2 (BL-NEW-BE-PERF-COLD-START 의 일부)

### 배경
T-BE-PERF spike 결론 = production 3-4s 의 main bottleneck = Cloud Run cold start. Whisper chunked concurrency=4 시 cold start 환경에서 OOM 위험. min-instances=1 = cost vs latency trade.

### 진입 조건
- BL-NEW-BE-PERF-COLD-START 와 통합 검토
- Sentry production trace 도입 후 cold start 빈도 측정 → 비용 정당화

---

## BL-070 — Upload full streaming refactor (Sprint 25 polish carry, agy F2)

**상태**: 미시작 (Sprint 25 codex+agy review 결과 진입 시점 carry — 본 sprint 는 부분 fix 만)
**우선순위**: P2 (DoS 완화는 됐으나 streaming 이 진정한 fix)

### 배경
agy adversarial review (2026-05-21, Sprint 25 polish) F2 — `backend/src/upload/router.py:upload_file_proxy` 가 `await file.read()` 로 전체 파일을 RAM 적재 후 검증. 500MB × 4 concurrent = 2GB → Cloud Run 2GB instance OOM 위험.

Sprint 25 polish 부분 fix (commit `947b778`): `file.size` (multipart 메타) pre-read 차단 — 정상 client 의 oversize 페이로드는 RAM 적재 전 413. 그러나:
- `file.size = None` 인 client 는 여전히 fallback `await file.read()` → 전체 메모리 적재
- 정상 size 인 정상 파일도 read 시점에 메모리 폭발 가능 (concurrent N → N × file_size RAM)

### 진정한 fix (별도 sprint)
- `async for chunk in file:` streaming read
- 첫 512 byte signature 검증 후 stream-audit 으로 R2 putObject 직접 전달
- `UploadValidator` API refactor — `bytes` 인자 → `AsyncIterator[bytes]` 인자 또는 incremental validation
- aioboto3 multipart upload 활용 (Cloudflare R2 호환 확인 필요)

### 진입 조건
- 트래픽 증가 + Sentry trace 에서 OOM 또는 높은 메모리 사용 패턴 관찰
- 또는 GA launch 전 production hardening sprint

---

## BL-073 — Inbox handleConfirm 이 BE classify 미연결 (Sprint 25 polish carry, agy F-2B v2 검토 발견)

**상태**: 미시작 (agy F-2B v2 review 가 새로 발견 — F-2B 가 fix 한 dismiss 와 동일한 fake UX 패턴)
**우선순위**: P3 (사용자 발생 가능성 medium — "확정" 클릭 후 새로고침 시 회귀)

### 배경
agy F-2B v2 A/B review (Gap 1) — `SmartInboxItemCard.handleConfirm` 이 setStatus 만 호출, BE `useClassifyInbox` mutation 미연결.

```typescript
function handleConfirm() {
  setStatus("confirmed");  // local state 만
  // useClassifyInbox mutation 호출 X → BE 변경 0
}
```

`useClassifyInbox` 훅은 `hooks.ts:38-58` 에 정의되어 있고 BE `classify_inbox_item` API 와 연결돼있으나 `inbox-item-card.tsx` 에서 호출처 0.

증상: 사용자가 ✅ 확정 버튼 클릭 → UI "확정됨" 표시 → 페이지 새로고침 → 카드 다시 idle 상태로 복구 (BE persist 0).

이전 F-2B (dismiss) 와 동일한 패턴 — Sprint 25 polish v1 (commit 1caf99d) 이 dismiss 만 wire 하고 confirm 은 미처리.

### 작업
1. `inbox-item-card.tsx:handleConfirm`:
   - `useClassifyInbox` 훅 import + mutation 호출 추가
   - `dismissMutation.mutate(item.id, { onError: ... })` 패턴 follow
2. F-2B 와 동일하게 `confirmed` status 에서도 `↩ 되돌리기` 버튼 평가 (BE classify revert API 부재 가정)
3. 회귀 spec: e2e/tests/inbox-confirm.spec.ts 신설
4. **F-2B v3 agy 후속 발견 (Gap A + B 동봉)**:
   - `confirmed` 상태 카드 컨테이너 `opacity: 0.7` 도 WCAG AA 미달 (dismissed 와 동일 패턴) — F-2B v3 와 동일 fix 적용 (container opacity 제거 + 개별 요소 opacity)
   - `confirmed` 상태 `↩ 되돌리기` 버튼 도 BE classify wire 후 fake UX 위험 — dismissed 처럼 제거 + 정적 "확정됨" 표시 또는 BE revert API 동시 도입

### 진입 조건
- Sprint 25 polish 종료 후 즉시 또는 Sprint 26 inbox UX sprint 진입 시점
- F-2B v3 pattern 그대로 적용 가능

---

## BL-072 — Upload validation 의 ISO-BMFF text/plain bypass (Sprint 25 polish v3 carry, codex 4차 P2)

**상태**: 미시작 (Sprint 25 codex+agy 4차 A/B 결과 — Option B "KEEP v3 + carry" 채택)
**우선순위**: P3 (production 영향 낮음 — STT 미호출, R2 저장만)

### 배경
F-2A v3 (commit e2fa23b) 가 video/mp4 disguise bypass 는 막았으나, codex 4차 review 가 **신규 text/plain bypass 경로** 발견:

```
HEIC/AVIF (ftypheic) + filename=.txt + Content-Type=text/plain
→ _detect_mime_from_signature 가 disallowed brand 로 None 반환
→ _is_signature_compatible(None, text/plain) 가 text fail-open True
→ NUL byte 가 valid UTF-8 (U+0000) 이라 _check_text_content 통과
→ 201 R2 저장
```

v2 (audio/mp4 collapse) 였을 때는 text/plain 과 mismatch → 거부였으나, v3 brand allowlist 로 None 전환하면서 새 경로 노출.

### 실제 영향
- 인증 workspace member 만 가능 (외부 공격 X)
- text 파일은 STT 파이프라인 미진입 (`isAudioOrVideo` FE 분기) → 처리 안 됨, R2 저장만
- 자원 낭비 (R2 storage cost)
- Sprint 25 4차 iteration 깊어짐 + agy 4차 실패 (skill rabbit hole) 로 더 이상 양측 A/B 평가 불가

### 진정한 fix (별도 sprint)
1. `_detect_mime_from_signature` 가 sentinel 값 반환 ("application/octet-stream-unknown-ftyp") + _is_signature_compatible 에서 text/* 매칭 차단
2. 또는 real MIME detection library 도입 (`python-magic`, `filetype`) — 시스템 dep 추가
3. 또는 R2 upload 후 별도 post-validation lambda/event trigger

### 진입 조건
- Sprint 26+ 또는 GA hardening sprint
- 실제 자원 낭비 패턴이 Sentry/Cloud Run 메트릭에서 관찰 시 우선순위 상향

---

## BL-071 — Sync endpoint 재도입 시 Svix 검증 강제 CI guard (Sprint 25 polish carry, agy F9 sub-3)

**상태**: 미시작 (Sprint 25 codex+agy review F9 sub-3 — ADR-022 §"회수 옵션 5단계" 1차 완화 적용 후 carry)
**우선순위**: P3 (사용자 발생 가능성 낮음 — 단일 작성자 + ADR-022 lock-in)

### 배경
agy F9 sub-3 — `/api/v1/users/sync` endpoint 재도입 시 Svix 서명 검증 누락 위험. 현재 lock-in:
- ADR-022 §"회수 옵션 5단계" 에 Svix 검증 의무 명시
- `backend/tests/auth/test_auth_sync_disabled.py` 가 "404 응답" verify (재도입 시 fail → 작성자가 의식)

리스크: 재도입 commit 에서 회귀 테스트도 같이 제거 + Svix 추가 누락 → IDOR 회귀.

### 작업
- pre-commit hook 또는 CI lint:
  - `backend/src/auth/router.py` 에 `@router.post("/sync"` 또는 `@router.post("/users/sync")` 패턴 등장 시
  - 동일 파일에 `svix` 또는 `webhook_signature` 또는 `Webhook(` 임포트 부재면 block
- 또는 ADR-022 §"회수 옵션" 5단계 를 git commit message template 으로 강제 (작성자 의식 유도)

### 진입 조건
- GA launch 가 가시화되어 Clerk Production 발급 + sync 재도입이 실 작업이 될 때

---

## BL-NEW-DUE-DATE-LOG-TRACEABILITY — _validate_action_dates 로그 추적성 강화 (Sprint 25+)

**상태**: 미시작 (carry-over from Sprint 24 Wave 2 Gemini 2차 Low finding)
**우선순위**: P4

### 배경
`backend/src/services/ai_processing.py` 의 `_validate_action_dates` 후처리 helper 가 past year due_date drop 시 meeting_id + due_date + title 로그. ActionItem 의 다른 식별 정보 (assignee 등) 도 일부 남기면 prompt regression 추적성 향상.

### 작업
- log warn extra dict 에 `assignee` 등 추가
