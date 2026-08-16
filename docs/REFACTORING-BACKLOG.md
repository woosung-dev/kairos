# Kairos 리팩토링 백로그

> deepen-modules audit 산출물. 각 BL 항목은 사용자 승인 후 등재.
> 형식: BL-NNN + 우선순위(★) + Sprint 권고

---

> **2026-08-16 분할** — 해소된 BL 47건을 [`archive/backlog-resolved.md`](archive/backlog-resolved.md) 로 옮겼다.
> 본 파일은 **미해소 BL 만** 담는다. 해소 사유를 찾으려면 아카이브를 본다.

## 다음 Sprint 진입점 (Sprint 27+)

**Sprint 26 (glittery-tulip) 부터 sprint-별 handoff/closeout/verification/kickoff/final-summary 파일을 작성하지 않는다.** 지속 정보는 (1) git log + 머지된 PR body, (2) 이 백로그의 BL 항목, (3) `.claude/projects/.../memory/MEMORY.md` (선택). 다음 sprint 첫 commit 의도는 마지막 머지된 PR 의 "다음 sprint 진입점" 섹션에 1-3줄로 남긴다.

**현재 다음 픽업** (2026-05-23, Sprint 27a 진행 중): Sprint 26 머지 완료 (PR #104 → main `1be5beb`) → Sprint 27a luminous-anchor (D-6 grill + BL-S26-1 토큰컷, 본 PR) → Sprint 27b GA launch (Clerk Production + Svix + 외부 5명 dogfooding) → Sprint 28 paid customer 1명 (PMF signal).

**종료 기준** (3 도구 합의): GA launch 는 milestone, **paid customer 1명** 이 진짜 종료 신호.

---

## BL-S29-1 — `just docs-check` 게이트 신설 (규칙 재중복 방지) ⏳ **미착수**

**배경**: [ADR-029](adr/029-ai-rules-relocation.md) §2.2 가 「`apps/*/AGENTS.md` 는 `B-NN`·`F-NN`·`I-NN` 불변식을
재진술하지 않는다」를 규약으로 세웠으나, **강제 수단이 grep 뿐이다.** quant-bridge 는 `docs-audit.sh` 로
집행하지만 kairos `justfile` 에는 docs recipe 가 0개다.

누군가 `AGENTS.md` 에 규칙 문장을 다시 쓰면 CONTEXT 와 두 정본이 되고, ADR-029 이전은
**드리프트를 옮긴 것에 불과**해진다. 이번 이전에서 실제로 정정한 드리프트가 10건이었다는 점이 근거다.

**할 일**:
1. `just docs-check` recipe 신설 — 아래 3종 grep 을 묶는다
   - `git grep -n '\.ai/' -- . ':!docs/adr' ':!docs/dev-log'` 에서 tombstone 외 신규 발생 0건
   - `apps/*/AGENTS.md` 에 `B-\d+`/`F-\d+` 패턴이 **정의 형태**(표 행)로 등장하지 않을 것 (포인터 인용은 허용)
   - 옛 규칙 파일명(`backend.md`·`frontend.md`·`global.md`·`workflow.md`·`typescript.md`) 참조 0건
2. CI job 추가 (`.github/workflows/test.yml`)

**우선순위**: ★★ (ADR-029 의 효과 지속 여부가 여기 달려 있음)

---

## BL-S27c-1 — `get_current_user` lazy seed race condition fix ★★★ (P0)

**현 상태**: `apps/api/src/auth/dependencies.py:160-169` 의 User INSERT 가 race-unsafe. Dashboard 첫 진입 시 FE 가 5+ API 동시 호출 → 각 transaction 이 `find_by_clerk_id`=None → 동시 INSERT → 1개 성공 + 나머지 IntegrityError `duplicate key value violates unique constraint "ix_users_clerk_id"` → 500.

**증상 verified** (Sprint 27c audit, Account #3 c@e.com localhost 재현): `GET /workspaces` 500 + `/workspaces/{id}/members` 500 + `/workspaces/{id}/projects` 500 + `/workspaces/{id}/inbox` 403 (lazy fallback). production 의 동일 증상도 같은 race condition 추정 (deploy stale 가설 무효).

**목표**: User INSERT 에 `ON CONFLICT (clerk_id) DO NOTHING` 추가 (같은 file line 175-184 의 workspace INSERT 패턴 정합). 또는 try/except IntegrityError + retry find_by_clerk_id fallback.

**근거**: Sprint 27c audit, `git history`.

**영향**: 외부 5명 진입 60-80% 첫 dashboard 진입 시 500 가능성. dogfooding prerequisite.

---

## BL-S27c-2 — GEMINI_API_KEY 재발급 ★★★ (P0)

**현 상태**: `apps/api/.env` 의 `GEMINI_API_KEY` invalid. BE log `google.genai.errors.ClientError: 400 API_KEY_INVALID`. 회의 업로드 → AI pipeline 전체 실패 (status="실패").

**목표**: Google AI Studio (`https://aistudio.google.com`) 에서 새 API key 발급 + local `.env` + Cloud Run secret 동기화.

**근거**: Sprint 27c audit, `git history` P0-AI-PIPELINE.

**영향**: Kairos 핵심 가치 (AI 자동 요약) 0. ADR-019 Phase B (gemini-3.1-flash-lite) 동작 prerequisite.

---

## BL-S27c-3 — Landing screenshot 3건 400 fix ★★ (P1)

**현 상태**: `/landing/screenshots/screenshot-dashboard.png` / `meeting-summary.png` / `rag-answer.png` 모두 Next.js Image optimizer 400. 파일 disk 존재 (`apps/web/public/landing/screenshots/`). source code bug (localhost + production 동일 400).

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

## BL-S27c-9 — Production health check + Cloud Run min instance 1 ★ (P1)

**현 상태**: production BE `/api/v1/health` 응답이 200 (~65ms) ↔ timeout (10s+) 반복. Cloud Run cold start aggressive scaling 추정. 외부 5명 동시 진입 시 SLA risk.

**목표**: Cloud Run min instance 1 권고 (USD ~$10-15/month) 또는 CDN 헬스체크 + alert 설정.

**근거**: Sprint 27c audit `cto-perspective.md` 운영 readiness 3/10 BLOCK 한계.

---

## BL-S27c-10 — Cloud Run secret rotation 정책 ★ (P2)

**현 상태**: GEMINI_API_KEY invalid 가 secret 관리 process 의 첫 실패 case. rotation 정책 (auto-renewal / alert / staging verify) 부재.

**근거**: Sprint 27c audit `cto-perspective.md` 보안 baseline.

---

## BL-S27c-11 — Real IDOR + edge case 회귀 가드 강화 ★ (P2)

**현 상태**: Sprint 27c audit 에서 real cross-tenant IDOR verified (Account #1 → Account #2 workspace, 5 endpoint 403). 단 `apps/api/tests/integration/` 의 동일 시나리오 회귀 가드 명시 필요. Sprint 19 BUG-C01-EXT 의 후속 안정화.

**근거**: Sprint 27c audit `qa-edgecase.md` real verify 통과 + 헌법 I-9 정합 verified.

---

## BL-S27e-3 — CSP 정책 도입 (Sprint 27d carry) ★ (P3)

**현 상태**: Sprint 27d 보안 헤더 fix (BUG-S27d-4) 에서 X-Frame-Options / X-Content-Type-Options / Referrer-Policy / Permissions-Policy 4종은 추가됐으나 CSP 는 의도적 SKIP. Next.js + Clerk + R2 + Sentry 등 다수 도메인의 정책 정리 미완.

**목표**: 외부 도메인 inventory 정리 → `strict-dynamic` + nonce 기반 CSP 적용. Clerk SDK 의 inline script 정책 호환 확인.

**근거**: Sprint 27d opus audit BUG-S27d-4 fix 시 CSP 분리. agent-3 CTO 권고.

---

## BL-S27e-D — 성능 P2/P3 cluster (Sprint 28 carry) ★ (P2/P3)

- PERF-6/7/8/11/12 + PERF-r2-6~12 + BUG-S28-PERF-4~12 — promote cache wipe / cache cleanup cron / created_at 인덱스 / BG task leak / member cache scope 등
- 2026-07-05 team-collab-audit 정리: ✅ refetchOnWindowFocus 전역 false (`lib/query-client.tsx` — 탭 refocus 마다 앱 셸 7쿼리 재발화 × 인원수 증폭 차단) · ✅ PERF-9 "inbox N+1" 은 코드 반증(2쿼리+순수 변환)으로 종결 — 실제 N+1 은 멤버 목록이었고 BL-S27e-C 에서 해결 · ✅ tiptap dynamic 은 `/notes/[id]` 라우트 청크에만 포함 확인으로 종결 (대시보드 번들 무관)

---

## BL-S27e-F — 아키텍처 deepening cluster (Sprint 28 carry, 5-6d) ★★ (P1/P2)

- ARCH-1 + ARCH-r2-1 + ARCH-5 + BUG-S28-ARCH-2 — OnboardingService DI 통일 + Demeter helper
- ARCH-2 + ARCH-r2-3 — services DTO 일관
- ARCH-3 + BUG-S28-ARCH-1 — `apps/api/src/audit/` 도메인 신설 → BE 17 모듈 (현재 16)
- ARCH-6 — `common/promote_helpers.py` 확장 + 5 도메인 promote SRP
- ARCH-r2-2 — auth lazy seed LazySeedService 추출
- BUG-S28-ARCH-4 — `core ↔ common` cycle 분리
- BUG-S28-ARCH-5 (= TEST-7) — architecture test gate 4건

---

## BL-S27e-H — backend dependency upper-bound 정책 (Sprint 27e Round 2 신규) ★ (P3)

**현 상태**: `apps/api/pyproject.toml` 17 dependencies 중 `pgvector>=0.4.2,<1.0.0` 만 upper-bound 명시. 나머지 (google-genai/openai/sentry-sdk/fastapi 등) 하한만 → `uv sync` 자동 재해결 시 major bump (1.x → 2.x) 자동 적용 가능 → breaking API 변경 risk.

**Fix 후보**:
- (a) `uv.lock` pin 만 신뢰: CI 와 production Dockerfile 에서 `uv sync --frozen` 강제 (단순)
- (b) `pyproject.toml` 에 명시 upper-bound (`google-genai>=1.70.0,<2.0.0`) — 17 파일 patch
- (c) CI 에 `uv lock --check` 추가 (lock-pyproject mismatch 차단)

**권고**: 옵션 (a) + (c) 조합. uv.lock 이 ground truth, CI 가 drift 차단.

**근거**: Sprint 27e Round 2 security-findings-r2.md §2 r2-10. P3 분류.

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

**⚠️ Sprint 27e Round 2 회귀 발견** (2026-05-25, ARCH-r2-7): Sprint 27a partial 보고 `~3,398 tokens` 대비 현 실측 = **CONTEXT-MAP.md 7,960 bytes (`wc -c`) / 106 lines**. ADR-024 supersedes + I-21 HNSW 세션 변수 + 후속 추가로 본문 다시 확장. 목표 ≤3,000 까지 잔여 ~62% (보고 13% 가 stale). Sprint 27a 후 atomic update 정책 정합 회복 필요 — 향후 헌법 추가 시 토큰 비용 명시 책임.

**Sprint 27a 진행** (2026-05-23, stale): 2,918→2,614 words / 3,793→~3,398 tokens (10% 절감). 목표 ≤3,000 까지 추가 13% cut 필요. CONTEXT-MAP I-2/I-9/I-14/I-17/I-18 압축 + §2 4 박스 → 1 박스 + AGENTS.md Kairos 컨텍스트 80줄 → 8줄 (CONTEXT-MAP 위임). 추가 cut 시 정보 손실 risk → plan §3 정책으로 잔여 carry. ★★→★ 강도 하향.

**현 상태:** 2026-05-26 Sprint 28 Round A 측정 = CONTEXT-MAP.md **8,007 bytes / 106 lines** (Sprint 27e Round 2 7,960 대비 +47 bytes 추가 회귀). 목표 ≤ 3,000 tokens (~167% 초과). 본 sprint 진정한 cut 시도 X — BL-S26-1 목표 자체 재검토 권고 (token vs byte 단위 명시 + tiktoken 도구 표준화 — BUG-S28-ARCH-7).

**대상:** `AGENTS.md` + `CONTEXT-MAP.md`. (2026-08-15 ADR-029 — 구 대상이던 `.ai/common/global.md` 71줄은 `AGENTS.md §5` 로 흡수, `.ai/templates/workflow.md` 80줄은 삭제됐다.)

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
- `apps/api/src/meetings/models.py` — MeetingProgress 모델 추가
- `apps/api/src/meetings/pipeline_service.py` — commit 횟수 감소
- `alembic/versions/` — 마이그레이션 추가

**예상 LOC delta:** +50 (모델) / -30 (pipeline_service 단순화)

**Risk:** 🟡 중간 — polling API(`GET /status`)가 새 테이블을 읽도록 변경 필요

**Test harness:** 현 test 3개 존재. 마이그레이션 + polling API 테스트 추가 권고.

**우선순위:** ★★★☆☆

**Sprint 묶음 권고:** 단독 (Sprint 11+, F4 외부 인터뷰 완료 후)

**근거:** deepen-modules audit 2026-05-12 (git history)

---

## BL-007 — memory AI 호출 helper (`_call_distill` / `_call_embedding` / `_call_transcribe`) → services/memory_ai_calls.py 통합

**현 상태:**
`apps/api/src/memory/service.py:637~709` — module-level helper 3개에서 Gemini / OpenAI / Whisper client 직접 생성. 주석 "테스트 monkeypatch 진입점"이지만 BG task session_factory 컨텍스트와 AI 호출 시간 블로킹 분리 X. session orphan 위험.

**목표 인터페이스:**
```python
# services/memory_ai_calls.py 신설 (또는 services/ai_processing.py 확장)
class MemoryAiCallsService:
    async def distill(self, transcript: str) -> MemoryDistillResult: ...
    async def transcribe(self, r2_key: str) -> str: ...
    async def embed(self, text: str) -> list[float]: ...
```

**영향 파일:**
- `apps/api/src/services/memory_ai_calls.py` — 신설 (또는 ai_processing.py 확장)
- `apps/api/src/memory/service.py` — helper 제거

**예상 LOC delta:** +120 (services) / -75 (memory/service)

**Risk:** 🟢 낮음 — interface 변경 없음, 위치만 이동

**Test harness:** 신규 test_memory_ai_calls.py 필요

**우선순위:** ★★★☆☆ (P1, Seam 보강)

**Sprint 묶음 권고:** Sprint 18+ (BL-005/006 이후)

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-008 — memory R2 boto3 client 재생성 → R2Service 메서드로 상향

**현 상태:**
`apps/api/src/memory/service.py:602, 620` — `_upload_audio_to_r2` / `_download_audio_from_r2`가 R2Service 주입받지만 `self.r2_service._session.client(...)` non-public API 우회. Backend Rules §5 권장 (`aioboto3` async session 패턴) 위반.

**목표 인터페이스:**
```python
# common/r2.py R2Service 확장
class R2Service:
    async def upload_audio(self, key: str, body: bytes, content_type: str) -> None: ...
    async def download_audio(self, key: str) -> bytes: ...
    async def delete_audio(self, key: str) -> None: ...
```

**영향 파일:**
- `apps/api/src/common/r2.py` — 메서드 3개 추가
- `apps/api/src/memory/service.py` — helper 2개 → R2Service 메서드 호출

**예상 LOC delta:** +60 (r2.py) / -30 (memory/service)

**Risk:** 🟢 낮음 — interface 단순화. 기존 동작 동일.

**Test harness:** R2Service mock 테스트 추가

**우선순위:** ★★★☆☆ (P1)

**Sprint 묶음 권고:** Sprint 18+ (BL-007과 묶을 수 있음, 두 건 다 service.py LOC 감소)

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-009 — memory MemoryItem status state machine 분리 (3 BG task 중복 제거)

**현 상태:**
`apps/api/src/memory/service.py:515~549, 568~588, 755~787` — `processing → embedding_pending → active` (또는 embedding_failed) 전이 로직이 3개 BG task에 유사 중복. status 열거형은 `models.py:48~49`에 있지만 transition 검증 X. status 추가/변경 시 grep 3곳 수정 필요 (locality 낮음).

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
- `apps/api/src/memory/status_flow.py` — 신설
- `apps/api/src/memory/service.py` — 3개 BG task에서 사용

**예상 LOC delta:** +60 (status_flow) / -40 (service)

**Risk:** 🟢 낮음 — 행동 동일

**Test harness:** status_flow unit test 신설 + 기존 service 테스트 통과 유지

**우선순위:** ★★☆☆☆ (P2)

**Sprint 묶음 권고:** Sprint 19+ (BL-006 pipeline_service 분리 후 자연스럽게 결합)

**근거:** Sprint 15 Stage 5-1 audit (2026-05-14)

---

## BL-010 — memory MemoryQueryEmbeddingCache race condition 정책 결정

**현 상태:**
`apps/api/src/memory/service.py:335~355` — `_get_query_embedding` cache lookup 후 저장 (line 354). 동시 호출 시 UNIQUE 충돌 무시 (`repository.py:269` "race condition은 무시"). 두 workspace가 동일 normalized_query 입력 시 cache 공유 여부 deterministic X.

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
2. Schema + backfill 단일 migration — 2단계 배포 위반 (`apps/api/AGENTS.md` §9)
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
- alembic 추가 마이그레이션 + 기존 데이터 재배치 (대용량 시 다운타임 가능 — `apps/api/AGENTS.md` §9 2단계 배포)
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

## BL-028 — memory/service.py BackgroundMemoryService 분할

**도메인:** backend / memory
**근거:** Sprint 18 PR-C3 진행 중 발견. memory/service.py 864 LOC monolith. 클래스 메서드 `_bg_distill_and_embed` + `_bg_transcribe_distill_embed` + 모듈 함수 `_bg_promote_embed` 가 백그라운드 task 책임. Sprint 18 에서는 11줄 wrapper `_create_memory_embedding_chunk` 만 inline (circular import 회피).

**문제:**
- `_call_distill` / `_call_embedding` / `_call_transcribe` 모듈 헬퍼가 service.py 내부에 있어 background 분리 시 circular import.
- Foreground (capture_text/capture_voice/recall) + background (distill/embed/transcribe) 책임 단일 클래스 누적.

**해결:**
- `apps/api/src/memory/_helpers.py` 신설 — `_call_*` 헬퍼 3개 이동.
- `apps/api/src/memory/background.py` 신설 — `BackgroundMemoryService` 클래스 (3 백그라운드 task).
- `MemoryService.__init__` 에 BackgroundMemoryService 주입. router 변경 없음.

**예상 LOC delta:** service.py −300 / background.py +250 / _helpers.py +100. net +50, monolith 해소.

**Risk:** 🟡 중간 — session_factory 패턴 유지 + 22 memory tests 회귀 검증 필요.

**우선순위:** ★★☆☆☆ (구조 개선, 동작 동등)

**Sprint 묶음:** 단독 또는 다른 memory 부채 (BL-005/006) 와 묶음.

**근거:** Sprint 18 PR-C3 retrofit (commit ccfb192).

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

## BL-NEW-RAG-SOURCE-SELECT — RAG source-level selection v1 (Sprint 25+ 검토)

**현 상태:** 미시작 (carry-over from Sprint 24 Wave 2 T-RAG-MOCK-REMOVE / BUG-POW-005).

Sprint 24 Wave 2 T-RAG-MOCK-REMOVE 에서 `apps/web/src/features/rag/components/search-scope.tsx` 의 MOCK_SELECTABLE_SOURCES 5건 제거 후 "선택한 소스" 탭을 "소스 선택 기능 준비 중 — 현재는 전체 워크스페이스에서 검색합니다" empty state 로 변경. 장기적으로 source-level (회의/노트 단위) RAG 검색 범위 선택이 실제로 필요한가는 Power persona 데이터 수집 후 결정.

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

1. `apps/api/tests/llm/fixtures/sample_transcripts.py` 의 DELTA_3 ground-truth sample 을 5 → 20 으로 확장 (다양한 회의 시나리오 — 1:1, 4+명 회의, 마감일 명시/미명시 mix, assignee 명시/미명시 mix).
2. `apps/api/scripts/sprint24_wave2_delta.py` (또는 후속 sprint 의 동등 스크립트) 로 post-Phase-2 모델 (gemini-3.1-flash-lite + T-AI-DATE prompt) 재측정.
3. 결과 비교: baseline `P=1.000 R=1.000` (n=5) vs post-Phase-2 (n=20) — gate 임계 P/R ≥ 0.9.
4. fail 시: prompt 추가 강화 (예: assignee 명시 의무 위반 사례 Few-shot 추가) 또는 hybrid (chain-of-thought 또는 2-step extraction) 도입 검토.

**Risk:** 🟢 낮음 — 측정 작업. 실 API key + 비용 (~$0.50 예상, n=20 × 2 모델).

**우선순위:** ★★★☆☆ (P1 — Phase B swap gate 의 conditional 조건 해소 + ADR-019 Phase B 정합성 closure).

**Sprint 묶음 권고:** Sprint 25 첫 commit 또는 Sprint 24 closeout 직후. carry-over 시 conditional 조건 closure 까지 추적.

**예상 시간:** 1-2h (fixture 확장 1h + 측정 + 비교 1h).

**근거:** `git history` §4 + §7 + §9 — Phase 2 진입 conditional 조건 명시 + Gate FAIL revert 미발동 사유 의존.

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

**근거:** `git history` §T-OBN-05 D 옵션 + Codex/Gemini deep research 합의 메모.


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

**상태**: ✅ 종결 (2026-07-05 team-collab-audit) — activeWorkspaceId 가 zustand persist 라 재방문 시 앱 셸 쿼리들이 이미 병렬 발화 (uvicorn 로그 실측: workspaces/projects×2/inbox/members/onboarding 이 동시 burst). 워터폴은 최초 방문 1회뿐이며 Sprint 28 User/Member 캐시로 이미 1586ms 단축. 추가 작업 이득 없음.
**우선순위**: ~~P2~~ 종결

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
Sprint 24 Wave 2 Phase 6 T-BE-PERF Top 1 fix 에서 `apps/api/src/auth/dependencies.py` 의 `_JWT_CLAIMS_CACHE` 를 자체 dict + 수동 maxsize 청소로 구현. Gemini 2차 review 가 `cachetools.TTLCache` 권고 (의존성 추가, 검증된 라이브러리).

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
`apps/api/src/rag/service.py` 의 `is_time_filtered = time_range is not None and time_range != "all"`. None 이 default 라 None 도 cache 적용 (의도된 작동). 그러나 가독성 위해 명시적 처리 권고.

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
agy adversarial review (2026-05-21, Sprint 25 polish) F2 — `apps/api/src/upload/router.py:upload_file_proxy` 가 `await file.read()` 로 전체 파일을 RAM 적재 후 검증. 500MB × 4 concurrent = 2GB → Cloud Run 2GB instance OOM 위험.

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
- `apps/api/tests/auth/test_auth_sync_disabled.py` 가 "404 응답" verify (재도입 시 fail → 작성자가 의식)

리스크: 재도입 commit 에서 회귀 테스트도 같이 제거 + Svix 추가 누락 → IDOR 회귀.

### 작업
- pre-commit hook 또는 CI lint:
  - `apps/api/src/auth/router.py` 에 `@router.post("/sync"` 또는 `@router.post("/users/sync")` 패턴 등장 시
  - 동일 파일에 `svix` 또는 `webhook_signature` 또는 `Webhook(` 임포트 부재면 block
- 또는 ADR-022 §"회수 옵션" 5단계 를 git commit message template 으로 강제 (작성자 의식 유도)

### 진입 조건
- GA launch 가 가시화되어 Clerk Production 발급 + sync 재도입이 실 작업이 될 때

---

## BL-NEW-DUE-DATE-LOG-TRACEABILITY — _validate_action_dates 로그 추적성 강화 (Sprint 25+)

**상태**: 미시작 (carry-over from Sprint 24 Wave 2 Gemini 2차 Low finding)
**우선순위**: P4

### 배경
`apps/api/src/services/ai_processing.py` 의 `_validate_action_dates` 후처리 helper 가 past year due_date drop 시 meeting_id + due_date + title 로그. ActionItem 의 다른 식별 정보 (assignee 등) 도 일부 남기면 prompt regression 추적성 향상.

### 작업
- log warn extra dict 에 `assignee` 등 추가

---

## 2026-06-23 Fullsweep 멀티-퍼스펙티브 QA 잔여 P3 (F5~F9)

> 6관점 Generator→적대적 Evaluator 검증에서 confirmed 된 P3 (P1/P2 F1~F4 는 PR 에서 수정 완료).

### BL-F5 — 모바일(<380px) RAG 오버레이 가로 오버플로 (P3, UX)
`globals.css:55 --rag-overlay-width:380px` 고정 + `panel-layout.tsx:112` RAG 오버레이 패널에 `isMobile ? '100%'` 분기 누락 (형제 SourceViewer panel-layout.tsx:161 은 분기 보유). 320px(iPhone SE)에서 좌측 콘텐츠 클리핑. 수정=line 112 에 isMobile 분기 1줄. 회귀 가드: mobile-responsive.spec.ts 에 오버레이 열어 폭 검증 추가.

### BL-F6 — OnboardingService.get_status repository 우회 raw SQL (P3, I-1 국소 일탈)
`onboarding/service.py:39` 가 self._session.execute(text("SELECT ...")) 직접 실행 (repository 우회). 같은 클래스 increment_step 은 repo 위임. :user_id 바인딩이라 SQLi 없음 — 순수 tech-debt. 수정=OnboardingRepository 에 get_step 메서드 추가 후 위임.

### BL-F7 — Markdown citation 주입이 표/blockquote/h4-h6 미커버 (P3, correctness)
`markdown-message.tsx:87` components 매핑이 p/li/h1-h3 만 injectCitations → remark-gfm 표 셀/blockquote 내 [N] 이 raw 노출. RAG_SYSTEM_PROMPT 가 표 미요청이라 저확률(LLM 자발 표 emit 시만). 수정=td/th/blockquote/h4-h6 컴포넌트에도 injectCitations 적용 + 테스트 케이스.

### BL-F8 — Citation [N] out-of-range silent no-op + SourceViewer '내보내기' dead button (P3, UX)
`rag-chat.tsx:62` sources[num-1] 범위 초과 시 무반응(LLM 오작동 의존 edge). `source-viewer.tsx:231` ExternalLink('내보내기') onClick 부재 dead button. ⚠️2026-06-19 generator-checklist CASUAL-05 가설로 기등재. 수정=out-of-range 가드 토스트 + SourceViewer export wiring(또는 버튼 제거).

### BL-F9 — team spine T7 RBAC-mutate e2e flaky (P3, 테스트 인프라)
간헐 ~60s 행 → 30s 타임아웃(retry#2 전부 pass). rbac.py member-cache 60s TTL 관련 — 테스트 role-reset 경로(ensureMemberBaseline)에서 invalidate_member_cache 전파가 간헐 누락되어 캐시 TTL 만료까지 대기하는 정황. CI retries=2 가 가림. 보안 게이트(require_owner→403)는 건재(rbac.py + test_rbac.py 16-cell + T8 PASS). 수정=fixture 의 cache-warm/poll 보강 또는 setRole 후 명시적 cache 무효화 await.

### BL-F10 — inbox-dismiss e2e 테스트 격리 취약성 (P3, 테스트 인프라)
`inbox-dismiss.spec.ts:62` 가 `h3:has-text("${titleBefore}")` substring 매치로 dismiss 후 0건을 기대 → 공유 Neon dev DB 에 반복 e2e 실행으로 동일 AI 제목 inbox 항목이 누적되면(관측: 20건) 제목 유일성 가정이 깨져 실패. 2026-06-24 fullsweep 재실행 중 발현(수정 전 첫 런은 통과 — 데이터 누적 전). 제품 결함 아님(inbox 도메인 코드 무변경, F1~F4 와 무관). 수정=① 테스트가 고유 마커 제목 inbox 항목을 시드 후 그 항목만 dismiss/검증(self-contained), 또는 ② dismiss 한 항목의 id 기반 검증(has-text substring 대신 data-testid). 보강 전까지 dev DB inbox 누적 시 간헐 실패.

---

## 2026-07-01 Architecture Verification 산출 (BL-AV-N)

> docs + AGENTS.md 기반 아키텍처/기능 검증 (3-agent recon + deep-module Ousterhout deletion-test 렌즈). Scope B = 문서 정합 + arch test gate + 안전 FE 리팩토링. 검증 결론 = 코드는 헌법 21불변식을 대체로 준수 (I-1/I-4/I-9/I-13 clean; embeddings E-9·onboarding I-1 은 문서화된 예외).

### ✅ 본 PR 에서 해소 (RESOLVED)
- **문서 drift 봉합**. 모듈/feature 개수 정합 (BE 16 = 13 도메인 + common/core/services, FE 15 — feedback 등재) → `AGENTS.md` / `docs/architecture/directory-map.md` / `CONTEXT-MAP.md §4.3`. `apps/api/CONTEXT.md §4` 표 정정 (auth/notes/upload CONTEXT.md 존재 반영, feedback 행 추가). `apps/api/src/workspaces/CONTEXT.md` 신설 (유일 도메인 CONTEXT.md gap 해소).
- **arch test gate 강제화** (BUG-S28-ARCH-5 부분 해소). I-1 (service 가 AsyncSession 인스턴스 미보유, onboarding allowlist) / I-4 (프롬프트 `common/prompts.py` 중앙화) / core→common import allowlist (cycle 악화 회귀 가드) 3종 추가. 기존 memory→embeddings 가드 포함 arch test 4 게이트로 확대.
- **FE shallow/FSD 위반 제거**. notes·meetings `export-button.tsx` ~95% 중복 → `components/shared/ExportButton.tsx` 1개로 추출 (동작 보존, wrapper 2파일 삭제). FSD 격리 위반 2건 해소 — `getCitationColor` → `lib/citation-colors.ts`, visibility 공유 어휘(`ProjectVisibility` 타입 + 라벨/설명/색상) → `lib/visibility.ts` (members → projects 컴포넌트 내부 import 제거).

### BL-AV-1 — FE project-dashboard.tsx god component 분해 (P2, FE 아키텍처) ✅ **완료 (2026-07-13 FE seam 리팩토링 PR)**
`features/projects/components/project-dashboard.tsx`(637줄→셸 ~120줄)를 `components/dashboard/` 8파일로 분해 — header/content/actions-section/admin-dialogs 가 각자 쿼리 소유(쿼리 소유권 하향). 온보딩 게이트는 dashboard-content 소유로 거동 보존. team spine t3/t14/t20/t21 그린.

### BL-AV-2 — FE FSD public-API barrel 부재 (P3, FE 아키텍처) ✅ **완료 (2026-07-13, barrel 대신 lint 채택)**
barrel `index.ts` 대신 (Vercel bundle-barrel-imports 규칙과 상충 회피) `lib/query-keys.ts` 레지스트리로 cross-feature key import 소멸 + eslint `no-restricted-imports` 로 `@/features/*/components/*` cross-feature deep import 차단.

### BL-FE-COMPILER — React Compiler 재도입 (P3, FE 성능) — 진입 조건부
2026-07-13 시도→revert. 원인: compiler auto-memo 가 zustand store 의 안정 참조 함수 `hasRole("admin")` 결과를 stale 캐시 → role-gated UI(설정 Audit 탭, projects 생성 버튼) 미표시, team spine t16+t20 결정적 실패 (revert 후 그린). **재도입 조건**: `workspaces/store.ts` 의 `hasRole`(get() 클로저)를 반응형 selector 기반으로 교체 후. 현행 완화: SmartInboxItemCard 수동 memo.

### 백엔드 deep-module (이연 유지)
`audit/` 도메인 추출(`common/audit_*` + `promote_*`) + `core↔common` cycle 해소(`common/database.py` → `core/database.py`)는 **기존 BL-S27e-F** 클러스터로 이연(Scope C). 본 검증으로 둘 다 코드 재확인 완료 — core→common 단일 edge=`lifespan.py → common.database`(test gate 로 고정), `common/audit_router.py` 가 `prefix=/audit` + `tags=["audit"]` 자가선언(도메인 추출 신호).

